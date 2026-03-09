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
| vite-plugin-pwa | 1.2 | Service Worker + manifest |

## Estructura

```
kiosco-pwa/src/
├── api/
│   ├── client.js        # Axios instance (baseURL, interceptors)
│   └── kiosco.js        # Wrappers tipados EP1/EP2/EP3
├── stores/
│   └── operario.js      # Pinia store — sesión del operario
├── router/
│   └── index.js         # 3 rutas + navigation guard
├── views/
│   ├── LoginQR.vue      # Pantalla de login (escáner + modal manual)
│   ├── TareasList.vue   # Lista de Work Orders
│   └── PokaYokeScanner.vue  # Validación de materiales
├── App.vue              # Shell: solo <RouterView />
├── main.js              # Punto de entrada (app + pinia + router)
└── style.css            # Tailwind import + overrides industriales
```

## Rutas

| Path | Componente | Meta | Lazy |
|------|-----------|------|------|
| `/` | `LoginQR` | `{ guest: true }` | No |
| `/tareas` | `TareasList` | — | Sí |
| `/poka-yoke/:workOrder` | `PokaYokeScanner` | `props: true` | Sí |

### Navigation Guard

```js
router.beforeEach((to) => {
  const store = useOperarioStore()
  if (!to.meta.guest && !store.isLoggedIn) return '/'
})
```

Redirige a login si no hay sesión, excepto rutas con `meta.guest`.

## Estado (Pinia)

### `operario` store

| Propiedad | Tipo | Descripción |
|-----------|------|-------------|
| `operario` | object \| null | Datos del empleado (de EP1) |
| `sid` | string \| null | Session ID de Frappe |

| Getter | Retorna |
|--------|---------|
| `isLoggedIn` | `!!sid` |
| `fullName` | `operario.full_name` |

| Action | Descripción |
|--------|-------------|
| `login(qrToken)` | Llama EP1, guarda operario + sid |
| `logout()` | Limpia estado, redirige a `/` |

## Axios Client (`client.js`)

- **Base URL**: `/api` (proxy por Vite en dev)
- **Credentials**: `withCredentials: true` (cookies `sid`)
- **Request interceptor**: Convierte `object` a `URLSearchParams` (Frappe requiere form-urlencoded)
- **Response interceptor**: Desenvuelve `response.data.message` (sobre Frappe)
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

### Modo 2: Entrada Manual (Plan B)
- Botón "Saisie Manuelle" abre modal via `<Teleport to="body">`
- Input con auto-focus + botones Annuler / Valider
- `manualOpen = true` pausa el listener del escáner
- Mismo pipeline `handleLogin()` que el escáner

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
