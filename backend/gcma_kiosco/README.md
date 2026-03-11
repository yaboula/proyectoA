# GCMA Kiosco - Custom Frappe App

App custom para la fabrica quimica GCMA.

Incluye:

- Seed data idempotente del PoC
- API REST del kiosco de operarios
- API REST del laboratorio de calidad
- Hook `before_request` para exencion CSRF en rutas `gcma_kiosco.*`

## Estado actual

Endpoints de produccion implementados:

- EP1 `login_operario`
- EP1b `get_operario_session`
- EP1c `logout_operario`
- EP2 `get_tareas`
- EP3 `validar_material`
- EP4 `reportar_consumo`
- EP5 pendiente

Endpoints de calidad implementados:

- EP6 `get_lotes_cuarentena`
- EP7 `aprobar_calidad`

## Estructura

```text
backend/gcma_kiosco/
  gcma_kiosco/
    api/
      kiosco.py
      calidad.py
      qr_utils.py
      _kiosco_architecture.py
    setup/
      seed_data.py
      test_data.py
      setup_admin_profile.py
    hooks.py
```

## Instalacion en entorno Docker/Frappe

```bash
# Copiar app al contenedor
docker cp backend/gcma_kiosco frappe_docker-backend-1:/home/frappe/frappe-bench/apps/

# Ajustar ownership
docker exec --user root frappe_docker-backend-1 \
  chown -R frappe:frappe /home/frappe/frappe-bench/apps/gcma_kiosco

# Instalar app en el site
docker exec -it frappe_docker-backend-1 bash
cd /home/frappe/frappe-bench
bench --site frontend install-app gcma_kiosco
```

## Seed y entorno de prueba

```bash
# Seed principal
docker exec frappe_docker-backend-1 \
  /home/frappe/frappe-bench/env/bin/python -c \
  "import frappe; frappe.connect(site='frontend'); from gcma_kiosco.setup.seed_data import run; run(); frappe.db.commit()"

# Test data (reset + caos + WO)
docker exec frappe_docker-backend-1 \
  /home/frappe/frappe-bench/env/bin/python -c \
  "import frappe; frappe.connect(site='frontend'); from gcma_kiosco.setup.test_data import run; run(); frappe.db.commit()"
```

## Notas tecnicas

- API contractual en `application/x-www-form-urlencoded`.
- Respuestas bajo sobre Frappe `{ "message": ... }`.
- Guardrail G3: no exponer `item_code` al operario en vistas de produccion.
- Mensajeria operativa en frances para terminal de planta.
