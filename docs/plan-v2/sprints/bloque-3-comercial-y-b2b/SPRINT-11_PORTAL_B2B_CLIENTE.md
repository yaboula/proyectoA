# Sprint 11 - Sub-bloque 3C: Portal B2B para Droguerías (Self-Service)

## Objetivo del Sprint
Empoderar al cliente final (dueño de droguería o distribuidor) con una plataforma 24/7 donde pueda autogestionar sus compras, revisar su cuenta corriente y acceder de inmediato a promociones estratégicas de fábrica.

## Requisitos Técnicos Core
1. **Portal Web App (Frontend B2B):**
   - Autenticación especial de "Cliente" (Customer Portal User en Frappe). Solo ve su propia información.
   - **Catálogo Inteligente:** Motor de sugerencias ("Quienes compraron A, también llevaron B").
   - **Módulo de Estado de Cuenta:** Visor histórico de Facturas, Pagos realizados y Saldo Vencido en tiempo real.
2. **Sistema de Fidelización y Soporte (Frappe):**
   - DocType `Loyalty Program` nativo de ERPNext adaptado: Regla de acumulación de puntos por familia de productos (Priorizando Mermas/FEFOs).
   - Botón SOS (Ticket de Soporte): Creación de un `Issue` en Frappe en un clic (Ej: "Problema con Resina Lote X"), adjuntando fotos desde el móvil del cliente.

## Criterios de Aceptación (DoD)
- [ ] Seguridad: El cliente autenticado intentando forzar un pedido a nombre de otro ID de cliente por API recibe error HTTP 403 (Forbidden).
- [ ] Una droguería con deuda superior a 30 días no puede generar nuevos pedidos en el Portal B2B, sino que ve una pantalla instando al pago o a contactar a cartera.
- [ ] La creación de un Ticket SOS gatilla una alerta inmediata (Notificación in-app y/o email) al equipo de Calidad en fábrica.
- [ ] Evidencia requerida: Flujo automatizado Playwright de login de cliente, intento de fraude y petición exitosa de soporte.

---

### Endpoints Clave (Esquema Inicial)
```javascript
// frontend/src/api/customerPortal.js
export async function createSupportTicket(description, b64Photo, affectedBatch) {
  // Llama al Frappe para crear un Issue vinculado al Customer y al Lote
}
```
