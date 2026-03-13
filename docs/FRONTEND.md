# Frontend Architecture - Kiosco PWA

## Stack

| Libreria | Version | Rol |
|----------|---------|-----|
| Vue 3 | 3.5 | UI framework |
| Vite | 7.3 | Build + dev server |
| Tailwind CSS | 4.2 | Utility styling |
| Pinia | 3.0 | Estado global |
| Vue Router | 4.6 | Navegacion SPA |
| Axios | 1.13 | Cliente HTTP |
| PrimeVue | 4.5 | Drawer, inputs, Toast (modulo laboratorio) |
| lucide-vue-next | 0.577 | Iconografia |

## Estructura

```text
kiosco-pwa/src/
  api/
    client.js          # Axios + form-urlencoded + unwrap response.message
    kiosco.js          # Wrappers EP1-EP5 + calidad + recepcion + inventario ciego
  components/
    KioskLayout.vue
    ScanStation.vue
    ManualInputModal.vue
    FullScreenOverlay.vue
    EmptyState.vue
    ReceptionCaptureModal.vue
  composables/
    useScanner.js      # Scanner USB HID
  router/
    index.js           # Guards por sesion y modulo
  stores/
    operario.js        # Sesion, perfil y modulos permitidos
    blindInventory.js  # Conteo offline persistente por warehouse
    syncQueue.js       # Cola diferida para EP4, EP7 y EP_REC_5
  views/
    LoginQR.vue
    ModuleHub.vue
    TareasList.vue
    PokaYokeScanner.vue
    LaboratoireQC.vue
    ReceptionMateriaux.vue
    TransladoCuarentena.vue
    ReimpresionEtiqueta.vue
    InventarioCiego.vue
  utils/
    printer.js         # Servicio local ZPL para Zebra
    qr.js              # Parser QR kiosco con soporte QA,item|batch
  App.vue
  main.js
  style.css
```

## Rutas

| Path | Vista | Meta |
|------|-------|------|
| / | LoginQR | guest |
| /hub | ModuleHub | - |
| /tareas | TareasList | module: production |
| /laboratoire | LaboratoireQC | module: quality |
| /recepcion | ReceptionMateriaux | module: reception |
| /traslado-cuarentena | TransladoCuarentena | module: reception |
| /reimpresion | ReimpresionEtiqueta | module: reception |
| /inventario-ciego | InventarioCiego | module: reception |
| /poka-yoke/:workOrder | PokaYokeScanner | module: production |

Guard global:

- Rutas guest no requieren sesion.
- El resto llama `ensureSession()`.
- Si no hay sesion valida, redirige a `/`.
- Si el perfil no tiene permiso para el modulo, redirige a `/hub`.

## Store de Sesion

Store: `operario`

- Estado: `operario`, `sid`, `initialized`, `restoring`.
- Persistencia: `sessionStorage` para rehidratar sesion de navegador.
- Acciones:
  - `login(qrToken)` -> EP1
  - `restoreSession()` -> EP1b
  - `ensureSession()`
  - `logout()` -> EP1c
  - `hasModule(code)`

## API Client

`src/api/client.js`

- `withCredentials: true` para cookie `sid`.
- Convierte payloads object a `application/x-www-form-urlencoded`.
- Desenvuelve sobre Frappe (`data.message`).
- Cabeceras anti-cache para evitar estados inconsistentes en kioscos.

## Wrappers API

`src/api/kiosco.js`

- EP1 `loginOperario`
- EP1b `getOperarioSession`
- EP1c `logoutOperario`
- EP2 `getTareas`
- EP3 `validarMaterial`
- EP4 `reportarConsumo`
- EP5 `getInfoLote`
- EP6 `getLotesCuarentena`
- EP7 `aprobarCalidad`
- EP_REC_1 `getComprasPendientes`
- EP_REC_2 `registrarRecepcion`
- EP_REC_3 `trasladarLoteAprobado`
- EP_REC_4 `getLoteParaImpresion`
- EP_REC_5 `subirConteoFisico`

## Flujo de Pantallas

### LoginQR

- Scanner QR por teclado HID con fallback manual.
- Si hay sesion valida: salta a hub o ruta default del perfil.
- UI en frances y touch-first.

### ModuleHub

- Muestra solo modulos permitidos por perfil (`production` / `quality`).
- CTA grandes para tablet.

### TareasList

- Consume EP2 por empresa + warehouse por defecto.
- Tarjetas de WO con estado de stock y CTA "DEMARRER LA PRODUCTION".

### PokaYokeScanner

- Carga materiales de la WO desde EP2.
- Valida cada escaneo por EP3.
- Estados: ready/scanning/loading/success/error.
- Cierre EP4:
  - standard
  - extras
  - submitting
  - success/error overlays

### LaboratoireQC

- Lista lotes en cuarentena (EP6).
- Consulta informativa de lote (EP5) al abrir el drawer.
- Drawer de inspeccion con parametros dinamicos.
- Decisiones Approved/Rejected.
- Submit a EP7 con journal de ultima accion.

### ReceptionMateriaux

- Lista Purchase Orders abiertas via EP_REC_1.
- Modal dedicado de captura con qty, lote proveedor y fecha de vencimiento.
- Botones fat-finger `+1`, `+10`, `MAX` para cantidades.
- Submit a EP_REC_2 y recarga inmediata del backlog de quai.
- Intento de impresion local Zebra via `printer.js`; si falla, la UI muestra alerta amarilla pero mantiene la recepcion ERP como exitosa.
- Hub operativo hacia Sprint 5 con accesos directos a gestion de quarantaine y re-impresion.

