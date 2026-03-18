# GCMA Kiosque Opérateur — MES Industrial

> Digitalización de planta química en Marruecos — Sistema MES completo con ERPNext + PWA Vue.js. **v0.9.2**

## Visión General

Plataforma de **manufactura digitalizada** (MES) para una fábrica química en Marruecos (GCMA). Cubre cuatro dominios operativos completos:

| Dominio | Módulos | Estado |
|---------|---------|--------|
| **Producción** | Login QR, Tareas, Poka-Yoke materiales, Reporte consumos | ✅ MVP operativo |
| **Calidad** | Laboratorio QC, Inspección lotes cuarentena, Liberación | ✅ MVP operativo |
| **Recepción / Almacén** | Recepción MP, Cuarentena, Reimpresión etiquetas, Inventario ciego | ✅ MVP operativo |
| **Comercial B2B** | Rutas + GPS, Catálogo + carrito offline, Cobros, Picking FEFO, POD chofer, Portal cliente, Panel gerencial 360° | ✅ GO v0.8.10 |

---

## Arquitectura

```
┌──────────────────────────────────────────────────────────────┐
│                    Kiosco PWA (Vue 3)                        │
│  Producción · Calidad · Recepción · Comercial B2B · Portal   │
│  14 vistas · 10 componentes · 4 stores Pinia · Offline-first │
└────────────────────────┬─────────────────────────────────────┘
                         │  /api/method  (form-urlencoded)
                         ▼
┌──────────────────────────────────────────────────────────────┐
│            Docker — 9 contenedores                           │
│  backend-1 (Frappe/Gunicorn)  ·  frontend-1 (nginx :8080)   │
│  queue-short · queue-long · scheduler · websocket            │
│  db-1 (MariaDB 10.6)  ·  redis-cache  ·  redis-queue        │
│                                                              │
│  Custom App: gcma_kiosco                                     │
│  28 endpoints @frappe.whitelist  ·  3 DocTypes custom        │
│  Namespace alias: maroc_b2b → gcma_kiosco                    │
└──────────────────────────────────────────────────────────────┘
```

---

## Estructura del Proyecto

```
proyectoA/
├── .cursor/rules/            # Reglas Cursor (6 archivos .mdc)
├── .github/instructions/     # context.instructions.md para agente AI
├── .agents/rules/            # context.md
├── backend/
│   └── gcma_kiosco/          # Custom Frappe App (única)
│       └── gcma_kiosco/
│           ├── api/
│           │   ├── kiosco.py       # EP1-EP7: login, tareas, poka-yoke, consumo
│           │   ├── calidad.py      # EP6-EP7: cuarentena QC, aprobación
│           │   ├── recepcion.py    # EP_REC_1-5: recepción, cuarentena, etiquetas, inventario
│           │   ├── comercial.py    # S07-S11: rutas, checkin, catálogo, cobros, portal B2B, loyalty
│           │   ├── logistica.py    # S09-S10: pick list FEFO, override PIN, POD chofer
│           │   ├── gerencial.py    # S12: panel 360°, scorecard, mapa GPS, alerta churn
│           │   ├── qr_utils.py     # Parser QR (separador "|")
│           │   └── stock_utils.py  # Helpers stock v16 (Serial+Batch / SLE legacy)
│           ├── kiosco/doctype/
│           │   ├── check_in_visita/
│           │   ├── ruta_comercial_dia/
│           │   └── visitas_programadas/
│           └── setup/
│               ├── seed_data.py          # 15 pasos idempotentes
│               ├── test_data.py          # Stock + WO de prueba
│               └── setup_admin_profile.py
├── kiosco-pwa/               # Frontend PWA (Vue 3 + Vite + Tailwind)
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.js           # Axios + form-urlencoded + unwrap
│   │   │   ├── kiosco.js           # Wrappers EP1-EP7, recepción, logística
│   │   │   ├── customerPortal.js   # Wrappers B2B: catálogo, cobros, portal, loyalty
│   │   │   └── gerencial.js        # Wrappers S12: panel, mapa, CSV, alertas
│   │   ├── components/
│   │   │   ├── KioskLayout.vue         # Shell exterior global
│   │   │   ├── ScanStation.vue         # Estado del scanner
│   │   │   ├── ManualInputModal.vue    # Saisie manuelle
│   │   │   ├── FullScreenOverlay.vue   # Overlay error/success/loading
│   │   │   ├── EmptyState.vue          # Estado vacío
│   │   │   ├── ReceptionCaptureModal.vue
│   │   │   ├── CheckInModal.vue        # GPS check-in S07
│   │   │   ├── NetworkIndicator.vue    # Estado de red
│   │   │   ├── OverrideFEFOModal.vue   # Override FEFO con PIN encargado
│   │   │   └── CartePedidoModal.vue    # Carrito + bloqueo por mora S08
│   │   ├── composables/
│   │   │   └── useScanner.js
│   │   ├── stores/
│   │   │   ├── operario.js         # Sesión, perfil, módulos (sessionStorage)
│   │   │   ├── pokaYoke.js         # Estado flujo poka-yoke (localStorage)
│   │   │   ├── blindInventory.js   # Conteo offline por warehouse (localStorage)
│   │   │   └── syncQueue.js        # Cola offline diferida (localStorage)
│   │   ├── router/index.js         # 16 rutas con guards de sesión y módulo
│   │   ├── utils/
│   │   │   ├── qr.js
│   │   │   └── printer.js
│   │   └── views/                  # 15 vistas
│   │       ├── LoginQR.vue
│   │       ├── ModuleHub.vue
│   │       ├── TareasList.vue
│   │       ├── PokaYokeScanner.vue
│   │       ├── LaboratoireQC.vue
│   │       ├── ReceptionMateriaux.vue
│   │       ├── TransladoCuarentena.vue
│   │       ├── ReimpresionEtiqueta.vue
│   │       ├── InventarioCiego.vue
│   │       ├── RutaComercial.vue       # S07: hoja del día + check-in GPS
│   │       ├── CatalogoStock.vue       # S07: catálogo + carrito offline
│   │       ├── KioscoPickingFEFO.vue   # S09: picking dirigido FEFO
│   │       ├── AppChoferPOD.vue        # S10: firma + foto POD
│   │       ├── PortalB2BCliente.vue    # S11: portal droguería + loyalty
│   │       └── PanelGerencial360.vue   # S12: dashboard directivo
│   └── tests/e2e/              # Playwright (8 specs)
├── docs/
│   ├── API.md                  # 28 endpoints documentados con curl
│   ├── FRONTEND.md             # Arquitectura PWA completa
│   ├── RUNBOOK.md              # Docker, deploy, troubleshooting
│   ├── plan-v2/                # Planes de sprint S01-S12
│   └── qa/                     # Evidencias QA Bloque 1-3
├── scripts/
│   ├── smoke/                  # Scripts PowerShell de smoke test
│   ├── e2e/                    # Preparación sandboxes Playwright
│   └── manual/                 # Scripts Python auxiliares QA
├── frappe_docker/              # Docker Compose (.gitignored — upstream)
├── CHANGELOG.md
└── README.md
```

