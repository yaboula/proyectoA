# Sprint 01 - EP5 y Contratos API

Bloque: 1 - Nucleo Operativo y Confiabilidad
Duracion sugerida: 1 semana
Objetivo del sprint: cerrar el endpoint EP5 e integrarlo de forma usable en backend, wrapper y frontend.

## 1. Alcance

### In Scope

1. Implementacion backend de `info_lote` (EP5).
2. Wrapper frontend para EP5 en `kiosco.js`.
3. Integracion UI minima en vistas donde aporte valor operativo.
4. Documentacion API y changelog del nuevo endpoint.

### Out of Scope

1. Rediseño visual completo de vistas.
2. Refactor amplio no relacionado con EP5.
3. Nuevos modulos de inventario/comercial.

## 2. Historias Tecnicas

### H1 - Endpoint EP5 operativo

Como developer backend,
quiero exponer un endpoint `GET info_lote`
para consultar metadata de lote y stock,
con mensajes seguros y contrato estable.

Criterios de aceptacion:

1. Endpoint whitelisted implementado en `kiosco.py`.
2. Respuestas con envelope Frappe compatible y codigos de error coherentes.
3. Validaciones minimas de parametros y perfil permitido.

### H2 - Consumo frontend de EP5

Como developer frontend,
quiero consumir EP5 desde `kiosco.js`
para habilitar consulta rapida en pantallas de planta/lab.

Criterios de aceptacion:

1. Wrapper agregado y probado con payload real.
2. Al menos una vista usa la consulta con manejo de loading/error.
3. No rompe flujo actual de login/tareas/poka-yoke/lab.

### H3 - Contrato documentado

Como developer,
quiero API y frontend docs sincronizados
para evitar deriva documental.

Criterios de aceptacion:

1. `docs/API.md` actualizado con EP5.
2. `docs/FRONTEND.md` actualizado si hay UI nueva.
3. `CHANGELOG.md` registra la entrega del sprint.

## 3. Tareas Tecnicas

## Backend

1. Agregar `@frappe.whitelist()` para `info_lote`.
2. Definir input esperado:
   - `batch_no` (requerido)
   - `item_code` (opcional, para validacion cruzada)
3. Responder:
   - `batch_no`
   - `item_code`
   - `item_name`
   - `expiry_date`
   - `dias_restantes`
   - `stock_por_almacen[]`
   - `total_qty`
4. Errores controlados:
   - `MISSING_PARAMS`
   - `BATCH_NOT_FOUND`
   - `BATCH_ITEM_MISMATCH`
   - `INTERNAL_ERROR`

## Frontend

1. Agregar `getInfoLote(batchNo, itemCode?)` en `src/api/kiosco.js`.
2. Integrar en punto de uso (sugerido):
   - panel contextual en `PokaYokeScanner.vue` o `LaboratoireQC.vue`.
3. Mostrar estado:
   - loading
   - success
   - error FR

## Documentacion

1. `docs/API.md` seccion EP5 con request/response/errores/curl.
2. `docs/FRONTEND.md` seccion de consumo EP5 si hay UI.
3. `CHANGELOG.md` entrada de version.

## 4. Definicion de Terminado del Sprint

1. Endpoint EP5 usable desde frontend.
2. Flujo principal sin regresiones visibles.
3. Build frontend en verde.
4. Documentacion sincronizada.

## 5. Pruebas

### Manuales minimas

1. `batch_no` valido devuelve data consistente.
2. `batch_no` inexistente devuelve error funcional.
3. `item_code` incorrecto con batch valido devuelve mismatch.
4. UI muestra respuesta y errores sin bloquear flujo.

### Tecnicas

1. Verificar `git diff` sin cambios accidentales.
2. Verificar request form-urlencoded donde aplique.

## 6. Riesgos del Sprint

- Riesgo de inconsistencia entre fuentes de stock por lote.
- Riesgo de latencia en consulta si se agregan joins costosos.

Mitigacion:

- Reutilizar patrones ya validados en `calidad.py` para saldos por lote.
- Mantener respuesta compacta para consumo operativo.

## 7. Entregables

1. Codigo EP5 backend.
2. Wrapper EP5 frontend.
3. Integracion visual minima.
4. Documentacion API/frontend/changelog.