### TransladoCuarentena

- Usa `useScanner()` o `ManualInputModal` para capturar `batch_no` o QR `item|lot`.
- Valida ubicacion real del lote via EP5 `getInfoLote` antes de permitir cualquier traslado.
- Si el lote no tiene saldo en `Cuarentena MP - <ABBR>`, muestra bloqueo inline rojo y deshabilita la CTA.
- La CTA primaria mueve toda la cantidad disponible mediante EP_REC_3 hacia `Materia Prima Aprobada - <ABBR>`.
- Tras un traslado exitoso, la vista preserva el mensaje de exito y evita sobrescribirlo con el aviso "Le lot n'est pas en quarantaine MP." durante la recarga post-accion.

### ReimpresionEtiqueta

- Captura `batch_no` por scanner HID o entrada manual.
- Consulta EP_REC_4 para reconstruir `item_code`, `item_name`, `batch_no` y `expiry_date`.
- Reutiliza `printSingleKioscoLabel()` sobre `printer.js` para relanzar ZPL al bridge local `http://localhost:9000/print`.

### InventarioCiego

- Flujo 100% offline durante el escaneo: cada lectura agrega localmente una unidad al conteo activo sin postback.
- Selector rapido de warehouse sobre cuatro almacenes operativos frecuentes del tenant.
- Usa `blindInventory.js` para persistir conteos por warehouse en `localStorage`.
- Usa `syncQueue.js` para encolar `EP_REC_5_SUBIR_CONTEO` cuando no hay red o el postback falla por conectividad.
- El parser QR tolera `QA,ITEM_CODE|BATCH_NO` y `ITEM_CODE|BATCH_NO`.

## Design System Actual (Light Industrial)

Fuente principal y estilo:

- Theme claro industrial.
- Fondo base `#f4f4f5`.
- Paneles blancos con borde zinc.
- CTA principal azul (`bg-blue-600`).

Clases compartidas en `style.css`:

- `.kiosk-panel`
- `.kiosk-panel-soft`
- `.gcma-data-row`
- `.gcma-stat`
- `.kiosk-chip`
- `.kiosk-icon-shell`
- `.gcma-toolbar`
- `.gcma-section-label`

Reglas de accesibilidad/touch:

- Base font-size: 16px mobile, 18px desde `sm`.
- CTA primarias en `h-16`.
- Acciones secundarias/destructivas minimo `h-12`.

## Scanner HID

`useScanner(onScan, { gapMs = 80, minLength = 3, disabled })`

- Escucha `keydown`.
- Buffer con timeout por gap.
- `Enter` dispara callback.
- `disabled` pausa lectura (modales/errores).
- En Sprint 6 se reutiliza sin validacion backend por scan; el callback hace agregacion local en memoria persistida.

## Testing E2E

Playwright queda configurado en `kiosco-pwa/` para pruebas visibles del kiosco y ya cubre Bloque 2 completo.

Archivos base:

- `playwright.config.js` — arranca/reutiliza Vite en `:5173` y deja trace/screenshot/video en fallos.
- `tests/e2e/reception.spec.js` — recepcion parcial y recarga del backlog.
- `tests/e2e/quarantine.spec.js` — traslado de lote aprobado fuera de cuarentena.
- `tests/e2e/reprint.spec.js` — reimpresion de etiqueta con bridge Zebra mockeado.
- `tests/e2e/inventory.spec.js` — conteo local y envio del borrador ERPNext.

Scripts npm disponibles:

- `npm run test:e2e` — suite E2E completa.
- `npm run test:e2e:block2` — suite Playwright etiquetada `@block2` en modo determinista (`--workers=1`).
- `npm run test:e2e:headed` — navegador visible.
- `npm run test:e2e:block2:headed` — Bloque 2 visible en navegador, tambien en modo determinista (`--workers=1`).
- `npm run test:e2e:debug` — inspector paso a paso.
- `npm run test:e2e:prepare-reception` — prepara una Purchase Order abierta para el flujo de recepcion.
- `npm run test:e2e:prepare-block2` — prepara recepcion, cuarentena e inventario ciego para la suite de Bloque 2.

Prerequisitos operativos:

- Docker Frappe/ERPNext levantado en `http://localhost:8080`.
- El test arranca Vite automaticamente si `:5173` no esta ocupado.
- Si hace falta otro badge, se puede sobrescribir con `PLAYWRIGHT_BADGE_TOKEN`.

## Persistencia Offline

- `operario.js` persiste `operario` y `sid` en `sessionStorage`.
- `blindInventory.js` persiste `activeWarehouse`, `countsByWarehouse` y `lastScan` en `localStorage`.
- `syncQueue.js` persiste operaciones diferidas en `localStorage` para reintento posterior.

## Estado de Implementacion

- Flujo production operativo: login -> tareas -> poka-yoke -> EP4.
- Flujo quality operativo: hub -> laboratoire -> EP7.
- Flujo reception operativo: hub -> recepcion -> EP_REC_1/EP_REC_2 + impresion local.
- Flujo Sprint 5 operativo: recepcion -> traslado-cuarentena -> EP5/EP_REC_3 y recepcion -> reimpresion -> EP_REC_4 + Zebra local.
- Flujo Sprint 6 operativo: recepcion -> inventario-ciego -> conteo offline -> EP_REC_5 o cola diferida.
- Perfilado por badge operativo en frontend/router/store.
- Mobile fixes del drawer de laboratorio aplicados (scroll + reset iOS).
