"""
GCMA Kiosco — Endpoints REST para la PWA del operario.

Rutas base: /api/method/gcma_kiosco.api.kiosco.<nombre_metodo>

Arquitectura completa documentada en: _kiosco_architecture.py

Endpoints implementados:
  [✓] EP1 — login_operario     (POST, auth por QR badge)
  [✓] EP2 — get_tareas          (GET,  Work Orders pendientes)
  [✓] EP3 — validar_material    (POST, Poka-Yoke escaneo MP)
  [ ] EP4 — reportar_consumo    (POST, consumo real post-mezcla)
  [ ] EP5 — info_lote           (GET,  consulta informativa lote)
"""

import frappe
from frappe import _
from frappe.utils import today, date_diff, getdate, flt
from gcma_kiosco.api.qr_utils import parse_qr_material


# ═══════════════════════════════════════════════════════════════════════════
# CSRF — Eximir las rutas del Kiosco (PWA servida desde origen distinto)
# ═══════════════════════════════════════════════════════════════════════════
def exempt_csrf():
    """Hook before_request: desactiva la verificación CSRF para los
    endpoints del módulo Kiosco. La PWA no recibe la cookie csrf_token
    porque se sirve desde un origen diferente al de Frappe."""
    if frappe.request and frappe.request.path.startswith(
        "/api/method/gcma_kiosco."
    ):
        frappe.flags.ignore_csrf = True


# ═══════════════════════════════════════════════════════════════════════════
# EP1 — AUTENTICACIÓN DEL OPERARIO POR QR BADGE
# ═══════════════════════════════════════════════════════════════════════════
#
# El operario escanea su badge QR personal al inicio del turno.
# El QR contiene un token único (ej. "OP-2026-BADGE-00042").
# El Kiosco NO tiene teclado — el QR es el único medio de login.
#
# Ruta: POST /api/method/gcma_kiosco.api.kiosco.login_operario
# Test: curl -X POST http://localhost:8080/api/method/gcma_kiosco.api.kiosco.login_operario \
#         -H "Content-Type: application/json" \
#         -d '{"qr_token": "OP-2026-BADGE-00042"}'
# ═══════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=True)
def login_operario(qr_token: str = None):
    """Autentica un operario a partir del token embebido en su badge QR.

    Flujo:
        1. Buscar Employee con custom_qr_badge_token == qr_token
        2. Verificar que el Employee está activo
        3. Verificar que tiene un User vinculado
        4. Crear sesión Frappe para ese User
        5. Devolver datos del operario (nombre, empresa, almacén)

    Guardrails aplicados:
        G1 — Mensajes siempre en francés, sin tracebacks
        G3 — Nunca se expone item_code al operario
    """
    # ── Validación de entrada ──
    if not qr_token or not isinstance(qr_token, str):
        frappe.local.response["http_status_code"] = 400
        return {
            "success": False,
            "error_code": "MISSING_TOKEN",
            "message_fr": "Code QR manquant. Veuillez scanner votre badge.",
        }

    qr_token = qr_token.strip()

    try:
        # ── Buscar empleado por token de badge ──
        employee = frappe.db.get_value(
            "Employee",
            {"custom_qr_badge_token": qr_token},
            ["name", "employee_name", "user_id", "company", "status"],
            as_dict=True,
        )

        # Badge no encontrado en la BD
        if not employee:
            frappe.local.response["http_status_code"] = 401
            return {
                "success": False,
                "error_code": "INVALID_BADGE",
                "message_fr": "Badge non reconnu. Veuillez contacter le superviseur.",
            }

        # Empleado existe pero está desactivado
        if employee.status != "Active":
            frappe.local.response["http_status_code"] = 403
            return {
                "success": False,
                "error_code": "EMPLOYEE_INACTIVE",
                "message_fr": "Compte désactivé. Contactez les Ressources Humaines.",
            }

        # Empleado activo pero sin User vinculado (falta configuración)
        if not employee.user_id:
            frappe.local.response["http_status_code"] = 403
            return {
                "success": False,
                "error_code": "NO_USER_LINKED",
                "message_fr": "Aucun compte utilisateur lié. Contactez l'administrateur.",
            }

        # ── Crear sesión Frappe para el usuario del operario ──
        frappe.local.login_manager.login_as(employee.user_id)

        # ── Obtener datos complementarios ──
        company = employee.company
        abbr = frappe.db.get_value("Company", company, "abbr")
        default_wip = f"Planta Mezclas WIP - {abbr}" if abbr else None

        return {
            "success": True,
            "operario": {
                "full_name": employee.employee_name,
                "employee_id": employee.name,
                "company": company,
                "company_abbr": abbr,
                "default_warehouse": default_wip,
            },
            "sid": frappe.session.sid,
            "message_fr": f"Bienvenue, {employee.employee_name}.",
        }

    except frappe.AuthenticationError:
        frappe.local.response["http_status_code"] = 401
        return {
            "success": False,
            "error_code": "AUTH_FAILED",
            "message_fr": "Erreur d'authentification. Contactez l'administrateur.",
        }
    except Exception:
        # G1: log completo para el admin, mensaje limpio para el operario
        frappe.log_error(
            title=f"Erreur login kiosque — badge {qr_token}",
            message=frappe.get_traceback(),
        )
        frappe.local.response["http_status_code"] = 500
        return {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message_fr": "Erreur interne. Veuillez contacter l'administrateur.",
        }


