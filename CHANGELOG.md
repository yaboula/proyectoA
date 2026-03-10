# Changelog

Todos los cambios notables del proyecto se documentan aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

## [0.4.0] — 2026-03-10

### Added

**Backend — Bloque 4 Control de Calidad**
- Nuevo módulo `gcma_kiosco.api.calidad` con endpoints nativos de laboratorio
- `get_lotes_cuarentena` lista lotes de PT con saldo positivo en `Cuarentena PT - PDM`
- `aprobar_calidad` crea `Quality Inspection` manual y, si aprueba, libera stock con `Stock Entry` `Material Transfer`
- El `Quality Inspection` queda enlazado al `Stock Entry Detail.quality_inspection`

**Backend — EP4 `reportar_consumo`**
- Endpoint POST para registrar consumo real de materiales al finalizar la mezcla
- Calcula desviaciones vs BOM teórica (cantidad, porcentaje)
- Alerta WARNING si algún material supera 10% de desviación
- Registra consumo como Comment en la Work Order con trazabilidad de documentos generados
- Recibe lotes usados y extras por `item_name` (guardrail G3 — nunca `item_code` visible en el Kiosco)
- Crea `Stock Entry` nativos `Material Transfer for Manufacture` y `Manufacture`
- Usa `SerialBatchCreation` nativo de ERPNext para materiales con lote y cierra la WO en `Completed`

**Frontend — Modal de Consumo (EP4) en PokaYokeScanner.vue**
- Diálogo "Standard ou Extra ?" con 2 botones fat-finger (emerald / amber)
- Formulario de extras: lista scrollable de ingredientes con inputs numéricos `qty_extra`
- Overlay de éxito: pantalla completa emerald "LOT TERMINÉ — Placer en zone de Quarantaine" con redirect 3s
- Overlay de error: pantalla completa rose con botón "Réessayer"
- Máquina de estados: idle → asking → extras → submitting → success / error
- Iconos lucide: Scale, PackageCheck

**Frontend — API Wrapper EP4**
- `reportarConsumo(workOrder, lotesUsados, consumosExtra)` en `kiosco.js` con `JSON.stringify` para serializar mapas como form-urlencoded

**Frontend — Hub + Laboratoire (Bloque 4)**
- PrimeVue activado globalmente con preset Aura dark y `ToastService`
- Nuevo `ModuleHub.vue` como entrada post-login para elegir Production / Laboratoire
- Nueva pantalla `LaboratoireQC.vue` con KPIs, búsqueda, cards de lotes y drawer de inspección
- El laboratorio consume EP6 `get_lotes_cuarentena` y EP7 `aprobar_calidad`
- El flujo de login ahora redirige al hub, no directamente a producción

### Changed
- `docs/API.md`: Documentación completa de EP4 (request, response, errores, curl)
- `docs/FRONTEND.md`: Flujo EP4, tabla de API wrappers
- `docs/RUNBOOK.md`: la demo contable ya no es manual; se verifica cierre automático con EP4
- `docs/API.md`: se documentan EP6/EP7 de Control de Calidad y la base URL `gcma_kiosco.api.calidad`
- `docs/RUNBOOK.md`: se añade la nota operativa de ERPNext v16 para lotes en cuarentena usando `Serial and Batch Entry`
- `gcma_kiosco.setup.test_data.run`: ahora resetea la demo y recrea un entorno repetible con fixtures de caos
- `gcma_kiosco.setup.test_data.run`: también limpia `Quality Inspection` y `Stock Entry` de liberación QC antes de reinyectar la demo
- `reportar_consumo`: añade guardrail `EXTRA_QTY_ABSURD` para bloquear errores groseros de tipeo en extras
- Sesión del kiosco: restauración desde cookie `sid`, logout explícito y headers anti-cache para evitar fallos entre navegadores
- `App.vue`, `main.js` y `style.css`: nueva shell visual con PrimeVue dark, fondo atmosférico y overrides profesionales de componentes
- `TareasList.vue`: añade navegación directa al hub y al módulo de laboratorio

### Fixed
- `aprobar_calidad`: el flujo rechazado ahora referencia el `Stock Entry` que originó el lote en cuarentena, evitando errores nativos de `Quality Inspection` sin referencia
- `get_lotes_cuarentena` y la validación de saldo por lote usan `Serial and Batch Entry` como fuente principal en ERPNext v16

## [0.3.0] — 2025-07-25

### Added

**Design System — Industrial Premium MES**
- Tema oscuro industrial (bg-slate-900 fondo, bg-slate-800 cards/headers)
- Paleta: emerald-600 (acción primaria), rose-600 (errores), amber-400 (warnings)
- Librería de iconos lucide-vue-next reemplaza todos los emoji y SVG inline
- Animaciones CSS: shake (error overlay), fade-in (modales), pulse-ring (finalizar)
- Reglas UX fat-finger: botones h-16 min, rounded-md (no rounded-2xl/3xl), select-none

### Changed

**Frontend — LoginQR.vue**
- Reescrito completo: tema oscuro, iconos lucide (ScanBarcode 64px, ShieldCheck, Loader2, etc.)
- Modal de saisie manuelle estilo shadcn (bg-slate-800, border-slate-700, rounded-md)
- Barra superior con ShieldCheck + versión
- Input font-mono, botón emerald "Valider" con ChevronRight

