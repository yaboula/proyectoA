# API Reference — GCMA Kiosco

Base URL principal: `/api/method/gcma_kiosco.api.kiosco`

Base URL calidad: `/api/method/gcma_kiosco.api.calidad`

Base URL recepcion: `/api/method/gcma_kiosco.api.recepcion`

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
    "default_warehouse": "Planta Mezclas WIP - PDM",
    "profile_code": "production",
    "profile_label": "Production",
    "allowed_modules": ["production", "reception"],
    "default_route": "/tareas"
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
    "default_warehouse": "Planta Mezclas WIP - PDM",
    "profile_code": "production",
    "profile_label": "Production",
    "allowed_modules": ["production", "reception"],
    "default_route": "/tareas"
  },
  "sid": "abc123..."
}
```

### Notas de perfil

- El `Employee` ahora define `custom_kiosk_profile` con valores `production` o `quality`.
- EP1 y EP1b devuelven el perfil efectivo del badge y la lista de módulos permitidos.
- Los endpoints de producción (`get_tareas`, `validar_material`, `reportar_consumo`) rechazan badges de laboratorio con `403 PROFILE_NOT_ALLOWED`.
- Los endpoints de calidad (`get_lotes_cuarentena`, `aprobar_calidad`) rechazan badges de producción con `403 PROFILE_NOT_ALLOWED`.

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

## EP5 — Info Lote

Consulta informativa de un lote para uso rapido en planta/laboratorio.

| Campo | Valor |
|-------|-------|
| **Ruta** | `GET /api/method/gcma_kiosco.api.kiosco.info_lote` |
| **Auth** | Sesión requerida (cookie `sid`) |

### Request

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `batch_no` | string | Sí | Lote a consultar |
| `item_code` | string | No | Validación cruzada opcional del item del lote |

### Response (200 OK)

```json
{
  "success": true,
  "lote": {
    "batch_no": "LOTE-CHAOS-PT-001",
    "item_code": "PT-PIN-BLC-MAT-20L",
    "item_name": "Peinture Blanche Mate 20L",
    "expiry_date": "2027-03-10",
    "dias_restantes": 364
  },
  "stock_por_almacen": [
    {
      "warehouse": "Cuarentena PT - PDM",
      "qty": 5.0
    }
  ],
  "total_qty": 5.0,
  "message_fr": "Informations du lot chargees."
}
```

### Errores

| HTTP | `error_code` | `message_fr` | Causa |
|------|-------------|-------------|-------|
| 400 | `MISSING_PARAMS` | Paramètre 'batch_no' obligatoire. | Falta `batch_no` |
| 404 | `BATCH_NOT_FOUND` | Lot '...' introuvable. | Lote inexistente |
| 422 | `BATCH_ITEM_MISMATCH` | Le lot indique ne correspond pas... | `item_code` no coincide con el lote |
| 500 | `INTERNAL_ERROR` | Erreur interne lors de la consultation du lot. | Excepción no controlada |

### curl

```bash
curl "http://localhost:8080/api/method/gcma_kiosco.api.kiosco.info_lote?batch_no=LOTE-CHAOS-PT-001&item_code=PT-PIN-BLC-MAT-20L" \
  -b "sid=<session_id>"
