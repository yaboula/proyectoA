# GCMA Kiosque Opérateur

> Digitalización de planta química — Kiosco de producción para operarios con ERPNext + PWA Vue.js.

## Visión General

Sistema completo de **control de producción en planta** para una fábrica química en Marruecos (GCMA). Un kiosco industrial (tablet + pistola láser QR) permite a los operarios:

1. **Identificarse** escaneando su badge QR personal
2. **Ver sus órdenes de fabricación** pendientes con materiales y stock
3. **Validar materiales** (Poka-Yoke) escaneando QR de lotes antes de mezclar
4. **Reportar consumos** reales post-producción *(próximamente)*

## Arquitectura

```
┌─────────────────────┐     ┌──────────────────────────┐
│   Kiosco PWA        │     │   Docker (Frappe/ERPNext) │
│   Vue 3 + Vite      │────▶│   Backend API (Python)   │
│   Tailwind CSS      │ /api│   MariaDB + Redis        │
│   Pinia + Router    │◀────│   9 containers           │
└─────────────────────┘     └──────────────────────────┘
        Tablet                     Servidor local
```

## Estructura del Proyecto

```
proyectoA/
├── .github/instructions/     # Reglas para Copilot/agente
├── backend/
│   └── gcma_kiosco/          # Custom Frappe App
│       └── gcma_kiosco/
│           ├── api/
│           │   ├── kiosco.py         # EP1-EP5 endpoints REST
│           │   └── qr_utils.py       # Parser QR (separator "|")
│           └── setup/
│               ├── seed_data.py      # 15 pasos de datos semilla
│               └── test_data.py      # Stock + Work Order de prueba
├── kiosco-pwa/               # Frontend PWA
│   ├── src/
│   │   ├── api/              # Axios client + wrappers
│   │   ├── stores/           # Pinia (sesión operario)
│   │   ├── router/           # Vue Router (3 rutas)
│   │   └── views/            # LoginQR, TareasList, PokaYoke
│   └── vite.config.js        # Tailwind + PWA + proxy
├── frappe_docker/            # Docker Compose (upstream, .gitignored)
├── docs/                     # Documentación técnica
│   ├── API.md                # Referencia de endpoints
│   ├── FRONTEND.md           # Arquitectura PWA
│   └── RUNBOOK.md            # Operaciones y troubleshooting
├── index.html                # Documentación diseño funcional
└── technical-design-data-foundation.html
```

## Stack Tecnológico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| ERP | ERPNext | 16.8.2 |
| Framework | Frappe | 16.10.10 |
| Base de datos | MariaDB | 10.6 |
| Frontend | Vue 3 (Composition API) | 3.5 |
| Bundler | Vite | 7.3 |
| CSS | Tailwind CSS | 4.2 |
| Estado | Pinia | 3.0 |
| HTTP | Axios | 1.13 |
| PWA | vite-plugin-pwa | 1.2 |
| Contenedores | Docker Compose | - |

## Empresas del PoC

| Empresa | Abreviatura | Sector | Estado |
|---------|------------|--------|--------|
| GCMA | GCMA | Holding (padre) | Creada |
| Peintures du Maroc | PDM | Pinturas | PoC activo |
| Produits d'Entretien | PEM | Limpieza | Pendiente (G2) |

## Guardrails (Cicatrices del CTO)

| ID | Regla | Impacto |
|----|-------|---------|
| **G1** | Server Scripts: `try/except` + mensajes siempre en **francés** | Todo error visible al operario |
| **G2** | Chart of Accounts: paridad PDM = PEM | Seed data de PEM |
| **G3** | `item_code` **nunca** visible al operario — solo en QR | Toda la API y UI |

## Quick Start

### Requisitos
- Docker Desktop
- Node.js >= 18
- Git

### Backend (Docker)
```bash
cd frappe_docker
docker compose up -d              # 9 containers
# Seed data (primera vez):
docker exec frappe_docker-backend-1 \
  /home/frappe/frappe-bench/env/bin/python -c \
  "import frappe; frappe.connect(site='frontend'); \
   from gcma_kiosco.setup.seed_data import run; run(); \
   frappe.db.commit()"
```

### Frontend (PWA)
```bash
cd kiosco-pwa
npm install
npm run dev          # http://localhost:5173
```

### Test del login
Escanea o escribe manualmente: `OP-2026-BADGE-00042` → Ahmed Benali

## Documentación

| Documento | Descripción |
|-----------|------------|
| [docs/API.md](docs/API.md) | Referencia completa de endpoints REST |
| [docs/FRONTEND.md](docs/FRONTEND.md) | Arquitectura PWA, componentes, estado |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | Operaciones Docker, deploy, troubleshooting |
| [CHANGELOG.md](CHANGELOG.md) | Historial de cambios por versión |

## Licencia

Proyecto interno GCMA — Uso privado.
