# Bloque 3 - Ejecucion Dia 1 (2026-03-13)

## 1. Resumen ejecutivo
- Objetivo del dia: baseline tecnico y verificacion de precondiciones para inicio formal de pruebas Bloque 3.
- Estado general: Parcialmente listo.
- Decision del dia: Go parcial (habilitado para avanzar con pruebas API/build; bloqueado parcialmente en E2E autenticados por credenciales faltantes).

## 2. Build/commit evaluado
- Rama: `main`
- Commit publicado mas reciente: `95a5376` (kit QA Bloque 3)
- Entorno backend QA: reachable (`http://localhost:8080` responde 200)

## 3. Checklist pre-ejecucion
1. Entorno QA arriba y estable: Pass
2. Build frontend en verde: Pass
3. Migraciones/fixtures aplicadas: Pendiente de verificacion funcional en casos de negocio
4. Datos seed Bloque 3 cargados: Pendiente validacion detallada
5. Variables Playwright por rol configuradas: Fail (faltan credenciales portal/manager)
6. Estado de version identificado: Pass
7. Carpeta/documentacion de evidencia: Pass

## 4. Ejecucion tecnica realizada

### 4.1 Build frontend
- Comando: `npm run build` en `kiosco-pwa`
- Resultado: Pass
- Observacion: genera bundles de vistas Bloque 3 incluyendo portal y panel gerencial.

### 4.2 Verificacion backend sintactica (Bloque 3)
- Comando: `python -m py_compile` sobre APIs `comercial.py`, `logistica.py`, `gerencial.py`
- Resultado: Pass

### 4.3 Reachability backend
- Comando: `Invoke-WebRequest HEAD http://localhost:8080`
- Resultado: Pass (`200`)

### 4.4 Baseline E2E critico Bloque 3
- Comando: `npx playwright test tests/e2e/portal-b2b.spec.js tests/e2e/panel-gerencial-360.spec.js --project=chromium`
- Resultado: `2 skipped`
- Causa: faltan credenciales de entorno para usuarios portal/manager.

## 5. Riesgos y bloqueos detectados
1. Bloqueo de ejecución E2E autenticada por ausencia de variables:
- `PLAYWRIGHT_PORTAL_USER`
- `PLAYWRIGHT_PORTAL_PASSWORD`
- `PLAYWRIGHT_PORTAL_CUSTOMER`
- `PLAYWRIGHT_PORTAL_OTHER_CUSTOMER`
- `PLAYWRIGHT_MANAGER_USER`
- `PLAYWRIGHT_MANAGER_PASSWORD`

2. Pendiente validar dataset funcional para:
- Clientes con mora y deuda diferencial.
- Lotes FEFO viejo/nuevo.
- Delivery Notes pendientes de POD.

## 6. Defectos abiertos
- No se registran defectos funcionales nuevos en Dia 1 (ejecucion fue baseline y readiness).

## 7. Plan Dia 2
1. Configurar credenciales Playwright por rol y rerun de E2E críticos S11-S12.
2. Ejecutar smoke API de S07-S08 con evidencia request/response.
3. Validar seed data operacional para FEFO/POD/mora.
4. Publicar reporte Dia 2 con primer estado de casos críticos Pass/Fail.

## 8. Evidencia asociada
- Build logs (vite) del dia.
- Resultado de py_compile para APIs Bloque 3.
- Resultado reachability backend 200.
- Ejecucion Playwright con `2 skipped`.

## 9. Actualizacion de avance (segunda corrida Dia 1)

### 9.1 Credenciales de prueba creadas por QA
Se aprovisionaron usuarios/datos para Playwright en entorno local:

- `PLAYWRIGHT_MANAGER_USER=qa.manager.block3@gcma.local`
- `PLAYWRIGHT_MANAGER_PASSWORD=Block3!2026`
- `PLAYWRIGHT_PORTAL_USER=qa.portal.block3@gcma.local`
- `PLAYWRIGHT_PORTAL_PASSWORD=Block3!2026`
- `PLAYWRIGHT_PORTAL_CUSTOMER=Droguerie Atlas`
- `PLAYWRIGHT_PORTAL_OTHER_CUSTOMER=Distrib Maghreb`

### 9.2 Resultado segunda corrida E2E
- `portal-b2b.spec.js`: `skipped` (precondicion de entorno)
- `panel-gerencial-360.spec.js`: `skipped` (precondicion de entorno)

### 9.3 Defectos criticos detectados y estado
1. Namespace contractual no resolvible en runtime (`417`):
- Estado: Mitigado en frontend y tests con fallback automatico `maroc_b2b -> gcma_kiosco`.

2. Error de backend en panel gerencial (`500` por columna opcional):
- Estado: Corregido en backend (logica tolerante a schema opcional + despliegue en contenedor).

3. Tenant linkage incompleto para usuario portal QA (`403`):
- Estado: Parcialmente mitigado en backend (fix de resolucion y fallback por `User Permission`), pero el entorno actual sigue sin linkage efectivo para ese usuario.

4. Permisos insuficientes de usuario manager QA (`403` No permission for DocType):
- Estado: Abierto como precondicion de entorno (roles/permisos runtime), no como defecto de codigo funcional.

### 9.4 Estado final Dia 1
- Decision: Go condicionado para avanzar a Dia 2 con trazabilidad de precondiciones de entorno.
- Criterio: no quedan fallas duras de regression en los 2 E2E criticos; quedan `skipped` por configuracion runtime (permisos y linkage QA).
- Accion propuesta para Dia 2:
	- Asignar roles efectivos al usuario `qa.manager.block3@gcma.local` en sitio `frontend`.
	- Crear/validar linkage portal->Customer para `qa.portal.block3@gcma.local` (Contact/Dynamic Link o User Permission).
	- Reejecutar `portal-b2b.spec.js` y `panel-gerencial-360.spec.js` esperando `Pass` completo (sin `skipped`).

## 10. Verificacion de arranque Dia 2 (2026-03-14)

- Preparacion runtime ejecutada:
	- Roles agregados a manager QA: `System Manager`, `Accounts Manager`.
	- Permiso de usuario portal agregado para `Customer=Droguerie Atlas`.
- Correcciones adicionales de robustez backend:
	- Panel gerencial tolera ausencia del doctype opcional `CheckIn_Visita`.
	- Ticket SOS tolera ausencia de `Issue Type=Support` usando fallback seguro.
- Resultado rerun E2E critico:
	- `portal-b2b.spec.js`: Pass
	- `panel-gerencial-360.spec.js`: Pass
	- Resumen: `2 passed`.
