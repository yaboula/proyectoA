# Sprint 08 - Sub-bloque 3A: Cobranzas y Toma de Pedidos (PWA Offline)

## Objetivo del Sprint
Finalizar la venta "in-situ": controlar el límite de crédito (Cobranzas) previo a habilitar al comercial la toma de un nuevo pedido, y asegurar la toma del pedido con capacidades *offline-first* para cubrir zonas de Marruecos sin señal 4G limpia.

## Requisitos Técnicos Core
1. **Cobranzas y Riesgo (Frappe):**
   - El endpoint `get_estado_cuenta` debe exponer `deuda_vencida` y `limite_credito`.
   - endpoint `post_cobro` (registro de pago de cheques/efectivo).
2. **Kiosco de Pedidos Móvil (PWA):**
   - Pantalla obligatoria de Estado de Cuenta (Bloqueante si hay mora grave).
   - "Shopping Cart" estilo B2B: Cantidad por SKU, descuentos comerciales.
   - Sincronización en diferido (`IndexedDB` + Background Sync Queue). Si el dispositivo pierde internet al darle "Enviar Pedido", el pedido se encola y el comercial recibe la confirmación visual de "Guardado para enviar".

## Criterios de Aceptación (DoD)
- [ ] Validar Poka-Yoke: Intentar tomar un pedido para una droguería excedida en su límite de crédito lanza un Modal Bloqueante pidiendo "Autorización de Manager".
- [ ] El carrito de compra verifica el "stock_proyectado" desde Frappe para no emitir venta al vacío.
- [ ] Validar offline: Apagar el Wi-fi/4G en DevTools, crear pedido, verificar que se guarda en la IndexedDB "Sync Queue", volver a prender la red y confirmar que el `ServiceWorker` lo descarga a Frappe.
- [ ] Evidencia requerida: Grabación/Capturas del flujo Offline.

---

### Endpoints Clave (Esquema Inicial)
```javascript
// frontend/src/utils/syncQueue.js
export async function enqueueOrder(orderPayload) {
  // 1. Save to local DB
  // 2. Register Sync Event Request with ServiceWorker
}
```
