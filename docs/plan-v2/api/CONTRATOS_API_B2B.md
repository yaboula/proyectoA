# Contratos de Integración API (Bloque 3 - B2B y Comercial)

*Documento Arquitectónico para Desarrolladores Frontend y Backend (AI Agents).*
*Regla de Oro: El Mobile PWA "habla" exactamente este idioma, ni un key más ni un key menos.*

---

## 1. Sub-bloque 3A: Fuerza de Ventas Mobile

### 1.1 `GET /api/method/maroc_b2b.api.comercial.get_ruta_dia`
Obtiene los clientes a visitar hoy para el comercial logueado.
* **Request:** `Bearer <token>` / Cookie de Sesión Frappe.
* **Response (200 OK):**
```json
{
  "message": {
    "id_ruta": "RUTA-2026-0012",
    "estado": "En Curso",
    "clientes": [
      {
        "id_cliente": "DROG-001",
        "nombre": "Drogueria Casablanca Centro",
        "gps_lat": 33.5731,
        "gps_lng": -7.5898,
        "visitado": false
      }
    ]
  }
}
```

### 1.2 `POST /api/method/maroc_b2b.api.comercial.post_checkin`
Auditoría in-situ del comercial.
* **Request Payload:**
```json
{
  "id_cliente": "DROG-001",
  "gps_lat_capturada": 33.5732,
  "gps_lng_capturada": -7.5890,
  "timestamp": "2026-03-13T10:00:00Z"
}
```
* **Response (200 OK):** `{"message": {"status": "success", "es_fraude": false, "distancia_metros": 85}}`

### 1.3 `GET /api/method/maroc_b2b.api.comercial.get_estado_cuenta`
Bloqueo por morosidad (Consulta Obligatoria pre-pedido en el PWA).
* **Parámetro GET:** `?id_cliente=DROG-001`
* **Response (200 OK):**
```json
{
  "message": {
    "limite_credito": 50000.0,
    "deuda_total": 45000.0,
    "deuda_vencida": 12000.0,
    "dias_peor_mora": 45,
    "bloqueado_para_venta": true,
    "mensaje_bloqueo": "Excede días de mora permitidos (>30 días)."
  }
}
```

### 1.4 `POST /api/method/maroc_b2b.api.comercial.sync_pedidos_offline`
Suma de pedidos generados sin internet en la calle (Subida Bulk).
* **Request Payload:**
```json
{
  "pedidos": [
    {
       "id_local_indexeddb": "local_1740003000",
       "id_cliente": "DROG-001",
       "items": [
          {"item_code": "PINT-EPOXI-01", "qty": 10},
          {"item_code": "SOLV-ACET-05", "qty": 2}
       ]
    }
  ]
}
```
* **Response (200 OK):** `{"message": {"synced": 1, "failed": 0, "ids_creados": ["SO-00998"]}}`

---

## 2. Sub-bloque 3B: Kiosco Logístico FEFO

### 2.1 `POST /api/method/maroc_b2b.api.logistica.validar_scan_fefo`
Poka-Yoke de almacén por cada "Bip" de la pistola láser del Operario.
* **Request Payload:**
```json
{
  "sales_order": "SO-00998",
  "item_code": "PINT-EPOXI-01",
  "batch_scanned": "LOTE-2025-08"
}
```
* **Response (400 Bad Request) - FEFO VIOLATION:**
```json
{
  "exc_type": "ValidationError",
  "message": "Violación FEFO: Existe el LOTE-2024-11 con stock 50. Extraiga ese primero."
}
```
* **Response (200 OK) - Exitoso:** `{"message": {"status": "ok", "qty_restante_pedido": 9}}`
