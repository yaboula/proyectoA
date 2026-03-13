# Sprint 05 - Flujo de Cuarentena y Re-etiquetado

Estado: Terminado (Done)

Bloque: 2 - Operación de Inventario de Planta
Duración sugerida: 2 semanas
Objetivo del sprint: Completar el lado de inventario de planta permitiendo al personal de almacén/calidad re-gestionar lotes ingresados en cuarentena, hacer traslados internos documentados (Stock Entry) y re-imprimir etiquetas Poka-Yoke dañadas.

---

## 1. Alcance (Scope)

### In Scope
1. **[Backend]** Endpoints de Gestión de Cuarentena (Mover de Cuarentena a Stock General tras aprobación si Calidad no lo hace manual). `EP_REC_3`.
2. **[Backend]** Endpoint para re-impresión de QR (buscar por Item Code y extraer Batch). `EP_REC_4`.
3. **[Frontend]** Vista "Gestion Quarantaine" en la PWA.
4. **[Frontend]** Funcionalidad de "Re-imprimir QR" escaneando con la cámara o tipeando.
5. **[QA]** Smoke tests de movimiento de stock.

### Out of Scope
1. Devoluciones a proveedor (Purchase Return) desde el Kiosco. Ese flujo se mantiene en el backoffice de ERPNext por ser un proceso administrativo pesado.
2. Contrato de API con impresoras ajenas al servicio ZPL ya montado.

---

## 2. Historias Técnicas y Especificaciones (Para Developers)

### HT1 - Endpoint de Transferencia de Stock (EP_REC_3)
**Como** developer backend, **quiero** exponer `trasladar_lote_aprobado` **para** mover stock desde Cuarentena MP hacia Almacén General de Producción tras el OK de Control de Calidad.

*   **Archivo:** `gcma_kiosco/api/recepcion.py` (o `calidad.py` si centralizan).
*   **Contrato:**
    *   **Input (POST):** `item_code` (str), `batch_no` (str), `qty_to_move` (float), `source_warehouse` (str), `target_warehouse` (str).
    *   **Lógica Frappe:**
        1. Validar pre-condición: Saldo actual en `source_warehouse` a través de `stock_utils.get_stock_lote_almacen` debe ser `>= qty_to_move`.
        2. Crear un documento `Stock Entry` del tipo `"Material Transfer"`.
        3. Popular `from_warehouse` y `to_warehouse`.
        4. Agregar el ítem con su lote a detalle en la tabla `items` del Stock Entry.
        5. Evitar triggers manuales; ejecutar `doc.insert()` y `doc.submit()`.
    *   **Output JSON:** `{ "success": true, "stock_entry": "MAT-STE-2026-0005" }`

### HT2 - Endpoint Retrospectivo de Info de Etiqueta (EP_REC_4)
**Como** developer backend, **quiero** exponer `get_lote_para_impresion` **para** reconstruir los datos exactos que requiere la Zebra ZPL incluso si el recibo se hizo hace días.

*   **Archivo:** `gcma_kiosco/api/recepcion.py`
*   **Contrato:**
    *   **Input (GET):** `batch_no` (str)
    *   **Lógica Frappe:**
        - Buscar en tabla `Batch` de ERPNext.
        - Unir (JOIN lógico) con `Item` para sacar `item_name`.
        - Leer `expiry_date`.
    *   **Output JSON:**
        ```json
        {
          "success": true,
          "etiqueta": {
            "item_code": "PROD-102",
            "item_name": "Solvant Acrylique",
            "batch_no": "LOT-2026-081",
            "expiry_date": "2027-01-01"
          }
        }
        ```

### HT3 - UI Movimiento de Cuarentena (Frontend PWA)
**Como** operario de almacén, **quiero** una pantalla donde escanear un lote de cuarentena **para** trasladarlo a la estantería de MP aprobada.

*   **Ruta Vue:** `/traslado-cuarentena`
*   **Componentes:**
    *   Uso intensivo composable `useScanner` para lectura rápida.
    *   Layout con cards grandes y fuente hiper-legible.
    *   **Validación estricta UI:** Al escanear, llama a EP5 (`info_lote`) para verificar donde está el lote realmente. Si no está en "Cuarentena MP", bloquear el UI rojo con "Le lot n'est pas en quarantaine".
    *   **Acción:** Botón verde gigante "Transférer vers Stock General" que llama a EP_REC_3.

### HT4 - UI Re-impresión de Etiqueta (Frontend PWA)
**Como** operario, **quiero** poder re-imprimir una etiqueta si se rompió por humedad/químicos **para** mantener intacto el sistema Poka-Yoke de la fábrica.

*   **Ruta Vue:** `/reimpresion`
*   **Contrato de Acción:**
    - Input de `batch_no`.
    - Llama a EP_REC_4.
    - Repite llamada HTTP POST al servicio Node.js ZPL de la impresora usando la plantilla definida en HT4 del sprint anterior.

---

## 3. Matriz de Riesgo y Testeo (Definition of Done)

*   **Testing Requerido:**
    *   [x] Smoke Test `EP_REC_3`: Mover un lote que SI existe y saldo es suficiente.
    *   [x] Smoke Test `EP_REC_3` (Error): Intentar mover 100Kg de un lote que solo tiene 50Kg (capturado como rechazo HTTP `422` esperado en PowerShell 5.1).
    *   [x] UI Test Modal de Traslado (validado indirectamente via `npm run build` y flujo PWA con scanner/manual input).
    *   [x] E2E Playwright `@block2` (flujo cuarentena) ejecutado en verde con expectativas alineadas al mensaje de exito post-traslado.
*   **Critico ERPNext:** La cuenta puente contable temporal (Stock Adjustment) asignada al `Material Transfer` no debe generar saldos colgados de valoración. Alinear con el Contador.

## 5. Resultado implementado

- Backend operativo en `gcma_kiosco.api.recepcion` con EP_REC_3 `trasladar_lote_aprobado` y EP_REC_4 `get_lote_para_impresion`.
- PWA ampliada con `/traslado-cuarentena` y `/reimpresion`, accesibles desde `ReceptionMateriaux.vue`.
- Reutilizacion de `useScanner` y del servicio Zebra local para evitar logica duplicada.
- Smoke `scripts/smoke/test-ep-cuarentena.ps1 -PrepareSandbox` ejecutado en verde.
- `TransladoCuarentena.vue` reforzado para evitar falso error inmediatamente despues de un traslado exitoso: la recarga post-transfer conserva el mensaje de exito y suprime el bloqueo rojo en ese contexto.
- Validacion cruzada final 2026-03-13: `scripts/smoke/test-bloque-2.ps1` y `npm run test:e2e:block2` en verde.

## 4. Estructura de commits esperada

*   `feat(api): endpoint trasladar_lote_aprobado ep_rec_3 como stock_entry`
*   `feat(api): endpoint get_lote_para_impresion ep_rec_4`
*   `feat(pwa): pantalla traslado-cuarentena con check EP5`
*   `feat(pwa): vista reimpresion integracion Zebra Poka-yoke`
*   `test(api): validaciones de insuficiencia en traslados de cuarentena`
