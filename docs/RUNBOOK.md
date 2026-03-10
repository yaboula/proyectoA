# Operations Runbook — GCMA Kiosco

## Entorno Docker

### Contenedores (9)

```
frappe_docker-backend-1       # Gunicorn (Frappe/ERPNext)
frappe_docker-frontend-1      # Nginx reverse proxy (:8080)
frappe_docker-queue-short-1   # Redis worker (short)
frappe_docker-queue-long-1    # Redis worker (long)
frappe_docker-scheduler-1     # Background scheduler
frappe_docker-websocket-1     # Socket.IO
frappe_docker-db-1            # MariaDB 10.6
frappe_docker-redis-cache-1   # Redis (cache)
frappe_docker-redis-queue-1   # Redis (queue)
```

**Site name**: `frontend`

### Comandos frecuentes

```bash
# Estado general
docker compose -f frappe_docker/docker-compose.yml ps

# Logs en tiempo real
docker logs -f frappe_docker-backend-1

# Consola Frappe (bench console)
docker exec -it frappe_docker-backend-1 \
  /home/frappe/frappe-bench/env/bin/python -c \
  "import frappe; frappe.connect(site='frontend'); <CODE>; frappe.db.commit()"

# Acceso MariaDB
docker exec -it frappe_docker-db-1 mariadb -u root -p123 -D _1bd3e0294da19198
```

---

## Deploy de Código Backend

Patrón probado para actualizar archivos del Custom App en Docker:

### 1. Copiar archivos

```bash
# Copiar un archivo
docker cp backend/gcma_kiosco/gcma_kiosco/api/kiosco.py \
  frappe_docker-backend-1:/home/frappe/frappe-bench/apps/gcma_kiosco/gcma_kiosco/api/kiosco.py

# Copiar hooks.py
docker cp backend/gcma_kiosco/gcma_kiosco/hooks.py \
  frappe_docker-backend-1:/home/frappe/frappe-bench/apps/gcma_kiosco/gcma_kiosco/hooks.py
```

### 2. Corregir ownership

```bash
docker exec --user root frappe_docker-backend-1 \
  chown -R frappe:frappe /home/frappe/frappe-bench/apps/gcma_kiosco/
```

### 3. Reiniciar contenedores

```bash
# SIEMPRE reiniciar AMBOS — frontend cachea la IP del backend
docker restart frappe_docker-backend-1 frappe_docker-frontend-1
```

> **IMPORTANTE**: Si solo reinicias `backend-1`, nginx puede seguir apuntando a la IP antigua del contenedor → Error 502.

---

## Ejecución de Seed Data

```bash
docker exec frappe_docker-backend-1 \
  /home/frappe/frappe-bench/env/bin/python -c \
  "import frappe; frappe.connect(site='frontend'); \
   from gcma_kiosco.setup.seed_data import run; run(); \
   frappe.db.commit()"
```

### Test Data (stock artificial + Work Order)

```bash
docker exec frappe_docker-backend-1 \
  /home/frappe/frappe-bench/env/bin/python -c \
  "import frappe; frappe.connect(site='frontend'); \
   from gcma_kiosco.setup.test_data import run; run(); \
   frappe.db.commit()"
```

### Qué hace `test_data.run`

- Resetea la demo previa: Work Orders de prueba, Stock Entries de test, Comments del kiosco y Job Cards ligadas.
- Reinyecta stock válido para happy path.
- Crea fixtures de caos:
  - `MP-RES-ALK-G70|LOTE-CHAOS-RES-EXP-001` → lote caducado
  - `PT-PIN-BLC-MAT-20L|LOTE-CHAOS-PT-001` → material equivocado con QR válido
- Crea una Work Order nueva de 50 cubetas en `In Process`.

### Matriz de caos recomendada

