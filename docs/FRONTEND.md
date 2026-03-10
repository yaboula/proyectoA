# Frontend Architecture — Kiosco PWA

## Stack

| Librería | Versión | Rol |
|----------|---------|-----|
| Vue 3 | 3.5 | Framework UI (Composition API + `<script setup>`) |
| Vite | 7.3 | Bundler + dev server |
| Tailwind CSS | 4.2 | Styling vía `@tailwindcss/vite` (no PostCSS) |
| Pinia | 3.0 | Estado global |
| Vue Router | 4.6 | Navegación SPA |
| Axios | 1.13 | HTTP client |
| PrimeVue | 4.5 | Librería de componentes moderna (Cards, Drawer, Buttons, Toast, formularios) |
| @primeuix/themes | 2.0 | Tema base Aura en modo oscuro |
| vite-plugin-pwa | 1.2 | Service Worker + manifest |

## Estructura

```
kiosco-pwa/src/
├── api/
│   ├── client.js        # Axios instance (baseURL, interceptors)
│   └── kiosco.js        # Wrappers tipados EP1–EP4 + EP6/EP7 calidad
├── stores/
│   └── operario.js      # Pinia store — sesión del operario
├── router/
│   └── index.js         # rutas protegidas + hub de módulos
├── views/
│   ├── LoginQR.vue      # Pantalla de login (escáner + modal manual)
│   ├── ModuleHub.vue    # Hub visual para Production / Laboratoire
│   ├── LaboratoireQC.vue # Console qualité (Bloque 4)
│   ├── TareasList.vue   # Lista de Work Orders
│   └── PokaYokeScanner.vue  # Validación de materiales
├── App.vue              # Shell global + Toast + fondo temático
├── main.js              # Punto de entrada (Pinia + Router + PrimeVue)
└── style.css            # Tailwind + overrides PrimeVue + visual system
```

## Rutas

| Path | Componente | Meta | Lazy |
|------|-----------|------|------|
| `/` | `LoginQR` | `{ guest: true }` | No |
| `/hub` | `ModuleHub` | — | Sí |
| `/tareas` | `TareasList` | `{ module: 'production' }` | Sí |
| `/laboratoire` | `LaboratoireQC` | `{ module: 'quality' }` | Sí |
| `/poka-yoke/:workOrder` | `PokaYokeScanner` | `{ module: 'production' }`, `props: true` | Sí |

### Navigation Guard

```js
router.beforeEach(async (to) => {
  const store = useOperarioStore()
  if (to.meta.guest) return true
  const ok = await store.ensureSession()
  if (!ok) return '/'
  if (to.meta.module && !store.hasModule(to.meta.module)) return '/hub'
})
```

Redirige a login si no hay sesión y antes intenta restaurarla desde la cookie `sid`, excepto rutas con `meta.guest`. Además bloquea navegación directa a módulos no autorizados por el perfil del `Employee`.

## Estado (Pinia)

### `operario` store

| Propiedad | Tipo | Descripción |
|-----------|------|-------------|
| `operario` | object \| null | Datos del empleado (de EP1) |
| `sid` | string \| null | Session ID de Frappe |
| `initialized` | boolean | Indica si el store ya intentó restaurar sesión |
| `restoring` | boolean | Evita llamadas duplicadas a restauración |

| Getter | Retorna |
|--------|---------|
| `isLoggedIn` | `!!operario` |
| `fullName` | `operario.full_name` |
| `profileCode` | `operario.profile_code` |
| `profileLabel` | `operario.profile_label` |
| `allowedModules` | `operario.allowed_modules[]` |

| Action | Descripción |
|--------|-------------|
| `login(qrToken)` | Llama EP1, guarda operario + sid |
| `restoreSession()` | Llama EP1b y reconstruye el contexto desde la cookie `sid` |
| `ensureSession()` | Devuelve la sesión actual o intenta restaurarla |
| `hasModule(code)` | Indica si el perfil actual puede abrir un módulo |
| `logout()` | Llama EP1c y limpia estado local |

## API Wrappers (`kiosco.js`)

| Función | Endpoint | Parámetros |
|---------|----------|------------|
| `loginOperario(qrToken)` | EP1 `login_operario` | `qr_token` |
| `getOperarioSession()` | EP1b `get_operario_session` | — |
| `logoutOperario()` | EP1c `logout_operario` | — |
| `getTareas(company, warehouse)` | EP2 `get_tareas` | `company`, `warehouse` |
| `validarMaterial(workOrder, qrData)` | EP3 `validar_material` | `work_order`, `qr_data` |
| `reportarConsumo(workOrder, lotesUsados, consumosExtra)` | EP4 `reportar_consumo` | `work_order`, `lotes_usados` (JSON string), `consumos_extra` (JSON string) |
| `getLotesCuarentena(warehouse)` | EP6 `get_lotes_cuarentena` | `warehouse?` |
| `aprobarCalidad(payload)` | EP7 `aprobar_calidad` | `itemCode`, `batchNo`, `qty`, `parametros`, `aprobada`, `resultado`, `remarks` |