**Frontend — TareasList.vue**
- Reescrito completo: cards bg-slate-800 con border-slate-700/60 rounded-md
- Header bg-slate-800/80 con RefreshCw y LogOut (lucide icons)
- Badges de stock (emerald/amber) y estado (amber/slate) con bordes sutiles
- Botón h-16 bg-emerald-600 "DÉMARRER LA PRODUCTION" con icono Play
- Metadatos con iconos Beaker y Clock

**Frontend — PokaYokeScanner.vue**
- Reescrito completo: tema oscuro, checklist con cards bg-slate-800
- Error overlay: bg-rose-600 + animate-shake + TriangleAlert 80px + tap-to-dismiss (sin botón)
- Modal saisie manuelle estilo shadcn con X close button
- Checklist: CircleCheckBig para validados, badges rounded-md emerald/rose
- Scan status bar con iconos lucide (ScanBarcode, Loader2, CircleCheckBig)
- Botón "FINALISER LE MÉLANGE" con animate-pulse-ring y icono Check

**Instrucciones**
- Sección DESIGN SYSTEM añadida a context.instructions.md (paleta, iconos, UX, animaciones, patrones)

## [0.2.0] — 2026-03-09

### Added

**Frontend — TareasList.vue (EP2)**
- Tarjetas industriales gigantes con nombre del producto, cantidad pendiente, badge de estado
- Indicador de stock de materiales (✓ Stock complet / ⚠ Stock insuffisant)
- Botón "DÉMARRER LA PRODUCTION ▶" por tarjeta
- Estados: loading, error con retry, empty state
- Botón refresh + logout en header

**Frontend — PokaYokeScanner.vue (EP3)**
- Checklist de ingredientes con tracking local de validación
- Escáner USB HID con guard de modal y guard de error
- UX semafórica: flash verde por material, overlay rojo STOP pantalla completa
- Overlay CRITICO con `animate-pulse` para errores de seguridad (material incorrecto, lote caducado)
- Barra de estado coloreada (ready/scanning/loading/success)
- Entrada manual (Saisie Manuelle) con auto-focus
- Botón pulsante "FINALISER LE MÉLANGE ✓" cuando todos los materiales están validados
- Contador de progreso en header (X/Y validés)

### Changed
- `kiosco.js`: `getTareas()` ahora acepta `company` y `warehouse` como parámetros

## [0.1.0] — 2025-07-25

### Added

**Backend — Custom App `gcma_kiosco`**
- `seed_data.py`: 15 pasos idempotentes (UoMs, Companies, Warehouses, Items, BOM, Suppliers, Customers, Price Lists, Custom Fields, Test Employee)
- `test_data.py`: Stock artificial (2000 Kg/MP con LOTE-TEST-*) + Work Order MFG-WO-2026-00001
- EP1 `login_operario` — Autenticación por QR badge con sesión Frappe
- EP2 `get_tareas` — Work Orders pendientes con BOM explodida y stock
- EP3 `validar_material` — Poka-Yoke: material, lote, caducidad, stock
- `qr_utils.py` — Parser QR con separador `|` (contrato Zebra)
- `exempt_csrf()` — Hook `before_request` para eximir CSRF en rutas del kiosco
- `hooks.py` — Fixtures Custom Fields (`custom_qr_*`), before_request hook

**Frontend — PWA Kiosco**
- Scaffolding Vue 3 + Vite 7 + Tailwind CSS 4 + Pinia + Router
- `client.js` — Axios con interceptor form-urlencoded + desenvuelve Frappe envelope
- `kiosco.js` — Wrappers EP1/EP2/EP3
- `operario.js` — Store Pinia (sesión operario)
- `LoginQR.vue` — Escáner USB HID + modal de entrada manual (Plan B)
- `TareasList.vue` — Lista de Work Orders con materiales
- `PokaYokeScanner.vue` — Validación de materiales por QR
- PWA manifest (standalone, portrait, theme industrial)
- Estilos industriales (18px font, no zoom, no select, 100dvh)

**Documentación**
- `index.html` — Diseño funcional (bloques de análisis, inventario, aprovisionamiento)
- `technical-design-data-foundation.html` — Data Foundation + PoC Sandbox
- `docs/API.md` — Referencia completa de endpoints REST
- `docs/FRONTEND.md` — Arquitectura PWA, componentes, patrones
- `docs/RUNBOOK.md` — Operaciones Docker, deploy, troubleshooting
- `README.md` — Visión general del proyecto

**Infraestructura**
- Docker Compose con 9 contenedores (Frappe v16.10.10 + ERPNext v16.8.2)
- Empresa PoC: PDM (Peintures du Maroc), 6 almacenes lógicos
- Datos de prueba: Employee Ahmed Benali, badge OP-2026-BADGE-00042
- Git inicializado con `.gitignore` (excluye `frappe_docker/`, `node_modules/`, `dist/`)

### Fixed
- nginx 502 por Docker IP drift → reiniciar siempre `frontend-1` junto con `backend-1`
- `DataError` por Content-Type → interceptor convierte a `URLSearchParams`
- `CSRFTokenError` → `exempt_csrf()` hook desactiva CSRF para rutas del kiosco