---

## Stack Tecnológico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| ERP | ERPNext | 16.8.2 |
| Framework | Frappe | 16.10.10 |
| Base de datos | MariaDB | 10.6 |
| Frontend | Vue 3 (Composition API) | 3.5.25 |
| Bundler | Vite | 7.3 |
| CSS | Tailwind CSS | 4.2 |
| Estado | Pinia + persistedstate | 3.0 |
| HTTP | Axios | 1.13 |
| PWA | vite-plugin-pwa | 1.2 |
| UI Industrial | lucide-vue-next | 0.577 |
| Mapas | Leaflet | 1.9 |
| Tests E2E | Playwright | 1.58 |
| Contenedores | Docker Compose | — |

---

## Endpoints Backend (28 total)

| Módulo | Base URL | Endpoints |
|--------|----------|-----------|
| Kiosco producción | `gcma_kiosco.api.kiosco` | EP1 login, EP1b sesión, EP1c logout, EP2 tareas, EP3 poka-yoke, EP4 consumo, EP5 info lote |
| Calidad | `gcma_kiosco.api.calidad` | EP6 lotes cuarentena, EP7 aprobar QC |
| Recepción | `gcma_kiosco.api.recepcion` | EP_REC_1 POs, EP_REC_2 receipt, EP_REC_3 traslado, EP_REC_4 impresión, EP_REC_5 inventario |
| Comercial B2B | `maroc_b2b.api.comercial` | S07 ruta+checkin+catálogo, S08 estado cuenta+cobro+pedidos, S11 portal+loyalty |
| Logística | `maroc_b2b.api.logistica` | S09 pick list+FEFO+override PIN, S10 entregas+POD |
| Gerencial | `maroc_b2b.api.gerencial` | S12 panel 360°+mapa+fotos+CSV+churn alert |

---

## Quick Start

### Requisitos
- Docker Desktop
- Node.js ≥ 18
- Git

### Backend (Docker)
```bash
cd frappe_docker
docker compose up -d              # 9 contenedores, ~2 min
# Primera vez — Seed data:
docker exec frappe_docker-backend-1 \
  /home/frappe/frappe-bench/env/bin/python -c \
  "import frappe; frappe.connect(site='frontend'); \
   from gcma_kiosco.setup.seed_data import run; run(); \
   frappe.db.commit()"
# Acceso: http://localhost:8080
```

### Frontend (PWA)
```bash
cd kiosco-pwa
npm install
npm run dev        # http://localhost:5173
npm run build      # build producción
```

### Credenciales de prueba
| Rol | Badge / User | Módulos |
|-----|-------------|---------|
| Operario producción | `OP-2026-BADGE-00042` (Ahmed Benali) | production |
| Inspector QC | `OP-2026-BADGE-00043` | quality |
| Responsable recepción | `OP-2026-BADGE-00044` | reception |

---

## Guardrails del CTO

| ID | Regla | Impacto |
|----|-------|---------|
| **G1** | `try/except` en todo endpoint + mensajes de error siempre en **francés** | Todo error visible al operario |
| **G2** | Chart of Accounts: paridad PDM = PEM | Seed data de PEM |
| **G3** | `item_code` **nunca** visible al operario — solo en QR interno | API + UI |

---

## Documentación

| Documento | Descripción |
|-----------|------------|
| [docs/API.md](docs/API.md) | 28 endpoints con request/response/errores/curl |
| [docs/FRONTEND.md](docs/FRONTEND.md) | Arquitectura PWA, componentes, stores, patrones |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | Docker, deploy, troubleshooting, lecciones aprendidas |
| [CHANGELOG.md](CHANGELOG.md) | Historial de versiones (Keep a Changelog) |

---

## Licencia

Proyecto interno GCMA — Uso privado.