```

---

## Bloque 2 — Recepcion de Materias Primas

Los endpoints de recepcion viven en `gcma_kiosco.api.recepcion` y trabajan sobre `Purchase Order`, `Purchase Receipt`, `Purchase Receipt Item`, `Quality Inspection` y `Batch`.

### EP_REC_1 — Compras Pendientes de Recepcion

Lista Purchase Orders abiertas con lineas stock pendientes para el modulo de quai.

| Campo | Valor |
|-------|-------|
| **Ruta** | `GET /api/method/gcma_kiosco.api.recepcion.get_compras_pendientes` |
| **Auth** | Sesión requerida (cookie `sid`) |

### Request

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `company` | string | Sí | Empresa operativa (`Peintures du Maroc SARL`) |
| `warehouse` | string | No | Filtro opcional por almacén de línea |

### Response (200 OK)

```json
{
  "success": true,
  "company": "Peintures du Maroc SARL",
  "warehouse": null,
  "total": 1,
  "ordenes": [
    {
      "po_name": "PUR-ORD-2026-00001",
      "supplier": "ChimEurope SARL",
      "supplier_name": "ChimEurope SARL",
      "transaction_date": "2026-03-11",
      "items": [
        {
          "po_item_name": "abc123",
          "item_code": "MP-RES-ALK-G70",
          "item_name": "Résine Alkyde G-70",
          "qty_pending": 250.0,
          "uom": "Kg",
          "has_batch_no": 1,
          "has_expiry_date": 1
        }
      ]
    }
  ]
}
```

### Errores

| HTTP | `error_code` | `message_fr` |
|------|-------------|-------------|
| 400 | `MISSING_COMPANY` | Parametre 'company' obligatoire. |
| 500 | `INTERNAL_ERROR` | Erreur interne lors du chargement des commandes en attente. |

### EP_REC_2 — Registrar Recepcion

Crea un `Purchase Receipt` nativo en `Cuarentena MP - <ABBR>`, auto-genera `Quality Inspection` de entrada si el item la exige y devuelve los lotes resultantes para etiquetado Zebra.

| Campo | Valor |
|-------|-------|
| **Ruta** | `POST /api/method/gcma_kiosco.api.recepcion.registrar_recepcion` |
| **Auth** | Sesión requerida (cookie `sid`) |

### Request

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `po_name` | string | Sí | Purchase Order origen |
| `items_recibidos` | string (JSON) | Sí | Array JSON de `{item_code, qty, supplier_batch, expiry_date}` |
| `warehouse` | string | No | Override del warehouse destino |

### Response (200 OK)

```json
{
  "success": true,
  "purchase_receipt": "MAT-PRE-2026-00002",
  "warehouse": "Cuarentena MP - PDM",
  "posting_date": "2026-03-11",
  "lotes_generados": [
    {
      "item_code": "MP-RES-ALK-G70",
      "item_name": "Résine Alkyde G-70",
      "batch_no": null,
      "qty": 1.0,
      "uom": "Kg",
      "expiry_date": "2027-03-11",
      "supplier_batch": "FOURN-20260311220000"
    }
  ],
  "message_fr": "Reception enregistree avec succes."
}
```

### Errores

| HTTP | `error_code` | `message_fr` |
|------|-------------|-------------|
| 400 | `MISSING_PARAMS` | Parametres obligatoires: po_name et items_recibidos. |
| 400 | `INVALID_ITEMS_JSON` | Format JSON invalide pour items_recibidos. |
| 400 | `INVALID_ITEMS_TYPE` | items_recibidos doit etre une liste. |
| 404 | `PO_NOT_FOUND` | Commande d'achat introuvable. |
| 409 | `PO_NOT_RECEIVABLE` | Cette commande n'est pas ouverte a la reception. |
| 422 | `ITEM_NOT_PENDING` | L'article n'est pas en attente sur cette commande. |
| 422 | `QTY_EXCEEDS_PENDING` | Quantite recue superieure au reliquat. |
| 500 | `INTERNAL_ERROR` | Erreur interne pendant l'enregistrement de la reception. |

### Notas de implementación

- La transacción se ejecuta como usuario sistema durante `insert/save/submit` para permitir la creación nativa de lotes y stock ledger.
- Si el item tiene `inspection_required_before_purchase = 1`, el endpoint crea una `Quality Inspection` de entrada auto-generada y la enlaza al `Purchase Receipt Item` antes del submit.
- El parser de `items_recibidos` tolera payload JSON anidado, dict único o lista.

### curl

```bash
curl -X POST http://localhost:8080/api/method/gcma_kiosco.api.recepcion.registrar_recepcion \
  -b "sid=<session_id>" \
  -d "po_name=PUR-ORD-2026-00001" \
  --data-urlencode 'items_recibidos=[{"item_code":"MP-RES-ALK-G70","qty":1,"supplier_batch":"FOURN-001","expiry_date":"2027-03-11"}]'
