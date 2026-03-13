# Sprint 04 - Operación de Inventario de Planta (Recepción)

Bloque: 2 - Operación de Inventario de Planta
Duración sugerida: 2 semanas
Objetivo del sprint: Digitalizar el andén de recepción de materias primas y embalaje. El objetivo es registrar la llegada de la mercancía, generar e imprimir códigos de barras (Zebra), y dar ingreso al almacén "Cuarentena MP" en ERPNext.

Estado: Terminado (Done)

Avance implementado (2026-03-11):

1. EP_REC_1 `get_compras_pendientes` implementado en `gcma_kiosco/api/recepcion.py`.
2. EP_REC_2 `registrar_recepcion` implementado con `Purchase Receipt` nativo, `Quality Inspection` de entrada auto-generada y warehouse `Cuarentena MP - PDM`.
3. Nueva vista PWA `/recepcion` con modal de captura fat-finger y alerta de impresion local.
4. Servicio `src/utils/printer.js` añadido para ZPL local en `http://localhost:9000/print`.
5. Smoke `scripts/smoke/test-ep-recepcion.ps1` creado y ejecutado en verde contra sandbox.

---

## 1. Alcance (Scope)

### In Scope
1. **[Backend]** Implementación de endpoint `get_compras_pendientes` (EP_REC_1) para listar Órdenes de Compra abiertas.
2. **[Backend]** Implementación de endpoint `registrar_recepcion` (EP_REC_2) para crear el `Purchase Receipt` en ERPNext y generar lotes.
3. **[Frontend]** Nueva vista en la PWA "Réception Matériaux" adaptada a tablet/movil (color azul índigo).
4. **[Integración]** Llamada HTTP al servicio local ZPL para impresión de etiquetas (Zebra).
5. **[QA]** Smoke tests automatizados en PowerShell para validar la creación de recibos.

### Out of Scope
1. Sistema de impresión en la nube (la impresora local Zebra es requisito).
2. Procesamiento de compras de ítems no inventariables (ej. Servicios).
3. Devoluciones de recepción parcial (solo ingreso feliz).

---

## 2. Historias Técnicas y Especificaciones (Para Developers)

### HT1 - Endpoint de Órdenes Pendientes (EP_REC_1)
**Como** developer backend, **quiero** exponer `get_compras_pendientes` **para** que la UI liste las facturas por recibir.

*   **Archivo:** `gcma_kiosco/api/recepcion.py` (Nuevo archivo, requerirá registrar en `hooks.py` si es necesario, o import en un `__init__`).
*   **Contrato:**
    *   **Input:** `company` (str), `warehouse` (str, opcional).
    *   **Lógica Frappe:**
        1. Query a `Purchase Order`. 
        2. Condiciones: `docstatus == 1` (Submitted), `status != "Closed"`, `per_received < 100`.
        3. Hacer pre-fetch de los `Purchase Order Item` para devolver lista de ítems pendientes.
        4. Excluir items donde `qty == received_qty`.
    *   **Output JSON:**
        ```json
        {
          "success": true,
          "ordenes": [
            {
              "po_name": "PUR-ORD-2026-0001",
              "supplier_name": "Dow Chemicals",
              "items": [
                { "item_code": "...", "item_name": "...", "qty_pending": 1500.0, "uom": "Kg", "has_batch_no": 1 }
              ]
            }
          ]
        }
        ```

### HT2 - Endpoint de Registro de Recepción (EP_REC_2)
**Como** developer backend, **quiero** exponer `registrar_recepcion` **para** impactar el stock en ERPNext creando un `Purchase Receipt`.

