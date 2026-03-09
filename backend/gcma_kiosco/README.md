# GCMA Kiosco — Custom Frappe App

App custom para la fábrica química GCMA. Contiene:
- **Seed Data** del PoC Sandbox (Data Foundation §3.1)
- **API REST** del Kiosco de operarios (Bloque 3 FSD) — *en desarrollo*
- **Event hooks** para Server Scripts de QC/Stock (futuro)

## Instalación en Docker

```bash
# 1. Copiar el código al contenedor (o montar como volumen)
docker cp backend/gcma_kiosco frappe-bench:/home/frappe/frappe-bench/apps/

# 2. Entrar al contenedor
docker exec -it frappe-bench bash

# 3. Instalar la app en el site
cd /home/frappe/frappe-bench
bench --site tu-site.local install-app gcma_kiosco

# 4. Ejecutar el Seed Data
bench --site tu-site.local execute gcma_kiosco.setup.seed_data.run

# 5. (Después de cargar precios) Submittear la BOM
bench --site tu-site.local execute gcma_kiosco.setup.seed_data.submit_bom
```

## Alternativa sin instalar la app

Si no quieres instalar como app formal, puedes copiar solo el script:

```bash
# Copiar el script al contenedor
docker cp backend/gcma_kiosco/gcma_kiosco/setup/seed_data.py \
  frappe-bench:/home/frappe/frappe-bench/apps/gcma_kiosco/gcma_kiosco/setup/

# Ejecutar directamente
bench --site tu-site.local execute gcma_kiosco.setup.seed_data.run
```

## Estructura del App

```
gcma_kiosco/
├── setup.py                          # Packaging Python
├── requirements.txt
├── README.md
└── gcma_kiosco/
    ├── __init__.py
    ├── hooks.py                      # Hooks de Frappe (after_install, doc_events, etc.)
    ├── modules.txt
    ├── patches.txt
    ├── setup/
    │   ├── __init__.py
    │   └── seed_data.py              # ★ Seed Data PoC (bench execute)
    └── api/
        ├── __init__.py
        └── kiosco.py                 # ★ Endpoints REST Kiosco (próximo módulo)
```

## Notas Arquitectónicas

- El seed es **idempotente**: se puede ejecutar N veces sin duplicar datos.
- La BOM se crea en **Draft** porque necesita precios cargados antes del Submit.
- Los almacenes se crean bajo el nodo padre que ERPNext genera automáticamente al crear la Company.
- Solo carga PDM (Pinturas). PEM se cargará con un script paralelo para garantizar el Guardrail G2 (paridad CoA).