```

### EP_REC_3 — Trasladar Lote Aprobado

Genera un `Stock Entry` nativo `Material Transfer` desde `Cuarentena MP - <ABBR>` hacia `Materia Prima Aprobada - <ABBR>` para un lote ya validado.

| Campo | Valor |
|-------|-------|
| **Ruta** | `POST /api/method/gcma_kiosco.api.recepcion.trasladar_lote_aprobado` |
| **Auth** | Sesión requerida (cookie `sid`) |

### Request

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `item_code` | string | Sí | Código del item loteado |
| `batch_no` | string | Sí | Lote interno a mover |
| `qty_to_move` | float | Sí | Cantidad a trasladar |
| `source_warehouse` | string | No | Origen. Por defecto `Cuarentena MP - <ABBR>` |
| `target_warehouse` | string | No | Destino. Por defecto `Materia Prima Aprobada - <ABBR>` |

### Response (200 OK)

```json
{
  "success": true,
  "stock_entry": "MAT-STE-2026-00015",
  "item_code": "MP-RES-ALK-G70",
  "batch_no": "LOTE-QA-RECEP-0001",
  "qty_moved": 5.0,
  "source_warehouse": "Cuarentena MP - PDM",
  "target_warehouse": "Materia Prima Aprobada - PDM",
  "message_fr": "Lot transfere vers le stock approuve."
}
```

### Errores

| HTTP | `error_code` | `message_fr` |
|------|-------------|-------------|
| 400 | `MISSING_PARAMS` | Parametres obligatoires: item_code, batch_no et qty_to_move. |
| 400 | `INVALID_QTY` | La quantite a transferer doit etre strictement positive. |
| 404 | `BATCH_NOT_FOUND` | Lot introuvable. |
| 422 | `BATCH_ITEM_MISMATCH` | Le lot scanne ne correspond pas a cet article. |
| 422 | `INSUFFICIENT_STOCK` | Stock insuffisant en quarantaine. |
| 500 | `INTERNAL_ERROR` | Erreur interne pendant le transfert du lot. |

### Notas de implementación

- El saldo previo se valida con `stock_utils.get_stock_lote_almacen` antes de crear el movimiento.
- El `Stock Entry` se inserta y submittea como usuario sistema para evitar bloqueos de permisos operativos sobre stock.
- El endpoint acepta badges `production`, `quality` y `reception`.

### curl

```bash
curl -X POST http://localhost:8080/api/method/gcma_kiosco.api.recepcion.trasladar_lote_aprobado \
  -b "sid=<session_id>" \
  -d "item_code=MP-RES-ALK-G70" \
  -d "batch_no=LOTE-QA-RECEP-0001" \
  -d "qty_to_move=5" \
  -d "source_warehouse=Cuarentena MP - PDM" \
  -d "target_warehouse=Materia Prima Aprobada - PDM"
```

### EP_REC_4 — Obtener Datos de Etiqueta para Reimpresión

Reconstruye los datos mínimos de Zebra a partir del `Batch` y del `Item` nativo, sin depender del `Purchase Receipt` original.

| Campo | Valor |
|-------|-------|
| **Ruta** | `GET /api/method/gcma_kiosco.api.recepcion.get_lote_para_impresion` |
| **Auth** | Sesión requerida (cookie `sid`) |

### Request

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `batch_no` | string | Sí | Lote interno a reimprimir |

### Response (200 OK)

```json
{
  "success": true,
  "etiqueta": {
    "item_code": "MP-RES-ALK-G70",
    "item_name": "Résine Alkyde G-70",
    "batch_no": "LOTE-QA-RECEP-0001",
    "expiry_date": "2027-12-31"
  },
  "message_fr": "Donnees de reimpression chargees."
}
```

### Errores

| HTTP | `error_code` | `message_fr` |
|------|-------------|-------------|
| 400 | `MISSING_PARAMS` | Parametre 'batch_no' obligatoire. |
| 404 | `BATCH_NOT_FOUND` | Lot introuvable. |
| 500 | `INTERNAL_ERROR` | Erreur interne lors de la lecture de l'etiquette. |

### curl

```bash
curl "http://localhost:8080/api/method/gcma_kiosco.api.recepcion.get_lote_para_impresion?batch_no=LOTE-QA-RECEP-0001" \
  -b "sid=<session_id>"
