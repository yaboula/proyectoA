# Sprint 07 - Sub-bloque 3A: Fuerza de Ventas (Rutas y Visitas)

## Objetivo del Sprint
Proveer al Comercial B2B (Marruecos) de una app móvil para ver su hoja de ruta diaria, localizar droguerías/clientes, registrar "Check-In" auditado por GPS y visualizar el catálogo.

## Requisitos Técnicos Core
1. **PWA (Frontend):** 
   - Vista "Hoja del Día" (Routing).
   - Componente de Geolocalización (`navigator.geolocation`) para registrar longitud/latitud en Check-In de visita.
   - Vista de "Catálogo y Stock Proyectado" optimizada para móviles "fat-finger".
2. **Frappe (Backend):**
   - DocType / Endpoint para `Ruta_Comercial` y `Visita_Cliente`.
   - Endpoint `get_rutas_dia` y `registrar_visita`.

## Criterios de Aceptación (DoD)
- [ ] La app PWA pregunta por permisos de GPS. Si se niegan, no permite hacer "Check-In" de ruta.
- [ ] Al hacer "Check-In", el servidor Frappe guarda la latitud/longitud real vs la latitud/longitud teórica del cliente almacenada en DB.
- [ ] API REST responde en < 500ms al listar rutas para el comercial logueado.
- [ ] Evidencia requerida: Playwright Test de simulación de ruta completada + Capturas de PWA móvil.

---

### Endpoints Clave (Esquema Inicial)
```python
# frappe-bench/apps/sales/api/routing.py

@frappe.whitelist()
def registrar_checkin(cliente_id, gps_lat, gps_lng):
    # Regla: Calcular distancia euclidiana vs DB. 
    # Si > 500m, marcar visita como "Observada" por fraude de ubicación.
```