## Shell de Aplicación

- `main.js` inicializa PrimeVue con preset `Aura` y `ToastService`.
- `App.vue` deja de ser un `RouterView` plano y monta una shell oscura con fondo atmosférico y `Toast` global.
- El flujo post-login ya no entra directo en producción: redirige a `/hub`, donde el operario elige entre fabricación y laboratorio.

## ModuleHub — Selección de Zona

Vista de entrada post-login con módulos filtrados según `operario.allowed_modules`:

- **Production pilotée** → navega a `/tareas`
- **Laboratoire qualité** → navega a `/laboratoire`

Características:

- Hero visual tipo control room con resumen de sesión activa
- Perfil kiosco visible en el panel de sesión
- Cards de módulo con CTA grandes, énfasis visual distinto por dominio
- Botón explícito de cierre de sesión
- Navegación pensada para tablet, no para escritorio administrativo
- Si el badge solo tiene un módulo permitido, Login redirige directamente a su ruta por defecto sin pasar por el hub

## LaboratoireQC — Console Qualité

Pantalla completa de Bloque 4 construida con PrimeVue (`Card`, `Drawer`, `SelectButton`, `InputNumber`, `Textarea`, `Message`, `Toast`).

### Capacidades

- Consulta EP6 `get_lotes_cuarentena` al montar
- KPIs superiores: número de lotes, volumen en cuarentena y lote más antiguo
- Búsqueda libre por `item_code`, `item_name`, `batch_no` y fecha
- Grid de lotes con CTA `Lancer l’inspection`
- Drawer lateral de inspección con:
  - cantidad inspeccionada
  - selector de decisión `Approuver / Rejeter`
  - parámetros dinámicos con filas editables
  - textarea de observaciones
- Submit contra EP7 `aprobar_calidad`
- Journal lateral de la última acción con `Quality Inspection` y `Stock Entry` resultantes

### Comportamiento del drawer

- Si el veredicto es **Approved**, el botón principal ejecuta liberación y muestra toast success.
- Si el veredicto es **Rejected**, registra la inspección y deja el stock en cuarentena.
- Los parámetros se serializan como mapa JSON `nombre -> valor`, alineado con el backend actual.

## Axios Client (`client.js`)

- **Base URL**: `/api` (proxy por Vite en dev)
- **Credentials**: `withCredentials: true` (cookies `sid`)
- **Request interceptor**: Convierte `object` a `URLSearchParams` (Frappe requiere form-urlencoded)
- **Response interceptor**: Desenvuelve `response.data.message` (sobre Frappe)
- **Headers anti-cache**: `Cache-Control: no-store` y `Pragma: no-cache` para reducir estados inconsistentes entre navegadores
- **CSRF**: Deshabilitado server-side via `exempt_csrf()` → no se envía token

## Patrón Scanner USB HID

Los escáneres de código de barras USB se comportan como un teclado: envían caracteres uno por uno vía eventos `keydown` y terminan con `Enter`.

```
┌──────────────┐    keydown 'O'     ┌─────────────┐
│  USB Scanner  │───────────────────▶│  buffer += c │
│  emulates     │    keydown 'P'     │  resetTimer  │
│  keyboard     │───────────────────▶│  (80ms gap)  │
│               │    keydown Enter   │              │
│               │───────────────────▶│  → trigger() │
└──────────────┘                     └─────────────┘
```

**Implementación** (en `LoginQR.vue` y `PokaYokeScanner.vue`):

1. `keydown` listener en `window` (montado con `onMounted`, limpiado con `onUnmounted`)
2. Buffer acumula caracteres; timer de 80ms resetea si hay pausa larga
3. `Enter` → llama handler con buffer completo → reset buffer
4. Guard `manualOpen` pausa el listener cuando el modal manual está visible

## LoginQR — Modos de Entrada

### Modo 1: Escáner USB (por defecto)
- Pantalla completa con animación de escaneo
- El escáner envía el token via `keydown` + `Enter`
- 5 estados visuales: idle → scanning → loading → success / error
- Si el navegador ya tiene un `sid` válido, la vista restaura la sesión y redirige automáticamente a `/hub`

### Modo 2: Entrada Manual (Plan B)
- Botón "Saisie Manuelle" abre modal via `<Teleport to="body">`
- Input con auto-focus + botones Annuler / Valider
- `manualOpen = true` pausa el listener del escáner
- Mismo pipeline `handleLogin()` que el escáner

## TareasList — Lista de Work Orders

Pantalla principal post-login. Consume EP2 con `company` y `warehouse` del store Pinia.

### Características
- Llama `getTareas(company, warehouse)` en `onMounted`
- Tarjetas gigantes con: nombre del producto, cantidad pendiente (font 5xl), badge de estado, indicador de stock de materiales
- Botón "DÉMARRER LA PRODUCTION ▶" por tarjeta → navega a `/poka-yoke/:workOrder`
- Estados: loading (spinner), error (con "Réessayer"), empty (mensaje)
- Botón refresh (↻) en header + botón Déconnexion
- Atajos extra: botón `Modules` para volver al hub y botón `Laboratoire` para saltar a QC