```

### EP_REC_5 — Subir Conteo Fisico

Crea un `Stock Reconciliation` en borrador a partir de un conteo ciego offline. Solo persiste las lineas donde existe diferencia real contra el stock actual del warehouse seleccionado.

| Campo | Valor |
|-------|-------|
| **Ruta** | `POST /api/method/gcma_kiosco.api.recepcion.subir_conteo_fisico` |
| **Auth** | Sesión requerida (cookie `sid`) |

### Request

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `warehouse` | string | Sí | Warehouse auditado |
| `conteo` | string (JSON) | Sí | Array JSON de `{item_code, batch_no, qty_fisica}` |

### Response (200 OK)

```json
{
  "success": true,
  "reconciliation_doc": "MAT-RECO-2026-00002",
  "warehouse": "Materia Prima Aprobada - PDM",
  "items_count": 1,
  "message_fr": "Comptage envoye en brouillon pour reconciliation."
}
```

### Errores

| HTTP | `error_code` | `message_fr` |
|------|-------------|-------------|
| 400 | `MISSING_PARAMS` | Parametres obligatoires: warehouse et conteo. |
| 400 | `INVALID_CONTEO_JSON` | Format JSON invalide pour conteo. |
| 400 | `INVALID_CONTEO_TYPE` | conteo doit etre une liste. |
| 400 | `MISSING_ITEM_CODE` | Chaque ligne doit contenir item_code. |
| 400 | `MISSING_BATCH_NO` | Chaque ligne doit contenir batch_no. |
| 400 | `INVALID_QTY` | Chaque quantite physique doit etre strictement positive. |
| 404 | `WAREHOUSE_NOT_FOUND` | Entrepot introuvable. |
| 404 | `ITEM_NOT_FOUND` | Article introuvable dans ERPNext. |
| 404 | `BATCH_NOT_FOUND` | Lot introuvable dans ERPNext. |
| 422 | `BATCH_ITEM_MISMATCH` | Le lot scanne ne correspond pas a cet article. |
| 422 | `NO_DIFFERENCES_FOUND` | Aucune difference detectee entre le comptage physique et le stock systeme. |
| 500 | `INTERNAL_ERROR` | Erreur interne pendant la creation du brouillon de reconciliation. |

### Notas de implementación

- El endpoint agrega filas repetidas por `(item_code, batch_no)` antes de generar el borrador.
- Cada línea calcula `current_qty` mediante `stock_utils.get_stock_lote_almacen`.
- Si una línea no cambia la cantidad real contra el sistema, se omite del documento final.
- Si ninguna línea genera diferencia, el endpoint rechaza con `NO_DIFFERENCES_FOUND`.
- El `Stock Reconciliation` se crea en `docstatus = 0`; la aprobación contable queda fuera del kiosco.

### curl

```bash
curl -X POST http://localhost:8080/api/method/gcma_kiosco.api.recepcion.subir_conteo_fisico \
  -b "sid=<session_id>" \
  -d "warehouse=Materia Prima Aprobada - PDM" \
  --data-urlencode 'conteo=[{"item_code":"MP-RES-ALK-G70","batch_no":"LOTE-CIEGO-2026-0001","qty_fisica":10}]'
```

---

## Bloque 4 — Control de Calidad

Los endpoints de laboratorio viven en el módulo `gcma_kiosco.api.calidad` y se apoyan en los doctypes nativos `Quality Inspection`, `Quality Inspection Reading`, `Serial and Batch Entry` y `Stock Entry`.

### EP6 — Listar Lotes en Cuarentena

Devuelve los lotes de producto terminado con saldo positivo en `Cuarentena PT - <ABBR>`.

| Campo | Valor |
|-------|-------|
| **Ruta** | `GET /api/method/gcma_kiosco.api.calidad.get_lotes_cuarentena` |
| **Auth** | Sesión requerida (cookie `sid`) |

### Request

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `warehouse` | string | No | Almacén de cuarentena a consultar. Por defecto `Cuarentena PT - PDM`. |

### Response (200 OK)

```json
{
  "success": true,
  "warehouse": "Cuarentena PT - PDM",
  "lotes": [
    {
      "item_code": "PT-PIN-BLC-MAT-20L",
      "item_name": "Peinture Blanche Mate 20L",
      "batch_no": "LOTE-CHAOS-PT-001",
      "uom": "Nos",
      "qty": 5.0,
      "fecha_fabricacion": "2026-03-10"
    }
  ],
  "total": 1
}
```

### Errores

| HTTP | `error_code` | `message_fr` | Causa |
|------|-------------|-------------|-------|
| 500 | `INTERNAL_ERROR` | Erreur interne lors de la consultation... | Excepción no controlada |

### Notas de implementación

- En ERPNext v16 el saldo por lote de este flujo se calcula desde `Serial and Batch Entry` con fallback legacy a `Stock Ledger Entry` sin bundle.
- No confiar en `SLE.batch_no` como única fuente para PT en cuarentena; puede venir nulo aunque el lote exista y el stock sea correcto.

### curl

```bash
curl "http://localhost:8080/api/method/gcma_kiosco.api.calidad.get_lotes_cuarentena" \
  -b "sid=<session_id>"