# ═══════════════════════════════════════════════════════════════════════════
# EP2 — OBTENER TAREAS (Work Orders pendientes)
# ═══════════════════════════════════════════════════════════════════════════
#
# Después del login, el Kiosco muestra las Work Orders asignadas.
# Pantalla tipo "lista de tareas" con botones grandes.
#
# Ruta: GET /api/method/gcma_kiosco.api.kiosco.get_tareas
# Test: curl http://localhost:8000/api/method/gcma_kiosco.api.kiosco.get_tareas \
#         -H "Host: frontend" -G \
#         -d "company=Peintures du Maroc SARL" \
#         -d "warehouse=Planta Mezclas WIP - PDM"
# ═══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_tareas(company: str = None, warehouse: str = None):
    """Devuelve las Work Orders pendientes para el Kiosco.

    Filtra WOs con status In Process o Not Started, docstatus=1.
    Para cada WO, explota la BOM y verifica stock disponible.
    Guardrail G3: nunca expone item_code, solo item_name.
    """
    # ── Validación de entrada ──
    if not company:
        frappe.local.response["http_status_code"] = 400
        return {
            "success": False,
            "error_code": "MISSING_COMPANY",
            "message_fr": "Paramètre 'company' obligatoire.",
        }

    try:
        # ── Obtener Work Orders pendientes ──
        filters = {
            "company": company,
            "status": ["in", ["Not Started", "In Process"]],
            "docstatus": 1,
        }

        work_orders = frappe.get_all(
            "Work Order",
            filters=filters,
            fields=[
                "name", "production_item", "qty", "produced_qty",
                "bom_no", "status", "planned_start_date",
                "wip_warehouse", "stock_uom",
            ],
            order_by="planned_start_date asc, name asc",
        )

        # Si se filtra por warehouse, solo mostrar las de ese WIP
        if warehouse:
            work_orders = [
                wo for wo in work_orders if wo.get("wip_warehouse") == warehouse
            ]

        tareas = []
        for wo in work_orders:
            tarea = _build_tarea_detail(wo)
            tareas.append(tarea)

        result = {"tareas": tareas, "total": len(tareas)}
        if not tareas:
            result["message_fr"] = "Aucun ordre de fabrication en attente."

        return result

    except Exception:
        frappe.log_error(
            title="Erreur get_tareas kiosque",
            message=frappe.get_traceback(),
        )
        frappe.local.response["http_status_code"] = 500
        return {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message_fr": "Erreur interne. Veuillez contacter l'administrateur.",
        }


