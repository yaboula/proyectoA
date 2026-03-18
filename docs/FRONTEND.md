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
    client.js           # Axios + form-urlencoded + unwrap response.message
    kiosco.js           # Wrappers EP1-EP7, recepción, logística B2B (S09-S10)
    customerPortal.js   # Wrappers B2B: catálogo, cobros, portal, loyalty (S07-S11)
    gerencial.js        # Wrappers S12: panel, mapa, CSV, alertas
  components/
    KioskLayout.vue         # Shell exterior global. Prop: maxWidth ('5xl'|'6xl'|'7xl')
    ScanStation.vue         # Visualizador estado scanner (idle/scanning/loading/success/error)
    ManualInputModal.vue    # Modal saisie manuelle con Teleport
    FullScreenOverlay.vue   # Overlay fullscreen (error/success/loading/info). Tap-to-dismiss
    EmptyState.vue          # Estado vacío reutilizable. Props: icon, title, message
    ReceptionCaptureModal.vue # Modal captura datos de recepción MP
    CheckInModal.vue        # Modal check-in GPS para S07. Solicita navigator.geolocation
    NetworkIndicator.vue    # Indicador de conectividad (online/offline) con badge
    OverrideFEFOModal.vue   # Modal PIN encargado para override de lote FEFO (S09)
    CartePedidoModal.vue    # Modal carrito B2B con bloqueo por mora y fallback offline (S08)
  composables/
    useScanner.js       # Scanner USB HID — eventos keydown con buffer y timeout
  router/
    index.js            # 16 rutas con guards de sesión y módulo
  stores/
    operario.js         # Sesión, perfil, módulos permitidos (sessionStorage)
    pokaYoke.js         # Estado del flujo poka-yoke activo (localStorage)
    blindInventory.js   # Conteo offline persistente por warehouse (localStorage)
    syncQueue.js        # Cola diferida para EP4, EP7, EP_REC_5, pedidos offline (localStorage)
  views/
    LoginQR.vue                 # EP1: login por QR badge
    ModuleHub.vue               # Hub de navegación con módulos disponibles
    TareasList.vue              # EP2: listado de Work Orders pendientes
    PokaYokeScanner.vue         # EP3+EP4: validación materiales y reporte consumo
    LaboratoireQC.vue           # EP6+EP7: inspección QC con drawer PrimeVue
    ReceptionMateriaux.vue      # EP_REC_1+2: recepción de materiales con PO
    TransladoCuarentena.vue     # EP_REC_3: traslado lote aprobado a MP Aprobada
    ReimpresionEtiqueta.vue     # EP_REC_4: reimpresión etiqueta ZPL por lote
    InventarioCiego.vue         # EP_REC_5: conteo físico offline + sincronización
    RutaComercial.vue           # S07: hoja del día, check-in GPS, sync offline
    CatalogoStock.vue           # S07: catálogo con stock real, carrito, pedido S08
    KioscoPickingFEFO.vue       # S09: pick list FEFO, scan por ítem, override PIN
    AppChoferPOD.vue            # S10: entregas del turno, firma canvas + foto POD
    PortalB2BCliente.vue        # S11: portal droguería, estado cuenta, loyalty, SOS
    PanelGerencial360.vue       # S12: scorecard, mapa Leaflet GPS, hit-rate, alertas
  utils/
    printer.js          # Servicio local ZPL para Zebra
    qr.js               # Parser QR kiosco con soporte QA,item|batch
  App.vue
  main.js
  style.css