- Basura / badge de empleado: `OP-2026-BADGE-00042` → `INVALID_QR`
- Material equivocado: `PT-PIN-BLC-MAT-20L|LOTE-CHAOS-PT-001` → `WRONG_MATERIAL`
- Lote caducado: `MP-RES-ALK-G70|LOTE-CHAOS-RES-EXP-001` → `BATCH_EXPIRED`
- Batch inexistente: `MP-RES-ALK-G70|LOTE-INEXISTENTE-999` → `BATCH_NOT_FOUND`
- Batch cruzado: `MP-RES-ALK-G70|LOTE-TEST-PIG-001` → `BATCH_ITEM_MISMATCH`
- Item no loteado válido: `ENV-BID-20L-BLC|SIN-LOTE` → válido
- Consumo brutal en EP4: extra mayor que la cantidad teórica → `EXTRA_QTY_ABSURD`

### Demo contable automática (gerencia)

La preparación del entorno deja una WO limpia y EP4 ya ejecuta el cierre contable completo desde el kiosco.

Pasos recomendados:

1. Ejecutar `test_data.run` para regenerar `MFG-WO-2026-00001`.
2. Hacer el flujo kiosco completo: EP1 login, EP2 selección, EP3 validar los 7 materiales, EP4 finalizar.
3. Verificar en ERPNext:
  - Se creó un `Stock Entry` `Material Transfer for Manufacture` ligado a la WO.
  - Se creó un `Stock Entry` `Manufacture` ligado a la WO.
  - Ambos documentos quedaron en `docstatus = 1`.
  - La Work Order quedó en `Completed`.
  - `produced_qty = 50` y `consumed_qty/transferred_qty` se actualizaron en `required_items`.
  - El producto terminado entró en `Cuarentena PT - PDM`.

Verificación real ya reproducida en local:

- WO: `MFG-WO-2026-00001` → `Completed`
- Transfer: `MAT-STE-2026-00009`
- Manufacture: `MAT-STE-2026-00010`

---

## Troubleshooting — Problemas Conocidos

### 1. Error 502 Bad Gateway (nginx)

**Síntoma**: Llamada API devuelve 502. Logs de frontend muestran:
```
connect() failed (113: No route to host) to 172.21.0.X:8000
```

**Causa**: Docker asigna IPs dinámicas. Si `backend-1` se reinicia y cambia de IP, `frontend-1` mantiene la IP antigua en caché.

**Solución**:
```bash
docker restart frappe_docker-frontend-1
# O mejor, reiniciar ambos a la vez:
docker restart frappe_docker-backend-1 frappe_docker-frontend-1
```

### 2. `DataError: Invalid request body`

**Síntoma**: POST a endpoint Frappe devuelve error de cuerpo inválido.

**Causa**: Frappe `@whitelist()` endpoints esperan `application/x-www-form-urlencoded`. Si envías `application/json`, falla.

**Solución**: El interceptor de Axios en `client.js` convierte objetos a `URLSearchParams` automáticamente.

### 3. `CSRFTokenError`

**Síntoma**: POST devuelve `CSRFTokenError` en `exc_type`.

**Causa**: La PWA se sirve desde un origen diferente al de Frappe (ej. `localhost:5173` vs `localhost:8080`). Nunca recibe la cookie `csrf_token`.

**Solución**: Hook `before_request` en `hooks.py` llama a `exempt_csrf()` que desactiva CSRF para rutas `gcma_kiosco.*`. Los endpoints siguen protegidos por sesión `sid`.

**NOTA**: `frappe.auth.get_logged_user` NO está whitelisted en Frappe v16.10.10 — no sirve para obtener CSRF desde el frontend.

### 4. Vite HMR crash al editar `vite.config.js`

**Síntoma**: Error `TypeError: Cannot set properties of undefined (setting 'error')` en Vite 7.3.

**Causa**: El HMR no puede recargar la propia configuración de Vite.

**Solución**: Detener el dev server (`Ctrl+C`) y reiniciar manualmente con `npm run dev`.

### 5. Un navegador entra y otro no mantiene la sesión

**Síntoma**: En un navegador el operario entra correctamente y en otro reaparece login o errores de carga al volver a la lista.

