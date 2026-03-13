# Sprint 06 - Inventario Ciego por Código de Barras

Estado: Terminado (Done)

Bloque: 2 - Operación de Inventario de Planta
Duración sugerida: 1 semana
Objetivo del sprint: Proveer a los supervisores de almacén una herramienta rápida en la PWA para hacer recuentos físicos periódicos (Inventario Ciego) escaneando masivamente etiquetas Zebra y conciliando las diferencias contra ERPNext de forma automática.

---

## 1. Alcance (Scope)

### In Scope
1. **[Backend]** Endpoint para iniciar un ciclo de inventario (`Stock Reconciliation`). `EP_REC_5`.
2. **[Frontend]** Interfaz de "Conteo Físico" hiper optimizada para lectura continua de códigos QR.
3. **[Frontend]** Lógica de persistencia pesada (Pinia/IndexedDB) ya que un recuento puede durar horas y tomar cientos de códigos.
4. **[Integración]** Flujo de cierre y envío asíncrono hacia ERPNext.

### Out of Scope
1. Manejo de inventario por Ubicación (Bin level routing). Asumiremos conteo global por `Warehouse` para simplificar la primera fase de operación marroquí.
2. Autorizaciones multi-nivel (el conteo se sube y un manager lo aprueba en el backend clasico de Frappe, el Kiosco no aprueba).

---

## 2. Historias Técnicas y Especificaciones (Para Developers)

### HT1 - Interfaz PWA de "Recuento Rápido" (Continuous Scanning)
**Como** operario de almacén, **quiero** una pantalla donde la cámara no se apague nunca **para** poder "pistolear" (escanear) 50 tambores en menos de 2 minutos.

*   **Ruta Vue:** `/inventario-ciego`
*   **Componentes:**
    *   Reutilización de `useScanner` **sin el debounce de validación de backend**.
    *   **Importante:** A diferencia de Producción (EP3) donde cada scan hace un POST al servidor, el inventario ciego es **100% OFFLINE**.
    *   La lectura del QR PokaYoke (`QA,ITEM_CODE|BATCH_NO`) parsea el código y lo suma a la lista local. Si un tambor no tiene ZPL, se permite ingreso manual via `ManualInputModal`.
    *   La agrupación se hace en UI: "Materia Prima A - Lote X: 3 tambores escaneados".

### HT2 - Backend: `subir_conteo_fisico` (EP_REC_5)
**Como** developer backend, **quiero** recibir un mega-payload con todo lo escaneado **para** compararlo contra el sistema mediante un `Stock Reconciliation`.

*   **Archivo:** `gcma_kiosco/api/recepcion.py` (o módulo nuevo `api/inventario.py`)
*   **Contrato:**
    *   **Input (POST):** `warehouse` (str), `conteo` (Array de `{item_code, batch_no, qty_fisica}`).
    *   **Lógica Frappe:**
        1. Utilizar un script para generar un borrador (Draft) de Documento tipo `Stock Reconciliation`.
        2. Configurar "Purpose: Stock Reconciliation".
        3. Popular la tabla `items` con las lecturas. El sistema calculará la diferencia (`qty_diff`) contra el stock del sistema internamente.
        4. Guardar (`doc.insert()`), pero **NO `doc.submit()`**. El ajuste contable lo aprueba finanzas/gerencia en el backend.
    *   **Output JSON:** `{ "success": true, "reconciliation_doc": "MAT-REC-2026-0001" }`

### HT3 - Store de Sync Ciego (PWA)
**Como** tech lead, **quiero** asegurar que el array estructurado de conteo no se pierda por RAM constraints de la tablet **para** no obligar al operario a re-hacer horas de recuento.

*   **Archivo:** `stores/blindInventory.js`
*   Reutilizar `pinia-plugin-persistedstate`.
*   Guardar map: `{ 'WAREHOUSE_A': [ {item, batch, qty}... ] }`.

---

## 3. Matriz de Riesgo y Testeo (Definition of Done)

*   **Testing Requerido:**
    *   [x] Test Frontend: Pantalla `InventarioCiego.vue` compilada en verde y preparada para escaneo continuo local sin postback.
    *   [x] Smoke Test `EP_REC_5`: Ejecutado en verde creando `Stock Reconciliation` draft real inspeccionado en BD.
    *   [x] E2E Playwright `@block2` (inventario ciego) ejecutado en verde con corrida determinista (`--workers=1`) para evitar colisiones de fixtures compartidos.

## 5. Resultado implementado

- Backend operativo en `gcma_kiosco.api.recepcion` con EP_REC_5 `subir_conteo_fisico`.
- Conteo offline persistente por warehouse en `kiosco-pwa/src/stores/blindInventory.js`.
- Nueva vista `/inventario-ciego` accesible desde el modulo de recepcion.
- `syncQueue.js` ampliado para reintento diferido de `EP_REC_5_SUBIR_CONTEO`.
- Smoke `scripts/smoke/test-ep-inventario-ciego.ps1 -PrepareSandbox` ejecutado en verde.
- Cierre QA 2026-03-13: `scripts/smoke/test-bloque-2.ps1` y `npm run test:e2e:block2` completados en verde incluyendo el escenario de envio de borrador de reconciliacion.

## 4. Estructura de commits esperada

*   `feat(api): endpoint subir_conteo_fisico ep_rec_5 crea Stock Reconciliation`
*   `feat(pwa): store offline para conteo de inventario ciego`
*   `feat(pwa): pantalla fast-scanning de inventario sin postbacks`
*   `test(api): smoke creacion de document template draft`
