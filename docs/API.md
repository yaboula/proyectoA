# API Reference — GCMA Kiosco

Base URL: `/api/method/gcma_kiosco.api.kiosco`

Todos los endpoints usan `Content-Type: application/x-www-form-urlencoded`.
La respuesta se envuelve en el sobre estándar Frappe: `{ "message": { ... } }`.

---

## Autenticación

- **EP1** es `allow_guest=True` (público).
- **EP1b** `get_operario_session` es `allow_guest=True` pero devuelve `401` si no existe una sesión válida.
- **EP1c** `logout_operario` cierra la sesión Frappe del navegador actual.
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

## EP1b — Restaurar Sesión de Operario

Permite a la PWA reconstruir el contexto del operario a partir de la cookie `sid` ya presente en el navegador.

| Campo | Valor |
|-------|-------|
| **Ruta** | `GET /api/method/gcma_kiosco.api.kiosco.get_operario_session` |
| **Auth** | Público con validación interna de `sid` |

### Response — Sesión válida (200 OK)

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
  "sid": "abc123..."
}
```

### Errores

| HTTP | `error_code` | `message_fr` | Causa |
|------|-------------|-------------|-------|
| 401 | `NO_ACTIVE_SESSION` | Session expirée... | No hay cookie `sid` válida o el usuario ya no es un operario activo |

### curl

```bash
curl http://localhost:8080/api/method/gcma_kiosco.api.kiosco.get_operario_session \
  -b "sid=<session_id>"
```

---

## EP1c — Logout Operario

Cierra la sesión Frappe del navegador actual y elimina la cookie `sid` del kiosco.

| Campo | Valor |
|-------|-------|
| **Ruta** | `POST /api/method/gcma_kiosco.api.kiosco.logout_operario` |
| **Auth** | Sesión requerida |

### Response (200 OK)

```json
{
  "success": true,
  "message_fr": "Session fermée."
}
```

### curl

```bash
curl -X POST http://localhost:8080/api/method/gcma_kiosco.api.kiosco.logout_operario \
  -b "sid=<session_id>"
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
| `qr_data` | string | Sí | Contenido del QR del material (formato: `ITEM_CODE\|BATCH_NO`). Para items no loteados usar `ITEM_CODE\|SIN-LOTE` |

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

## EP4 — Reportar Consumo

Registra el consumo real de materiales al finalizar la mezcla y cierra el ciclo productivo nativo en ERPNext. El endpoint crea dos `Stock Entry` submitidos ligados a la Work Order:

- `Material Transfer for Manufacture` hacia `Planta Mezclas WIP - <ABBR>`
- `Manufacture` desde WIP hacia `Cuarentena PT - <ABBR>`

Además calcula desviaciones vs BOM teórica, registra un `Comment` de auditoría en la Work Order y, si alguna desviación supera el 10%, activa alerta `WARNING`.

| Campo | Valor |
|-------|-------|
| **Ruta** | `POST /api/method/gcma_kiosco.api.kiosco.reportar_consumo` |
| **Auth** | Sesión requerida (cookie `sid`) |

### Request

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `work_order` | string | Sí | Nombre de la Work Order (ej. `MFG-WO-2026-00001`) |
| `lotes_usados` | string (JSON) | No | Mapa JSON `item_name/item_code -> batch_no`. Obligatorio para materiales loteados. Para materiales no loteados el frontend envía `SIN-LOTE`. |
| `consumos_extra` | string (JSON) | No | Mapa JSON `item_name/item_code -> qty_extra` con ajustes finos sobre la BOM teórica. |
| `extras` | string (JSON) | No | Contrato legacy: array JSON de `{"item_name": str, "qty_extra": float}`. Se mantiene por compatibilidad hacia atrás. |

> **Nota**: el frontend actual envía `lotes_usados` y `consumos_extra` como JSON string porque Axios serializa a `URLSearchParams` (`application/x-www-form-urlencoded`).

### Response — Sin desviaciones (200 OK)

```json
{
  "success": true,
  "work_order": "MFG-WO-2026-00001",
  "stock_entry_transfer": "MAT-STE-2026-00009",
  "stock_entry_manufacture": "MAT-STE-2026-00010",
  "resumen": {
    "qty_producida": 50.0,
    "desviaciones": [],
    "merma_total_pct": 0,
    "estado": "Manufacturé"
  },
  "message_fr": "Consommation enregistrée et lot fabriqué avec succès."
}
```

### Response — Con desviaciones >10% (200 OK, alerta WARNING)

