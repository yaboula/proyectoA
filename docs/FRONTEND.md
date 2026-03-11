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
    kiosco.js          # Wrappers EP1-EP4 + EP6/EP7
  components/
    KioskLayout.vue
    ScanStation.vue
    ManualInputModal.vue
    FullScreenOverlay.vue
    EmptyState.vue
  composables/
    useScanner.js      # Scanner USB HID
  router/
    index.js           # Guards por sesion y modulo
  stores/
    operario.js        # Sesion, perfil y modulos permitidos
  views/
    LoginQR.vue
    ModuleHub.vue
    TareasList.vue
    PokaYokeScanner.vue
    LaboratoireQC.vue
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

## Estado de Implementacion

- Flujo production operativo: login -> tareas -> poka-yoke -> EP4.
- Flujo quality operativo: hub -> laboratoire -> EP7.
- Perfilado por badge operativo en frontend/router/store.
- Mobile fixes del drawer de laboratorio aplicados (scroll + reset iOS).