```

### EP7 — Aprobar Calidad / Liberar Lote

Registra una inspección de laboratorio nativa y, si el resultado es aprobado, crea un `Stock Entry` `Material Transfer` desde `Cuarentena PT - PDM` hacia `Producto Terminado - PDM`.

| Campo | Valor |
|-------|-------|
| **Ruta** | `POST /api/method/gcma_kiosco.api.calidad.aprobar_calidad` |
| **Auth** | Sesión requerida (cookie `sid`) |

### Request

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `item_code` | string | Sí | Código del producto terminado |
| `batch_no` | string | Sí | Lote inspeccionado |
| `qty` | float | Sí | Cantidad a inspeccionar/liberar |
| `parametros` | string (JSON) | Sí | Mapa JSON `nombre_parametro -> valor` o array de filas manuales |
| `aprobada` | bool/string | No | `1/true/oui/approuve` para aprobar. Si falta, se usa `resultado`. |
| `resultado` | string | No | `Approved` o `Rejected` |
| `remarks` | string | No | Observaciones del laboratorio |

### Response — Aprobado (200 OK)

```json
{
  "success": true,
  "quality_inspection": "MAT-QA-2026-00001",
  "stock_entry": "MAT-STE-2026-00010",
  "item_code": "PT-PIN-BLC-MAT-20L",
  "batch_no": "LOTE-CHAOS-PT-001",
  "qty": 1.0,
  "quality_status": "Accepted",
  "message_fr": "Inspection qualité approuvée. Lot libéré vers le stock vendable."
}
```

### Response — Rechazado (200 OK)

```json
{
  "success": true,
  "quality_inspection": "MAT-QA-2026-00002",
  "item_code": "PT-PIN-BLC-MAT-20L",
  "batch_no": "LOTE-CHAOS-PT-001",
  "qty": 1.0,
  "quality_status": "Rejected",
  "message_fr": "Inspection qualité enregistrée. Lot maintenu en quarantaine."
}
```

### Errores

| HTTP | `error_code` | `message_fr` | Causa |
|------|-------------|-------------|-------|
| 400 | `MISSING_PARAMS` | Paramètres obligatoires... | Faltan `item_code`, `batch_no` o `qty` |
| 400 | `MISSING_PARAMETERS` | Aucun paramètre laboratoire reçu... | `parametros` vacío o inválido |
| 404 | `ITEM_NOT_FOUND` | Article introuvable. | El item no existe |
| 404 | `BATCH_NOT_FOUND` | Lot introuvable. | El lote no existe |
| 422 | `INVALID_QTY` | La quantité inspectée doit être supérieure à zéro. | `qty <= 0` |
| 422 | `INVALID_RESULT` | Résultat qualité invalide... | `aprobada/resultado` incoherentes |
| 422 | `BATCH_ITEM_MISMATCH` | Le lot indiqué ne correspond pas... | El lote pertenece a otro item |
| 422 | `NO_STOCK_IN_QUARANTINE` | Aucun stock disponible... | No hay saldo del lote en cuarentena |
| 422 | `QTY_EXCEEDS_AVAILABLE` | Quantité demandée supérieure... | Se intenta liberar más de lo disponible |
| 422 | `MISSING_REFERENCE_STOCK_ENTRY` | Aucun document stock d'origine trouvé... | ERPNext no encontró el `Stock Entry` nativo que originó el lote en cuarentena |
| 422 | `ERP_VALIDATION_ERROR` | Transaction refusée par ERPNext... | ERPNext rechaza la inspección o el movimiento |
| 500 | `INTERNAL_ERROR` | Erreur interne lors de la validation... | Excepción no controlada |

### Lógica interna

1. Valida item, lote, parámetros y cantidad
2. Calcula saldo en cuarentena desde `Serial and Batch Entry` con fallback legacy
3. Si está aprobado, crea y submit un `Stock Entry` `Material Transfer`
4. Si está rechazado, crea y submit un `Quality Inspection` manual ligado al `Stock Entry` que metió el lote en cuarentena
5. Si está aprobado, crea y submit un `Quality Inspection` manual ligado al `Stock Entry` de liberación
6. ERPNext rellena `quality_inspection` en la línea del `Stock Entry Detail` cuando existe movimiento de liberación
7. Si está rechazado, solo registra la inspección y mantiene el stock en cuarentena

### curl

```bash
curl -X POST http://localhost:8080/api/method/gcma_kiosco.api.calidad.aprobar_calidad \
  -b "sid=<session_id>" \
  -d "item_code=PT-PIN-BLC-MAT-20L" \
  -d "batch_no=LOTE-CHAOS-PT-001" \
  -d "qty=1" \
  -d 'parametros={"pH":8.4,"viscosité KU":96,"aspect":"Conforme"}' \
  -d "aprobada=1" \
  -d "remarks=Libération test laboratoire"
```

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
