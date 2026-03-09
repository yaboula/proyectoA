# Changelog

Todos los cambios notables del proyecto se documentan aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

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