```

## Rutas

| Path | Vista | Meta |
|------|-------|------|
| `/` | LoginQR | guest |
| `/hub` | ModuleHub | — |
| `/tareas` | TareasList | module: production |
| `/poka-yoke/:workOrder` | PokaYokeScanner | module: production |
| `/laboratoire` | LaboratoireQC | module: quality |
| `/recepcion` | ReceptionMateriaux | module: reception |
| `/traslado-cuarentena` | TransladoCuarentena | module: reception |
| `/reimpresion` | ReimpresionEtiqueta | module: reception |
| `/inventario-ciego` | InventarioCiego | module: reception |
| `/rutas-comercial` | RutaComercial | module: comercial |
| `/catalogo-stock` | CatalogoStock | module: comercial |
| `/picking-fefo` | KioscoPickingFEFO | module: logistica |
| `/chofer-pod` | AppChoferPOD | module: logistica |
| `/portal-b2b` | PortalB2BCliente | guest (portal externo) |
| `/panel-gerencial-360` | PanelGerencial360 | guest (dashboard directivo) |

Guard global:

- Rutas `meta.guest` no requieren sesión.
- El resto llama `ensureSession()` → si no hay sesión válida, redirige a `/`.
- Si el perfil no tiene acceso al módulo requerido, redirige a `/hub`.

## Stores Pinia

### `operario` — Sesión global
- Estado: `operario`, `sid`, `initialized`, `restoring`, `customerId`.
- Persistencia: `sessionStorage`.
- Acciones: `login(qrToken)`, `restoreSession()`, `ensureSession()`, `logout()`, `hasModule(code)`.

### `pokaYoke` — Flujo de validación de materiales
- Estado: `workOrder`, `materialesValidados`, `consumosExtra`.
- Persistencia: `localStorage` (sobrevive recarga en caso de cierre accidental del kiosco).
- Acciones: `setWorkOrder()`, `marcarMaterialValidado()`, `reset()`.

### `blindInventory` — Conteo físico offline
- Acumula conteos por warehouse por item+lote.
- Persiste en `localStorage` hasta `subir_conteo_fisico` exitoso.
- Se vacía tras sincronización exitosa.

### `syncQueue` — Cola offline diferida
- Encola operaciones críticas (EP4 consumo, EP7 QC, pedidos B2B S08) cuando hay pérdida de red.
- Procesa la cola en `syncAll()` al reconectar.
- Expone `pendingCount` y `hasPending` para `NetworkIndicator`.

## API Client

`src/api/client.js`

- `withCredentials: true` para cookie `sid`.
- Convierte payloads object a `application/x-www-form-urlencoded`.
- Desenvuelve sobre Frappe (`data.message`).
- Cabeceras anti-cache para evitar estados inconsistentes en kioscos.

## Wrappers API

### `kiosco.js` — Producción, Calidad, Recepción, Logística
- EP1–EP5: `loginOperario`, `getOperarioSession`, `logoutOperario`, `getTareas`, `validarMaterial`, `reportarConsumo`, `getInfoLote`
- EP6–EP7: `getLotesCuarentena`, `aprobarCalidad`
- EP_REC_1–5: `getComprasPendientes`, `registrarRecepcion`, `trasladarLoteAprobado`, `getLoteParaImpresion`, `subirConteoFisico`
- S07: `getRutaDia`, `postCheckin`
- S09: `getPickList`, `validarScanFefo`, `overrideFefoBatch`
- S10: `getEntregasPendientesChofer`, `registrarPod`

### `customerPortal.js` — B2B Comercial y Portal
- S07: `getCatalogoStock`
- S08: `getEstadoCuenta`, `postCobro`, `syncPedidosOffline`
- S11: `getPortalDashboard`, `getPortalEstadoCuenta`, `crearPedidoPortal`, `createSupportTicket`, `getLoyaltyPoints`, `redimirPuntos`

### `gerencial.js` — Panel Directivo S12
- `getPanelGerencial360`, `getCoberturaMapa`, `getReporteFotosCompetencia`, `exportScorecardCsv`, `runAlertaAbandonoClientes`

### Patrón de namespace fallback
`kiosco.js` y `customerPortal.js` intentan primero `maroc_b2b.api.*` y, si el servidor devuelve `App maroc_b2b is not installed`, reintenta con `gcma_kiosco.api.*`. Esto permite despliegues donde el alias no está registrado.

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

## Sprint 12 - Panel Gerencial 360

Nuevas piezas frontend:

- `src/api/gerencial.js`
  - `getPanelGerencial360(fecha?)`
  - `getCoberturaMapa(fecha?)`
  - `getReporteFotosCompetencia(limit?)`
  - `runAlertaAbandonoClientes(fecha?)`
  - `exportScorecardCsv(fecha?)`
- `src/views/PanelGerencial360.vue`
  - KPI cards (clientes, check-ins, desviaciones, hit-rate).
  - Mapa de Marruecos con `leaflet` y marcadores por estado de visita.
  - Tabla scorecard top clientes.
  - Boton de ejecucion manual de alerta de abandono.
  - Descarga CSV del scorecard.
  - Reporte visual de fotos de competencia/precio.
- `src/router/index.js`
  - Nueva ruta `/panel-gerencial-360`.

Dependencia nueva:

- `leaflet` para renderizado del mapa GPS.

## Sprint 11 - Portal B2B Cliente

Nuevas piezas frontend:

- `src/api/customerPortal.js`
  - `getPortalDashboard(idCliente?)`
  - `getPortalEstadoCuenta(idCliente?, limit?)`
  - `crearPedidoPortal({ id_cliente, items })`
  - `createSupportTicket(description, b64Photo, affectedBatch, idCliente?)`
- `src/views/PortalB2BCliente.vue`
  - Home portal self-service con estado de cuenta y sugerencias.
  - Bloqueo visual por mora > 30 dias (sin permitir alta de pedido).
  - Formulario SOS con adjunto de foto (`capture="environment"`).
  - Historial de facturas/pagos.
- `src/router/index.js`
  - Nueva ruta `/portal-b2b`.

Notas UX:

- Se mantienen componentes y clases del design system industrial light (`kiosk-panel`, `gcma-stat`, `gcma-data-row`, `h-16` para CTA primario).
- Textos visibles al cliente en frances.
