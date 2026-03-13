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

### Playwright E2E visible

El frontend `kiosco-pwa` incluye Playwright para automatizar flujos del kiosco viendo el navegador en pantalla.

Preparacion recomendada:

```bash
cd kiosco-pwa
npm run test:e2e:prepare-reception
```

Preparacion completa de Bloque 2:

```bash
cd kiosco-pwa
npm run test:e2e:prepare-block2
```

Ejecucion visible:

```bash
cd kiosco-pwa
npm run test:e2e:headed
```

Suite visible solo de Bloque 2:

```bash
cd kiosco-pwa
npm run test:e2e:block2:headed
```

Modo depuracion paso a paso:

```bash
cd kiosco-pwa
npm run test:e2e:debug
```

Notas:

- Playwright reutiliza o arranca el dev server Vite en `http://127.0.0.1:5173`.
- El backend Frappe debe seguir accesible en `http://localhost:8080` para que el proxy `/api` funcione.
- La suite `@block2` cubre recepcion parcial, cuarentena, reimpresion e inventario ciego.

### Smoke completo Bloque 2

Para validar backend/API de los tres sprints de inventario:

```bash
cd D:\proyectoA
./scripts/smoke/test-bloque-2.ps1
```

Cobertura actual:

- Sprint 4: `EP_REC_1` y `EP_REC_2` con verificacion de reload tras recepcion parcial.
- Sprint 5: `EP_REC_3`, rechazo por stock insuficiente y `EP_REC_4`.
- Sprint 6: `EP_REC_5` con inspeccion del `Stock Reconciliation` draft.

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
- También elimina `Quality Inspection` y `Stock Entry` de liberación QC creados durante Bloque 4.
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

### 6. Calidad: lotes en cuarentena vacíos aunque exista stock

**Síntoma**: `get_lotes_cuarentena` devuelve lista vacía o `aprobar_calidad` responde `NO_STOCK_IN_QUARANTINE`, pero `Bin` muestra stock en `Cuarentena PT - PDM`.

**Causa**: En ERPNext v16, para PT loteado el saldo por lote puede persistirse en `Serial and Batch Entry` / `Serial and Batch Bundle` mientras `Stock Ledger Entry.batch_no` queda `NULL`.

**Solución aplicada**:
```text
- Listado y validación de calidad calculan el saldo desde Serial and Batch Entry
- Se mantiene fallback a Stock Ledger Entry legacy sin bundle
- No usar SLE.batch_no como única fuente para Bloque 4
```

**Validación reproducida**:
```text
- GET calidad.get_lotes_cuarentena → devuelve LOTE-CHAOS-PT-001 con qty 5
- POST calidad.aprobar_calidad → crea Quality Inspection MAT-QA-2026-00001
- También crea Stock Entry MAT-STE-2026-00010 y mueve 1 unidad a Producto Terminado - PDM
```

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

---

## Smoke Suite Sprint 2

Script oficial de validación rápida para endpoints críticos:

`scripts/smoke/smoke-kiosco.ps1`

### Ejecución base (solo lectura, no destructiva)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke/smoke-kiosco.ps1
```

Cobertura base:

- EP1 `login_operario`
- EP1b `get_operario_session`
- EP2 `get_tareas`
- EP3 `validar_material`
- EP5 `info_lote`
- EP6 `get_lotes_cuarentena`

### Ejecución con operaciones de escritura (opt-in)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke/smoke-kiosco.ps1 \
  -IncludeWriteOps \
  -LotesUsadosJson '{"Résine Alkyde G-70":"LOTE-TEST-RES-001"}' \
  -ConsumosExtraJson '{}'
```

`-IncludeWriteOps` ejecuta EP4 y modifica documentos productivos de demo.

### Test focalizado de EP5 (contrato `info_lote`)

Para validar rapidamente el contrato de EP5 tras deploy backend:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke/test-ep5-info-lote.ps1
```

Cobertura:

- Caso positivo: lote + item correctos.
- Caso de error de contrato: item incorrecto para el lote (se acepta HTTP 422 esperado).

Para EP7 (inspección calidad), usar explícitamente:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke/smoke-kiosco.ps1 \
  -IncludeQualityWriteOps \
  -QualityDecision Rejected
```

### Convenciones de salida

- `PASS`/`FAIL` por endpoint.
- Exit code `0` si todo pasa.
- Exit code `1` si al menos una prueba falla.

### Smoke recepcion Sprint 4

## Sprint 11 - Portal B2B (operacion)

Variables sugeridas para E2E de tenant isolation:

```powershell
$env:PLAYWRIGHT_PORTAL_USER = "cliente.portal@example.com"
$env:PLAYWRIGHT_PORTAL_PASSWORD = "<secret>"
$env:PLAYWRIGHT_PORTAL_CUSTOMER = "CLI-DROG-0003"
$env:PLAYWRIGHT_PORTAL_OTHER_CUSTOMER = "CLI-DROG-0004"
```

Ejecucion del spec del portal:

```powershell
cd kiosco-pwa
npx playwright test tests/e2e/portal-b2b.spec.js --project=chromium --headed
```

Checks backend rapidos:

- `GET /api/method/maroc_b2b.api.comercial.get_portal_dashboard`
- `GET /api/method/maroc_b2b.api.comercial.get_portal_estado_cuenta`
- `POST /api/method/maroc_b2b.api.comercial.crear_pedido_portal`
- `POST /api/method/maroc_b2b.api.comercial.create_support_ticket`

Si aparece 403 en pruebas de fraude con `id_cliente` ajeno, el aislamiento de tenant esta funcionando como esperado.

## Sprint 12 - Operacion panel gerencial

Endpoints operativos:

- `GET /api/method/maroc_b2b.api.gerencial.get_panel_gerencial_360`
- `GET /api/method/maroc_b2b.api.gerencial.get_cobertura_mapa`
- `GET /api/method/maroc_b2b.api.gerencial.get_reporte_fotos_competencia`
- `GET /api/method/maroc_b2b.api.gerencial.export_scorecard_csv`
- `POST /api/method/maroc_b2b.api.gerencial.run_alerta_abandono_clientes`

Scheduler diario habilitado:

- Hook: `gcma_kiosco.api.gerencial.scheduler_alerta_abandono_clientes`
- Ejecuta alerta para fecha de referencia `hoy - 1 dia`.

Parametros de configuracion (site_config):

- `b2b_churn_days_default`: umbral global de abandono (default 40).
- `b2b_churn_days_by_tipo`: JSON con overrides por `tipo_drogueria`.

Ejemplo:

```json
{
  "b2b_churn_days_default": 40,
  "b2b_churn_days_by_tipo": {
    "Mayorista": 35,
    "Minorista": 45,
    "Distribuidor Regional": 50
  }
}
```

Script oficial del modulo de quai:

`scripts/smoke/test-ep-recepcion.ps1`

Cobertura:

- bootstrap sandbox de Purchase Order via `bench --site frontend execute gcma_kiosco.api.recepcion.bootstrap_recepcion_sandbox`
- EP_REC_1 `get_compras_pendientes`
- EP_REC_2 `registrar_recepcion`

Comando:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke/test-ep-recepcion.ps1 -PrepareSandbox
```

Notas operativas:

- EP_REC_2 crea `Quality Inspection` de entrada auto-generada si el item exige `inspection_required_before_purchase`.

### Smoke cuarentena Sprint 5

Script oficial del flujo de traslado y re-etiquetado:

`scripts/smoke/test-ep-cuarentena.ps1`

Cobertura:

- bootstrap sandbox de lote reusable via `bench --site frontend execute gcma_kiosco.api.recepcion.bootstrap_cuarentena_transfer_sandbox`
- EP5 `info_lote` sobre stock en `Cuarentena MP - PDM`
- EP_REC_3 happy path con `Material Transfer`
- EP_REC_3 rechazo de stock insuficiente (HTTP `422` esperado)
- EP_REC_4 `get_lote_para_impresion`

Comando:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke/test-ep-cuarentena.ps1 -PrepareSandbox
```

Notas operativas:

- Si el smoke responde con `404` o `417` en EP_REC_3 / EP_REC_4, el contenedor backend sigue cargando una version vieja de `recepcion.py`.
- En ese caso, copiar `backend/gcma_kiosco/gcma_kiosco/api/recepcion.py` y `backend/gcma_kiosco/gcma_kiosco/api/kiosco.py`, aplicar `chown frappe:frappe` y reiniciar `frappe_docker-backend-1`.
- Para este smoke puntual, el caso negativo se considera valido si la API rechaza con HTTP `422` aunque el body de error llegue vacio en PowerShell 5.1.
- El submit del `Purchase Receipt` se ejecuta con usuario sistema para permitir la autogeneracion nativa de lotes.
- El smoke actual valida backend HTTP; la impresion Zebra local sigue siendo una validacion manual o con mock local.

### Smoke inventario ciego Sprint 6

Script oficial del flujo de conteo ciego y borrador de reconciliacion:

`scripts/smoke/test-ep-inventario-ciego.ps1`

Cobertura:

- bootstrap sandbox de cinco lotes en `Materia Prima Aprobada - PDM` via `bench --site frontend execute gcma_kiosco.api.recepcion.bootstrap_inventario_ciego_sandbox`
- EP_REC_5 `subir_conteo_fisico`
- inspeccion del ultimo `Stock Reconciliation` draft via `gcma_kiosco.api.recepcion.inspect_latest_blind_inventory_reconciliation`