def _build_tarea_detail(wo: dict) -> dict:
    """Construye el detalle de una tarea a partir de un Work Order.

    Explota la BOM, traduce item_code→item_name (G3), calcula stock disponible.
    """
    item_name = frappe.db.get_value("Item", wo.production_item, "item_name") or wo.production_item
    qty_pendiente = flt(wo.qty) - flt(wo.produced_qty)

    # ── Obtener materiales de la BOM ──
    materiales = []
    if wo.bom_no and frappe.db.exists("BOM", wo.bom_no):
        bom_doc = frappe.get_doc("BOM", wo.bom_no)
        abbr = frappe.db.get_value("Company", wo.get("company") or bom_doc.company, "abbr")
        wh_mp = f"Materia Prima Aprobada - {abbr}" if abbr else None

        for bom_item in bom_doc.items:
            qty_requerida = flt(bom_item.qty) * flt(qty_pendiente)

            qty_disponible = 0.0
            if wh_mp:
                qty_disponible = flt(
                    frappe.db.get_value(
                        "Bin",
                        {"item_code": bom_item.item_code, "warehouse": wh_mp},
                        "actual_qty",
                    )
                )

            mat_name = frappe.db.get_value("Item", bom_item.item_code, "item_name") or bom_item.item_code

            materiales.append({
                "item_name": mat_name,              # G3: nunca item_code
                "qty_requerida": round(qty_requerida, 2),
                "uom": bom_item.uom,
                "qty_disponible": round(qty_disponible, 2),
                "suficiente": qty_disponible >= qty_requerida,
            })

    return {
        "work_order": wo.name,
        "producto": item_name,                      # G3: item_name, no item_code
        "cantidad": flt(wo.qty),
        "cantidad_pendiente": round(qty_pendiente, 2),
        "uom": wo.stock_uom,
        "bom": wo.bom_no,
        "estado": wo.status,
        "fecha_inicio_plan": str(wo.planned_start_date) if wo.planned_start_date else None,
        "materiales": materiales,
    }


