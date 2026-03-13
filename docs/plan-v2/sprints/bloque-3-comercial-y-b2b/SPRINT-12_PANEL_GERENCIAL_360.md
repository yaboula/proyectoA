# Sprint 12 - Sub-bloque 3A.2: Panel Gerencial Comercial (Dashboard 360)

## Objetivo del Sprint
Dotar al Director/Gerente de un "Centro de Mando" analítico sobre la fuerza de ventas y el estado real de la calle, usando datos procesados de los Sprints 07 y 08 para auditar el desempeño de los comerciales en terreno.

## Requisitos Técnicos Core
1. **Workspace Frappe Directivo (Dashboard):**
   - **Scorecard de Droguerías:** Tabla que cruza Facturación YTD vs Saldo Vencido vs Frecuencia de Compra.
   - **Mapa GPS de Rutas (Frappe Map UI / Leaflet):** Pintar en el mapa de Marruecos dónde hizo Check-in cada comercial hoy, y si hubo desviación contra la ruta teórica asignada (> 500 metros alertados en rojo).
   - **Hit-Rate Visual:** Gráfico Circular/Barras de "Visitas con Pedido" vs "Visitas sin Pedido (Solo Saludo)".
2. **Alertas Automáticas (Churn y Pricing):**
   - Un Scheduler diario (Cron Job en Frappe) que busque qué clientes del Top 20% no han comprado en >40 días, y envíe un email/WhatsApp (Integration) al Gerente ("Alerta de Abandono").
   - Un reporte simple listando las fotos de "Precios de la Competencia" subidas por los comerciales en calle.

## Criterios de Aceptación (DoD)
- [ ] La vista principal carga el cruce de facturación vs deuda en menos de 2 segundos (Data caching o Reportes optimizados).
- [ ] El mapa logra pintar coordenadas válidas extrayendo la latitud y longitud guardadas por la PWA en el Sprint 07.
- [ ] El Scheduler de "Alerta de Abandono" está parametrizado (Configurable: días de corte por tipo de cliente).
- [ ] Evidencia requerida: Screenshots del Dashboard con datos Mock creados y el Log de envío exitoso del Job de Alerta.

---

### Endpoints Clave (Esquema Inicial)
```python
# frappe-bench/apps/sales/analytics/dashboard.py

@frappe.whitelist()
def get_cobertura_mapa(fecha):
    # Retorna [{comercial, lat, lng, time, estado_visita}]
    # Filtra fraudes (donde lat/lng de la app difiere del cliente)
```