*   **Archivo:** `gcma_kiosco/api/recepcion.py`
*   **Contrato:**
    *   **Input (POST):** `po_name` (str), `items_recibidos` (JSON String o dict). Array de `{item_code, qty, supplier_batch, expiry_date}`.
    *   **Lógica Frappe (Crítica):**
        1. Usar la API nativa de Frappe para mapear: `frappe.model.mapper.get_mapped_doc("Purchase Order", po_name, {"Purchase Order": {"doctype": "Purchase Receipt"}})`
        2. Limpiar las líneas generadas para dejar *sólo* los ítems que vienen en `items_recibidos` con la cantidad especificada.
        3. Forzar `set_warehouse` a `"Cuarentena MP - PDM"` (o el que se le pase de config de la app).
        4. Inyectar `supplier_batch` (lote prov) y `expiry_date` si aplica.
        5. Llamar a `pr.insert()` y `pr.submit()`. En ERPNext v16, esto generará el registro en `Serial and Batch Entry`.
        6. Recolectar de las líneas del PR final los `batch_no` que autogeneró ERPNext.
    *   **Output JSON:** `{ "success": true, "purchase_receipt": "MAT-PRE...", "lotes_generados": [{"item_code": "...", "batch_no": "LOTE-2601"}] }`

### HT3 - UI "Réception Matériaux" (Frontend PWA)
**Como** developer frontend, **quiero** una pantalla para seleccionar la PO, el ítem y digitar la cantidad **para** que el operario de andén documente la entrada.

*   **Ruta Vue:** `/recepcion`
*   **Componentes:**
    *   Reutilizar `KioskLayout.vue`.
    *   Header: Título "Réception", color theme índigo (clases de Tailwind específicas vs ámbar de producción).
    *   `KioskAccordion` o listado de cards para las `Purchase Orders`.
    *   Al tocar un ítem pendiente -> Abre Modal (basarse en `ManualInputModal.vue` modificado) con `input type="number"` grande para `qty`, `input type="text"` para `supplier_batch` y `input type="date"` para vencimiento.
*   **Contrato de Acción:** Al confirmar, llama a API `kiosco.js` -> `EP_REC_2`. Al éxito, dispara el print local (HT4).

### HT4 - Impresión Poka-Yoke (Frontend a Local)
**Como** operator de andén, **quiero** que al finalizar el recibo salgan las etiquetas Zebra **para** pegarlas en los tambores antes de moverlos a cuarentena.

*   **Lógica Frontend (`src/utils/printer.js` o en el store):**
    *   Endpoint local: `http://localhost:9000/print` (Manejar error elegantemente si no está el puente encendido).
    *   **Plantilla ZPL de Referencia:**
        ```zpl
        ^XA
        ^FO50,50^A0N,50,50^FD{item_name}^FS
        ^FO50,120^A0N,30,30^FDLot Interne: {batch_no}^FS
        ^FO50,160^A0N,30,30^FDExp: {expiry_date}^FS
        ^FO50,220^BQN,2,6^FDQA,{item_code}|{batch_no}^FS
        ^XZ
        ```
    *   Diseño debe ser un servicio en JS asíncrono que retorne alerta amarilla en la UI "Recepción registrada en ERP, pero falla en impresora local" si el HTTP call falla.

---

## 3. Matriz de Riesgo y Testeo (Definition of Done)

*   **Testing Requerido:**
  *   [x] Script `test-ep-recepcion.ps1` que valide contra datos de prueba (sandbox).
    *   [ ] Smoke Test Frontend: Completar flujo con puente POST de Zebra mockeado.
*   **Critico ERPNext:** Validar la regla contable (`Stock in Transit`) y de valoración (ERPNext exige un Default Valuation Rate en ítems estándar al hacer el Receipt, asegurarse que pase).
*   **UX:** Todo input numérico en el kiosco debe tener botones grandes `[+1] [+10] [MAX]` para manipulación gorda (fat-finger).

## 4. Estructura de commits esperada

*   `feat(api): endpoint get_compras_pendientes ep_rec_1`
*   `feat(api): endpoint registrar_recepcion ep_rec_2 con creacion PR`
*   `feat(pwa): pantallas y flujos de recepcion y modal de captura`
*   `feat(pwa): servicio de impresion ZPL local host`
*   `test(e2e): smoke tests powershell recepcion`