```json
{
  "success": true,
  "work_order": "MFG-WO-2026-00001",
  "stock_entry_transfer": "MAT-STE-2026-00011",
  "stock_entry_manufacture": "MAT-STE-2026-00012",
  "resumen": {
    "qty_producida": 50.0,
    "desviaciones": [
      {
        "item_name": "Dioxyde de Titane R-902",
        "qty_teorica": 400.0,
        "qty_real": 450.0,
        "diferencia_kg": 50.0,
        "diferencia_pct": 12.5
      }
    ],
    "merma_total_pct": 3.4,
    "estado": "Manufacturé"
  },
  "alerta": true,
  "alerta_nivel": "WARNING",
  "message_fr": "Consommation enregistrée et lot fabriqué. ⚠ Écart supérieur à 10% sur Dioxyde de Titane R-902."
}
```

### Errores

| HTTP | `error_code` | `message_fr` | Causa |
|------|-------------|-------------|-------|
| 400 | `MISSING_PARAMS` | Paramètre 'work_order' obligatoire. | Sin `work_order` |
| 400 | `MISSING_BATCH` | Lot manquant pour ... | Falta lote usado para un material con `has_batch_no = 1` |
| 422 | `EXTRA_QTY_ABSURD` | Saisie incohérente... | El extra supera la cantidad teórica del ingrediente; probable error de tipeo |
| 404 | `WO_NOT_FOUND` | Ordre de fabrication introuvable ou non validé. | WO no existe o `docstatus ≠ 1` |
| — | `WO_NOT_IN_PROCESS` | Cet ordre n'est pas en cours... | WO status no es Not Started / In Process |
| 422 | `INVALID_TARGET_WAREHOUSE` | L'entrepôt de produit fini doit être la quarantaine PT. | La WO apunta a un FG warehouse incorrecto |
| 422 | `ERP_VALIDATION_ERROR` | Transaction refusée par ERPNext... | ERPNext rechazó los `Stock Entry` o los bundles nativos |
| 500 | `INTERNAL_ERROR` | Erreur interne... | Excepción no controlada |

### Lógica interna

1. Valida que la WO existe, está submitted y en estado activo
2. Verifica que el `fg_warehouse` de la WO sea `Cuarentena PT - <ABBR>`
3. Construye el plan de consumo a partir de `required_items`, `lotes_usados` y `consumos_extra`
4. Bloquea extras absurdos (`qty_extra > qty_teorica`) con `EXTRA_QTY_ABSURD`
5. Crea y submit el `Stock Entry` `Material Transfer for Manufacture`
6. Crea y submit el `Stock Entry` `Manufacture`
7. Genera los `Serial and Batch Bundle` de salida con la vía nativa de ERPNext para materiales loteados
8. Registra un `Comment` `Info` en la Work Order con trazabilidad de consumos y documentos generados
9. Retorna resumen con desviaciones y nombres de `Stock Entry`

### curl

```bash
# Consumo estándar (sin extras)
curl -X POST http://localhost:8080/api/method/gcma_kiosco.api.kiosco.reportar_consumo \
  -b "sid=<session_id>" \
  -d "work_order=MFG-WO-2026-00001" \
  -d 'lotes_usados={"Résine Alkyde G-70":"LOTE-TEST-RES-001","Dioxyde de Titane R-902":"LOTE-TEST-PIG-001","White Spirit Standard":"LOTE-TEST-SOL-001","Eau Déminéralisée":"LOTE-TEST-H2O-001","Seau Plastique 20L Blanc":"SIN-LOTE","Couvercle Seau 20L":"SIN-LOTE","Étiquette Peinture Blanche Mate 20L":"SIN-LOTE"}' \
  -d "consumos_extra={}"

# Con extras (+50 Kg de Titane)
curl -X POST http://localhost:8080/api/method/gcma_kiosco.api.kiosco.reportar_consumo \
  -b "sid=<session_id>" \
  -d "work_order=MFG-WO-2026-00001" \
  -d 'lotes_usados={"Résine Alkyde G-70":"LOTE-TEST-RES-001","Dioxyde de Titane R-902":"LOTE-TEST-PIG-001","White Spirit Standard":"LOTE-TEST-SOL-001","Eau Déminéralisée":"LOTE-TEST-H2O-001","Seau Plastique 20L Blanc":"SIN-LOTE","Couvercle Seau 20L":"SIN-LOTE","Étiquette Peinture Blanche Mate 20L":"SIN-LOTE"}' \
  -d 'consumos_extra={"Dioxyde de Titane R-902":50}'
```

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

Para materiales sin trazabilidad por lote, el contrato del kiosco usa el marcador:

`ITEM_CODE|SIN-LOTE`

Ejemplos válidos:
- `ENV-BID-20L-BLC|SIN-LOTE`
- `ENV-TAP-BID-20L|SIN-LOTE`
- `ENV-ETQ-PIN-BLC|SIN-LOTE`

Parseado por `qr_utils.parse_qr_material()`.
