# Sprint 09 - Sub-bloque 3B: Kiosco de Picking Dirigido (FEFO)

## Objetivo del Sprint
Aislar el error humano durante la preparación de la carga en almacén. El operario escanea el Pedido y el PWA le exige, ítem por ítem, escanear el lote físico. El sistema **debe bloquear la preparación si no se respeta el FEFO** o si se arma de más.

## Requisitos Técnicos Core
1. **Reglas de Negocio en Frappe (Stock & Picking):**
   - API `get_pick_list`: Dado un ID Pedido, devuelve los lotes teóricos requeridos ordenados por fecha de expiración (FEFO Mínimo).
   - API `validate_picking_scan`: Hook que recibe el lote escaneado y determina si es "Legal" (¿Pertenece al SKU? ¿Es el lote más antiguo en almacén sin reservar?). 
2. **Kiosco de Expedición PWA (Tablet):**
   - Lector QR / Input Manual para Batch.
   - Sonidos de feedback (Success Beep / Error Buzz) como Poka-Yoke sensorial.
   - Modal de "Override de Lote" (Si el lote FEFO requerido no existe físicamente porque hubo merma no documentada, el Encargado debe meter su PIN para autorizar a sacar un lote más nuevo).

## Criterios de Aceptación (DoD)
- [ ] Validar FEFO: Hay en stock el Lote-AA (Vence este mes) y Lote-BB (Vence en 6 meses). Si la pistola lee Lote-BB, debe saltar pantalla roja bloqueante: "Existe lote anterior (Lote-AA). Extraiga ese primero".
- [ ] Validar Cantidades: Escanear 21 bidones de Pintura de un pedido de 20 lanza error: "Cantidad excedida". Escanear 19 y dar a finalizar pide confirmación de "Cierre Parcial".
- [ ] Las validaciones son server-side (Frappe) para inyectabilidad y fraude zero; el PWA solo renderiza mensajes.
- [ ] Evidencia requerida: Reporte de Playwright ejecutando el Error Poka-Yoke FEFO.

---

### Endpoints Clave (Esquema Inicial)
```python
# frappe-bench/apps/logistics/api/picking.py

@frappe.whitelist()
def validate_picking_fefo(item_code, batch_scanned):
    # Regla: Si hay lotes más antiguos que batch_scanned con stock real > 0 en el warehouse de despachos -> Lanza frappe.ValidationError("Poka-Yoke FEFO violado")
```
