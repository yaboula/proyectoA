# API Reference — GCMA Kiosco

Base URL: `/api/method/gcma_kiosco.api.kiosco`

Todos los endpoints usan `Content-Type: application/x-www-form-urlencoded`.
La respuesta se envuelve en el sobre estándar Frappe: `{ "message": { ... } }`.

---

## Autenticación

- **EP1** es `allow_guest=True` (público).
- **EP2–EP5** requieren sesión activa (cookie `sid` obtenida tras EP1).
- CSRF deshabilitado para rutas `gcma_kiosco.*` vía hook `before_request` (la PWA se sirve desde un origen distinto).

---

## EP1 — Login Operario

Autentica al operario escaneando su badge QR personal.

| Campo | Valor |
|-------|-------|
| **Ruta** | `POST /api/method/gcma_kiosco.api.kiosco.login_operario` |
| **Auth** | Público (`allow_guest=True`) |

### Request

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `qr_token` | string | Sí | Token del badge QR (ej. `OP-2026-BADGE-00042`) |

### Response (200 OK)

```json
{
  "success": true,
  "operario": {
    "full_name": "Ahmed Benali",
    "employee_id": "HR-EMP-00001",
    "company": "Peintures du Maroc SARL",
    "company_abbr": "PDM",
    "default_warehouse": "Planta Mezclas WIP - PDM"
  },
  "sid": "abc123...",
  "message_fr": "Bienvenue, Ahmed Benali."
}
```

### Errores

| HTTP | `error_code` | `message_fr` | Causa |
|------|-------------|-------------|-------|
| 400 | `MISSING_TOKEN` | Code QR manquant... | Sin `qr_token` |
| 401 | `INVALID_BADGE` | Badge non reconnu... | Token no existe en BD |
| 403 | `EMPLOYEE_INACTIVE` | Compte désactivé... | Employee status ≠ Active |
| 403 | `NO_USER_LINKED` | Aucun compte utilisateur... | Employee sin `user_id` |
| 401 | `AUTH_FAILED` | Erreur d'authentification... | Frappe login_as falló |
| 500 | `INTERNAL_ERROR` | Erreur interne... | Excepción no controlada |

### curl

```bash
curl -X POST http://localhost:8080/api/method/gcma_kiosco.api.kiosco.login_operario \
  -d "qr_token=OP-2026-BADGE-00042"
```

---

## EP2 — Obtener Tareas

Lista las Work Orders pendientes (Not Started / In Process) con materiales y stock.

| Campo | Valor |
|-------|-------|
| **Ruta** | `GET /api/method/gcma_kiosco.api.kiosco.get_tareas` |
| **Auth** | Sesión requerida (cookie `sid`) |

### Request

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `company` | string | Sí | Nombre de la empresa (ej. `Peintures du Maroc SARL`) |
| `warehouse` | string | No | Filtrar por WIP warehouse |

### Response (200 OK)

```json
{
  "tareas": [
    {
      "work_order": "MFG-WO-2026-00001",
      "producto": "Peinture Glycérophtalique Blanche 20L",
      "cantidad": 50.0,
      "cantidad_pendiente": 50.0,
      "uom": "Unit",
      "bom": "BOM-GLY-20L-001",
      "estado": "In Process",
      "fecha_inicio_plan": "2026-01-20",
      "materiales": [
        {
          "item_name": "Résine Alkyde Longue G70",
          "qty_requerida": 400.0,
          "uom": "Kg",
          "qty_disponible": 2000.0,
          "suficiente": true
        }
      ]
    }
  ],
  "total": 1
}
```

### Errores

| HTTP | `error_code` | `message_fr` |
|------|-------------|-------------|
| 400 | `MISSING_COMPANY` | Paramètre 'company' obligatoire. |
| 500 | `INTERNAL_ERROR` | Erreur interne... |

### curl

```bash
curl -s "http://localhost:8080/api/method/gcma_kiosco.api.kiosco.get_tareas?\
company=Peintures+du+Maroc+SARL&warehouse=Planta+Mezclas+WIP+-+PDM" \
  -b "sid=<session_id>"
```

---

## EP3 — Validar Material (Poka-Yoke)

Valida que el material escaneado es correcto, el lote no está caducado y hay stock.

| Campo | Valor |
|-------|-------|
| **Ruta** | `POST /api/method/gcma_kiosco.api.kiosco.validar_material` |
| **Auth** | Sesión requerida (cookie `sid`) |

### Request

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `work_order` | string | Sí | Nombre de la Work Order |
| `qr_data` | string | Sí | Contenido del QR del bidón (formato: `ITEM_CODE\|BATCH_NO`) |

### Response — Válido (200 OK)

```json
{
  "valido": true,
  "item_name": "Résine Alkyde Longue G70",
  "batch_no": "LOTE-TEST-RES-001",
  "fecha_caducidad": "2027-12-31",
  "dias_restantes": 700,
  "qty_disponible": 2000.0,
  "qty_requerida_bom": 400.0,
  "uom": "Kg",
  "message_fr": "✓ Matériau vérifié. Vous pouvez verser."
}
```

### Response — Inválido (200 OK con `valido: false`)

```json
{
  "valido": false,
  "error_code": "WRONG_MATERIAL",
  "item_escaneado": "Pigment Dioxyde de Titane TiO2",
  "items_esperados": ["Résine Alkyde Longue G70", "White Spirit D40"],
  "message_fr": "✗ STOP — Ce matériau ne correspond pas à la recette.",
  "alerta_nivel": "CRITICO"
}
```

### Errores

| HTTP | `error_code` | Causa |
|------|-------------|-------|
| 400 | `MISSING_PARAMS` | Faltan `work_order` o `qr_data` |
| 400 | `INVALID_QR` | QR no tiene formato `ITEM\|BATCH` |
| 404 | `WO_NOT_FOUND` | Work Order no existe o no está submitted |
| — | `WO_NOT_IN_PROCESS` | WO no está en estado activo |
| — | `WRONG_MATERIAL` | Material no pertenece a la BOM (Poka-Yoke STOP) |
| — | `BATCH_NOT_FOUND` | Lote no existe en Frappe |
| — | `BATCH_ITEM_MISMATCH` | Lote no corresponde al item escaneado |
| — | `BATCH_EXPIRED` | Lote caducado |
| — | `NO_STOCK` | Sin stock disponible en MP Aprobada |
| 500 | `INTERNAL_ERROR` | Excepción no controlada |

### curl

```bash
curl -X POST http://localhost:8080/api/method/gcma_kiosco.api.kiosco.validar_material \
  -b "sid=<session_id>" \
  -d "work_order=MFG-WO-2026-00001" \
  -d "qr_data=MP-RES-ALK-G70|LOTE-TEST-RES-001"
```

---

## EP4 — Reportar Consumo (TODO)

Registrará el consumo real de materiales post-mezcla vía Stock Entry tipo Manufacture.

**Estado:** Pendiente de implementación.

---

## EP5 — Info Lote (TODO)

Consulta informativa de un lote: item, caducidad, stock actual.

**Estado:** Pendiente de implementación.

---

## Formato QR de Materiales

Separador: `|` (pipe). Contrato con etiquetas Zebra.

```
ITEM_CODE|BATCH_NO
```

Ejemplo: `MP-RES-ALK-G70|LOTE-TEST-RES-001`

Parseado por `qr_utils.parse_qr_material()`.