# ═══════════════════════════════════════════════════════════════════════════
# EP3 — VALIDAR MATERIAL (Poka-Yoke)
# ═══════════════════════════════════════════════════════════════════════════
#
# El operario seleccionó una Work Order y escanea el QR del bidón de MP.
# El backend valida:
#   ✓ ¿Es el material correcto para esta BOM?
#   ✓ ¿El lote no está caducado?
#   ✓ ¿Hay stock suficiente de este lote?
#
# Ruta: POST /api/method/gcma_kiosco.api.kiosco.validar_material
# Test: curl -X POST http://localhost:8000/api/method/gcma_kiosco.api.kiosco.validar_material \
#         -H "Host: frontend" \
#         -d "work_order=WO-00001" \
#         -d "qr_data=MP-RES-ALK-G70|LOTE-TEST-RES-001"
# ═══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def validar_material(work_order: str = None, qr_data: str = None):
    """Valida un escaneo Poka-Yoke: material correcto, lote vigente, stock OK.

    Guardrails:
        G1 — Mensajes en francés, sin tracebacks
        G3 — Responde con item_name, nunca con item_code
    """
    # ── Validación de entrada ──
    if not work_order or not qr_data:
        frappe.local.response["http_status_code"] = 400
        return {
            "valido": False,
            "error_code": "MISSING_PARAMS",
            "message_fr": "Paramètres 'work_order' et 'qr_data' obligatoires.",
        }

    try:
        # ── Parsear QR ──
        item_code, batch_no = parse_qr_material(qr_data.strip())
        if not item_code or not batch_no:
            frappe.local.response["http_status_code"] = 400
            return {
                "valido": False,
                "error_code": "INVALID_QR",
                "message_fr": "Code QR illisible. Réessayez ou saisissez manuellement le numéro de lot.",
            }

        # ── Verificar que la Work Order existe y está activa ──
        wo_data = frappe.db.get_value(
            "Work Order",
            {"name": work_order, "docstatus": 1},
            ["name", "status", "bom_no", "qty", "produced_qty", "company"],
            as_dict=True,
        )
        if not wo_data:
            frappe.local.response["http_status_code"] = 404
            return {
                "valido": False,
                "error_code": "WO_NOT_FOUND",
                "message_fr": "Ordre de fabrication introuvable ou non validé.",
            }

        if wo_data.status not in ("Not Started", "In Process"):
            return {
                "valido": False,
                "error_code": "WO_NOT_IN_PROCESS",
                "message_fr": "Cet ordre de fabrication n'est pas en cours. Vérifiez avec le superviseur.",
            }

        # ── Verificar que el item pertenece a la BOM ──
        bom_items = frappe.get_all(
            "BOM Item",
            filters={"parent": wo_data.bom_no},
            fields=["item_code", "qty", "uom"],
        )
        bom_item_codes = [bi.item_code for bi in bom_items]

        if item_code not in bom_item_codes:
            # Material incorrecto → STOP Poka-Yoke
            item_name_scanned = frappe.db.get_value("Item", item_code, "item_name") or item_code
            expected_names = [
                frappe.db.get_value("Item", ic, "item_name") or ic
                for ic in bom_item_codes
            ]
            return {
                "valido": False,
                "error_code": "WRONG_MATERIAL",
                "item_escaneado": item_name_scanned,
                "items_esperados": expected_names,
                "message_fr": "✗ STOP — Ce matériau ne correspond pas à la recette. Vérifiez l'étiquette.",
                "alerta_nivel": "CRITICO",
            }

        # ── Verificar que el Batch existe ──
        if not frappe.db.exists("Batch", batch_no):
            return {
                "valido": False,
                "error_code": "BATCH_NOT_FOUND",
                "message_fr": f"✗ Lot '{batch_no}' introuvable dans le système.",
            }

        # ── Verificar caducidad ──
        batch_data = frappe.db.get_value(
            "Batch", batch_no, ["expiry_date", "item"], as_dict=True
        )

        # Verificar que el batch corresponde al item escaneado
        if batch_data.item != item_code:
            item_name_scanned = frappe.db.get_value("Item", item_code, "item_name") or item_code
            return {
                "valido": False,
                "error_code": "BATCH_ITEM_MISMATCH",
                "message_fr": f"✗ Le lot '{batch_no}' ne correspond pas à ce matériau.",
            }

        dias_restantes = None
        fecha_caducidad = None
        if batch_data.expiry_date:
            fecha_caducidad = str(batch_data.expiry_date)
            dias_restantes = date_diff(batch_data.expiry_date, today())
            if dias_restantes < 0:
                item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code
                return {
                    "valido": False,
                    "error_code": "BATCH_EXPIRED",
                    "item_name": item_name,
                    "batch_no": batch_no,
                    "fecha_caducidad": fecha_caducidad,
                    "message_fr": f"✗ STOP — Lot périmé depuis le {batch_data.expiry_date}. Ne pas utiliser.",
                    "alerta_nivel": "CRITICO",
                }

        # ── Verificar stock disponible del item en MP Aprobada ──
        abbr = frappe.db.get_value("Company", wo_data.company, "abbr")
        wh_mp = f"Materia Prima Aprobada - {abbr}"

        qty_en_almacen = flt(
            frappe.db.get_value(
                "Bin",
                {"item_code": item_code, "warehouse": wh_mp},
                "actual_qty",
            )
        )

        # Cantidad requerida por la BOM para las unidades pendientes
        qty_pendiente = flt(wo_data.qty) - flt(wo_data.produced_qty)
        bom_match = next(bi for bi in bom_items if bi.item_code == item_code)
        qty_requerida = flt(bom_match.qty) * qty_pendiente

        if qty_en_almacen <= 0:
            item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code
            return {
                "valido": False,
                "error_code": "NO_STOCK",
                "item_name": item_name,
                "batch_no": batch_no,
                "qty_disponible": 0,
                "message_fr": f"✗ Pas de stock disponible pour '{item_name}' dans l'entrepôt MP.",
            }

        # ── Todo OK → Validación Poka-Yoke superada ──
        item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code

        return {
            "valido": True,
            "item_name": item_name,
            "batch_no": batch_no,
            "fecha_caducidad": fecha_caducidad,
            "dias_restantes": dias_restantes,
            "qty_disponible": round(qty_en_almacen, 2),
            "qty_requerida_bom": round(qty_requerida, 2),
            "uom": bom_match.uom,
            "message_fr": "✓ Matériau vérifié. Vous pouvez verser.",
        }

    except Exception:
        frappe.log_error(
            title=f"Erreur validar_material kiosque — WO {work_order}",
            message=frappe.get_traceback(),
        )
        frappe.local.response["http_status_code"] = 500
        return {
            "valido": False,
            "error_code": "INTERNAL_ERROR",
            "message_fr": "Erreur interne. Veuillez contacter l'administrateur.",
        }


# ═══════════════════════════════════════════════════════════════════════════
# EP4 — REPORTAR CONSUMO REAL
# ═══════════════════════════════════════════════════════════════════════════
# TODO: Tercer módulo pendiente.
# Arquitectura detallada en: _kiosco_architecture.py → ENDPOINT 4

# ═══════════════════════════════════════════════════════════════════════════
# EP5 — INFO LOTE (consulta rápida)
# ═══════════════════════════════════════════════════════════════════════════
# TODO: Cuarto módulo pendiente.
# Arquitectura detallada en: _kiosco_architecture.py → ENDPOINT 5
