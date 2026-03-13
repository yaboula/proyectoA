# Sprint 10 - Sub-bloque 3B: Albaranes (BL) y Proof of Delivery (POD)

## Objetivo del Sprint
Automatizar la burocracia final: Emisión del "Bon de Livraison" (BL / Albarán) al finalizar el Picking, y digitalizar el comprobante de que el cliente (droguería) recibió la mercadería, liquidando así la entrega en sistema y gatillando la cuenta por cobrar.

## Requisitos Técnicos Core
1. **Generación de Documentos (Frappe):**
   - Transacción (Submit) de DocType *Delivery Note* basada en el escaneo real proveniente del Sprint 09.
   - Endpoint para emitir PDF Dinámico (jinja format) del Albarán en tamaño A4 y/o Papel Continuo de matriz de puntos (muy usado en fábricas marroquíes).
2. **App Chofer POD (PWA):**
   - Vista de "Camión Cargado" / "Mis entregas del turno".
   - Botón de Entregar -> Firma Digital (Canvas in Vue) + Captura de Cámara PWA para foto fachada/sello húmedo del cliente.
   - Guardado y cambio de estado a "Entregado" y habilitación de facturación.

## Criterios de Aceptación (DoD)
- [ ] La firma capturada en HTML5 Canvas se codifica en Base64, se envía al Backend, y se graba como archivo adjunto (*File*) referenciado al DocType del Albarán.
- [ ] La foto de captura usa `<input type="file" accept="image/*" capture="environment">` nativo para obligar a usar la cámara trasera y evitar que el chofer suba una foto vieja.
- [ ] El cambio a estado "Entregado" se verifica consultando Frappe.
- [ ] Evidencia requerida: Script de QA End-to-End o Grabación enviando la firma y la foto y verificando que impacta la base de datos de escritorio de Frappe sin recargar pantallas.

---

### Endpoints Clave (Esquema Inicial)
```python
# frappe-bench/apps/logistics/api/delivery.py

@frappe.whitelist()
def registrar_pod(delivery_note_id, b64_signature, b64_photo):
    # Regla: Adjuntar firma y foto al doc, actualizar estado a "Completed".
    # Frappe automágicamente genera el asiento contable (GL Entry) de salida del almacén a Costo de Ventas si está bien confgiguardo.
```
