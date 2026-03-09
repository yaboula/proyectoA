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