**Causa**: El store frontend era volátil y dependía solo del estado en memoria. Al recargar o volver desde otra pestaña, la PWA podía perder contexto aunque la cookie `sid` siguiera viva, o intentar reutilizar una sesión expirada.

**Solución aplicada**:
```text
- EP1b get_operario_session restaura el contexto del operario desde la cookie sid
- EP1c logout_operario cierra la sesión Frappe del navegador actual
- El store guarda operario en sessionStorage y rehidrata antes de entrar a rutas protegidas
- El cliente Axios envía cabeceras no-cache
```

**Recomendación operativa**: usar siempre `Quitter` para cerrar la sesión del kiosco antes de cambiar de navegador o de operario.

### 5. Stock no aparece por lote (Batch)

**Síntoma**: `Stock Ledger Entry` tiene `batch_no = NULL` aunque el Stock Entry especifica batch.

**Causa**: En ERPNext v16, el Item requiere `has_batch_no = 1` para que el SLE registre el batch. Si el Item no tiene este flag, el batch se ignora silenciosamente.

**Solución**: Consultar stock vía tabla `Bin` (que siempre refleja `actual_qty` correcta), no vía SLE.

---

## Test API manual

### Login

```bash
curl -X POST http://localhost:8080/api/method/gcma_kiosco.api.kiosco.login_operario \
  -d "qr_token=OP-2026-BADGE-00042"
```

Guardar el `sid` de la respuesta.

### Tareas

```bash
curl -s "http://localhost:8080/api/method/gcma_kiosco.api.kiosco.get_tareas?\
company=Peintures+du+Maroc+SARL" \
  -b "sid=<session_id>"
```

### Validar Material

```bash
curl -X POST http://localhost:8080/api/method/gcma_kiosco.api.kiosco.validar_material \
  -b "sid=<session_id>" \
  -d "work_order=MFG-WO-2026-00001" \
  -d "qr_data=MP-RES-ALK-G70|LOTE-TEST-RES-001"
```

### Finalizar Producción

```bash
curl -X POST http://localhost:8080/api/method/gcma_kiosco.api.kiosco.reportar_consumo \
  -b "sid=<session_id>" \
  -d "work_order=MFG-WO-2026-00001" \
  -d 'lotes_usados={"Résine Alkyde G-70":"LOTE-TEST-RES-001","Dioxyde de Titane R-902":"LOTE-TEST-PIG-001","White Spirit Standard":"LOTE-TEST-SOL-001","Eau Déminéralisée":"LOTE-TEST-H2O-001","Seau Plastique 20L Blanc":"SIN-LOTE","Couvercle Seau 20L":"SIN-LOTE","Étiquette Peinture Blanche Mate 20L":"SIN-LOTE"}' \
  -d "consumos_extra={}"
```

### Desde dentro del contenedor (sin proxy)

```bash
docker exec frappe_docker-backend-1 \
  curl -s -X POST http://localhost:8000/api/method/gcma_kiosco.api.kiosco.login_operario \
  -H "Host: frontend" \
  -d "qr_token=OP-2026-BADGE-00042"
```

---

## Rutas Importantes en el Contenedor

| Ruta | Contenido |
|------|-----------|
| `/home/frappe/frappe-bench/` | Raíz del bench |
| `/home/frappe/frappe-bench/apps/gcma_kiosco/` | Custom App |
| `/home/frappe/frappe-bench/env/` | Python virtualenv |
| `/home/frappe/frappe-bench/sites/frontend/` | Site config |
| `/home/frappe/frappe-bench/logs/` | Logs de Frappe |

---

## Checklist Pre-Deploy

- [ ] `kiosco.py` copiado y con ownership correcta
- [ ] `hooks.py` copiado si hubo cambios en hooks
- [ ] Ambos contenedores reiniciados (`backend-1` + `frontend-1`)
- [ ] Test EP1 login OK desde curl
- [ ] Test EP2/EP3 OK con sesión activa
- [ ] `npm run build` compila sin errores en `kiosco-pwa/`