### Indicador de Stock
- **✓ Stock complet** (verde): todos los materiales tienen `suficiente: true`
- **⚠ Stock insuffisant** (ámbar): al menos un material sin stock suficiente

## PokaYokeScanner — Validación de Materiales

Pantalla crítica de validación Poka-Yoke. Carga materiales de la WO via EP2, luego valida cada escaneo via EP3.

### Flujo
1. `onMounted` → carga tarea via `getTareas()` → filtra por `workOrder` → construye checklist con `status: 'pending'`
2. Escáner USB captura QR → `handleScan(qrData)` → llama EP3 `validarMaterial()`
3. Si EP3 `valido: true` → marca material matching como `'validated'` → flash verde en la card
4. Si EP3 `valido: false` → overlay rojo STOP pantalla completa (Teleport)
5. Cuando todos los materiales están validados → botón pulsante "FINALISER LE MÉLANGE ✓"
6. Click "FINALISER" → modal de ajuste de consumo (EP4):
   - **Fase `asking`**: Diálogo "Consommation standard ou extra ?" con 2 botones h-16 (emerald "NON, standard" / amber "OUI, extra")
   - **Fase `extras`**: Lista scrollable de ingredientes con inputs numéricos `qty_extra` por material, botón "Valider et Enregistrer"
   - **Fase `submitting`**: Overlay con spinner
  - **Fase `success`**: Overlay fullscreen emerald-700 "LOT TERMINÉ — Placer en zone de Quarantaine" con redirect automático a `/tareas` tras 3s. Si hay alerta de desviación >10%, se muestra un banner amber.
   - **Fase `error`**: Overlay fullscreen rose-700 con "Réessayer" y "Annuler"

### Contrato EP4 desde la vista

- `buildLotesUsados()` construye un mapa `item_name -> batch_no` a partir de `scanResult.batch_no`.
- Para materiales no loteados envía `SIN-LOTE`.
- `submitExtras()` construye un mapa `item_name -> qty_extra` solo con materiales cuyo extra sea `> 0`.
- `confirmStandard()` llama EP4 con `consumosExtra = {}`.
- EP4 ya no es un cierre “soft”: al responder `success`, la WO queda sincronizada con ERPNext y el producto terminado entra en `Cuarentena PT`.

### UX Semafórica
- **Verde**: Material validado → card pasa a fondo `green-50`, icono ✓ verde, flash `scale-[1.02]` durante 1.5s
- **Rojo STOP**: Error → overlay `fixed inset-0` rojo con mensaje en `text-3xl`, botón FERMER. Para `alerta_nivel: 'CRITICO'` → overlay pulsa (`animate-pulse`)
- **Barra de estado**: zona inferior con colores por estado (slate=ready, blue=scanning, amber=loading, green=success)

### Checklist de Ingredientes
- Cada material muestra: número ordinal, `item_name`, `qty_requerida` + `uom`, badge stock
- Al validar: icono cambia a ✓ verde, se muestra `batch_no` del lote escaneado
- Contador en header: `validatedCount / materials.length`

### Entrada Manual
- Botón "⌨ Saisie Manuelle" abre modal (Teleport)
- Input con auto-focus (`watch` + `nextTick`), placeholder `CODE|LOT`
- `manualOpen = true` pausa el listener del escáner USB
- Mismo pipeline `handleScan()` que el escáner

### Guards del Scanner
- `if (manualOpen.value) return` — pausa durante entrada manual
- `if (scanState.value === 'error') return` — ignora scans durante overlay rojo (debe cerrar primero)

## PWA Config

Manifest generado por `vite-plugin-pwa`:

```js
{
  name: 'GCMA Kiosque Opérateur',
  short_name: 'Kiosque',
  display: 'standalone',
  orientation: 'portrait',
  theme_color: '#1e40af',
  background_color: '#0f172a'
}
```

## Estilos Industriales (`style.css`)

```css
@import "tailwindcss";

html { font-size: 18px; }         /* Legibilidad en tablet industrial */
body {
  touch-action: manipulation;      /* Sin double-tap zoom */
  user-select: none;               /* Sin selección accidental */
  min-height: 100dvh;              /* Viewport dinámico */
}
```

Además ahora incluye:

- fondo multicapa con gradientes sutiles
- clase `glass-panel` para bloques premium
- overrides dark para `p-card`, `p-button`, `p-inputtext`, `p-inputnumber`, `p-textarea`, `p-drawer`, `p-selectbutton` y `p-toast`
- visual language consistente entre producción y laboratorio sin depender de estilos inline improvisados

## Proxy Vite (Desarrollo)

```js
// vite.config.js
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8080',    // Docker nginx
      changeOrigin: true,
      cookieDomainRewrite: { '*': '' }    // Cookies funcionen en localhost
    }
  }
}
```