Comando:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke/test-ep-inventario-ciego.ps1 -PrepareSandbox
```

Notas operativas:

- El payload del smoke fuerza una sola diferencia real para que ERPNext persista exactamente una linea en el draft.
- Si todas las cantidades fisicas coinciden con `current_qty`, EP_REC_5 responde `422 NO_DIFFERENCES_FOUND`.
- Si el smoke devuelve `404` o `417`, verificar que `recepcion.py` actualizado haya sido copiado al contenedor backend antes de ejecutar.

---

## Release Readiness Bloque 1

### Flujo obligatorio pre-release

1. Sincronizar codigo en backend docker (si aplica) y reiniciar `backend-1` + `frontend-1`.
2. Ejecutar build frontend:

```powershell
cd kiosco-pwa
npm run build
cd ..
```

3. Ejecutar smoke suite base (read-only):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke/smoke-kiosco.ps1
```

4. Validar que no existan endpoints core en `FAIL`.
5. Si el release incluye cambios en EP4/EP7, correr smoke con write-ops controlados.
6. Registrar evidencia en:
  - `docs/releases/BLOQUE1_RELEASE_CHECKLIST.md`
  - `docs/releases/BLOQUE1_ACTA_CIERRE.md`

### Regla de liberacion

- Sin evidencia de build + smoke + criterios de salida, el release no se considera aprobado.

---

## Lecciones Aprendidas — Mobile / PWA

### L1 — `crypto.randomUUID()` requiere HTTPS

**Contexto**: La API `crypto.randomUUID()` es parte de la Web Crypto API y **solo está disponible en contextos seguros** (HTTPS o `localhost`). Cuando el kiosco se accede desde un móvil vía HTTP (`http://192.168.x.x:5173`), `crypto.randomUUID` es `undefined` y lanza `TypeError` silencioso.

**Impacto**: Cualquier función que la llame falla sin mensaje visible. En `LaboratoireQC.vue`, esto dejaba `parameterRows = []` (filas vacías, botón «Ajouter» sin efecto).

**Regla**: Nunca usar `crypto.randomUUID()` en código de la PWA. Usar contador simple (`let _seq = 0; function nextId() { return String(++_seq) }`) o `Date.now() + Math.random()`.

### L2 — PrimeVue Drawer no scrollea en móvil (Aura preset)

**Contexto**: PrimeVue 4.5 Aura preset aplica estilos con alta especificidad a `.p-drawer-content` que impiden `overflow-y: auto`. Los overrides CSS globales no siempre ganan esa batalla.

**Solución definitiva**: Usar el slot `#container` del Drawer, que cede control total del layout interno. Estructurar con `flex-col h-full` + header `shrink-0` + content `flex-1 min-h-0 overflow-y-auto` + footer `shrink-0`. El `min-h-0` es **crítico**: sin él, un flex child no limita su altura natural y el overflow no funciona.

**Regla**: Para cualquier panel lateral (Drawer/Sheet) con contenido variable en móvil, usar siempre el slot `#container` y construir el layout manualmente.

### L3 — iOS auto-scroll al foco en Drawer (PrimeVue)

**Contexto**: Al abrir un Drawer, PrimeVue enfoca el primer elemento interactivo para accesibilidad. En iOS, el navegador hace scroll automático para mostrar ese elemento, dejando el contenido anterior fuera del viewport.

**Solución**: `@show` hook + `nextTick(() => contentScrollRef.value.scrollTop = 0)` después de que el Drawer termina de abrirse.

### L4 — Tailwind JIT no detecta clases dinámicas interpoladas

**Contexto**: Clases como `` `max-w-${props.maxWidth}` `` no son detectadas por el scanner estático de Tailwind JIT. El CSS para esas clases nunca se genera — la clase aparece en el DOM pero sin efecto visual.

**Solución**: Usar lookup maps estáticos: `const widthMap = { '5xl': 'max-w-5xl', '6xl': 'max-w-6xl', '7xl': 'max-w-7xl' }` y acceder con `widthMap[props.maxWidth]`.

**Regla**: Nunca construir nombres de clases Tailwind con interpolación de string. Siempre usar el nombre completo o un lookup map.

### L5 — Breakpoints `xl:` en dispositivos medianos (768–1279px)

**Contexto**: Usar `xl:` (1280px) para cambiar a layout de 2 columnas deja tablets Android/iPad (768–1023px) en layout de 1 columna aunque tengan espacio de sobra.

**Regla**: Layouts de 2 columnas principales → `lg:` (1024px). `xl:` solo para ajustes finos de proporción. `sm:` (640px) obligatorio para grids de estadísticas y cards.
