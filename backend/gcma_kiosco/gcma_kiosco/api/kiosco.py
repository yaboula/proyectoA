"""
GCMA Kiosco — Endpoints REST para la PWA del operario.

Rutas base: /api/method/gcma_kiosco.api.kiosco.<nombre_metodo>

Arquitectura completa documentada en: _kiosco_architecture.py

Endpoints implementados:
  [✓] EP1 — login_operario     (POST, auth por QR badge)
  [✓] EP2 — get_tareas          (GET,  Work Orders pendientes)
  [✓] EP3 — validar_material    (POST, Poka-Yoke escaneo MP)
    [✓] EP4 — reportar_consumo    (POST, consumo real post-mezcla)
    [✓] EP5 — info_lote           (GET,  consulta informativa lote)
"""

from contextlib import contextmanager

import frappe
from frappe import _
from frappe.utils import today, date_diff, getdate, get_datetime, flt, cint
from gcma_kiosco.api.qr_utils import parse_qr_material
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry as erpnext_make_stock_entry
from erpnext.stock.serial_batch_bundle import SerialBatchCreation
from gcma_kiosco.api.stock_utils import get_stock_lote_almacen, get_stock_lote_detallado


KIOSK_PROFILE_CONFIG = {
    "production": {
        "label": "Production",
        "allowed_modules": ["production", "reception"],
        "default_route": "/tareas",
    },
    "quality": {
        "label": "Laboratoire",
        "allowed_modules": ["quality", "reception"],
        "default_route": "/laboratoire",
    },
    "comercial": {
        "label": "Commercial B2B",
        "allowed_modules": ["comercial"],
        "default_route": "/rutas-comercial",
    },
    "logistica": {
        "label": "Logistique",
        "allowed_modules": ["logistica"],
        "default_route": "/picking-fefo",
    },
    "reception": {
        "label": "Reception",
        "allowed_modules": ["reception"],
        "default_route": "/recepcion",
    },
}


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


def _build_operario_payload(employee: dict):
    company = employee.get("company")
    abbr = frappe.db.get_value("Company", company, "abbr") if company else None
    default_wip = f"Planta Mezclas WIP - {abbr}" if abbr else None
    profile_code, profile_config = _resolve_kiosk_profile(employee)

    return {
        "full_name": employee.get("employee_name"),
        "employee_id": employee.get("name"),
        "company": company,
        "company_abbr": abbr,
        "default_warehouse": default_wip,
        "profile_code": profile_code,
        "profile_label": profile_config["label"],
        "allowed_modules": profile_config["allowed_modules"],
        "default_route": profile_config["default_route"],
    }


def _resolve_kiosk_profile(employee: dict):
    profile_code = (employee.get("custom_kiosk_profile") or "production").strip().lower()
    return profile_code, KIOSK_PROFILE_CONFIG.get(profile_code, KIOSK_PROFILE_CONFIG["production"])


def _build_profile_error_response(*allowed_profiles: str):
    labels = [KIOSK_PROFILE_CONFIG.get(profile, {}).get("label", profile) for profile in allowed_profiles]
    frappe.local.response["http_status_code"] = 403
    return {
        "success": False,
        "error_code": "PROFILE_NOT_ALLOWED",
        "message_fr": f"Accès refusé. Ce badge n'est pas autorisé pour le module {', '.join(labels)}.",
    }


def _require_kiosk_profile(*allowed_profiles: str):
    employee = _get_operario_for_user(frappe.session.user)
    if not employee:
        frappe.local.response["http_status_code"] = 401
        return {
            "success": False,
            "error_code": "NO_ACTIVE_SESSION",
            "message_fr": "Session expirée. Veuillez scanner votre badge à nouveau.",
        }

    profile_code, _profile_config = _resolve_kiosk_profile(employee)
    if allowed_profiles and profile_code not in allowed_profiles:
        return _build_profile_error_response(*allowed_profiles)

    return None


def _get_operario_for_user(user_id: str):
    if not user_id or user_id == "Guest":
        return None

    return frappe.db.get_value(
        "Employee",
        {"user_id": user_id, "status": "Active"},
        ["name", "employee_name", "user_id", "company", "status", "custom_kiosk_profile"],
        as_dict=True,
    )


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
            ["name", "employee_name", "user_id", "company", "status", "custom_kiosk_profile"],
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
        return {
            "success": True,
            "operario": _build_operario_payload(employee),
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


@frappe.whitelist(allow_guest=True)
def get_operario_session():
    """Restaura la sesión del kiosco a partir del sid actual de Frappe."""
    user_id = frappe.session.user
    employee = _get_operario_for_user(user_id)

    if not employee:
        frappe.local.response["http_status_code"] = 401
        return {
            "success": False,
            "error_code": "NO_ACTIVE_SESSION",
            "message_fr": "Session expirée. Veuillez scanner votre badge à nouveau.",
        }

    return {
        "success": True,
        "operario": _build_operario_payload(employee),
        "sid": frappe.session.sid,
    }


@frappe.whitelist()
def logout_operario():
    """Cierra la sesión Frappe del operario en el navegador actual."""
    try:
        if getattr(frappe.local, "login_manager", None):
            frappe.local.login_manager.logout()
        frappe.local.cookie_manager.delete_cookie("sid")
    except Exception:
        frappe.log_error(
            title="Erreur logout kiosque",
            message=frappe.get_traceback(),
        )

    return {
        "success": True,
        "message_fr": "Session fermée.",
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
    profile_error = _require_kiosk_profile("production")
    if profile_error:
        return profile_error

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
    profile_error = _require_kiosk_profile("production")
    if profile_error:
        return profile_error

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

        item_meta = frappe.db.get_value(
            "Item", item_code, ["item_name", "has_batch_no"], as_dict=True
        ) or {}

        dias_restantes = None
        fecha_caducidad = None

        # ── Items con lote obligatorio ──
        if cint(item_meta.get("has_batch_no")):
            if not frappe.db.exists("Batch", batch_no):
                return {
                    "valido": False,
                    "error_code": "BATCH_NOT_FOUND",
                    "message_fr": f"✗ Lot '{batch_no}' introuvable dans le système.",
                }

            batch_data = frappe.db.get_value(
                "Batch", batch_no, ["expiry_date", "item"], as_dict=True
            )

            if batch_data.item != item_code:
                return {
                    "valido": False,
                    "error_code": "BATCH_ITEM_MISMATCH",
                    "message_fr": f"✗ Le lot '{batch_no}' ne correspond pas à ce matériau.",
                }

            if batch_data.expiry_date:
                fecha_caducidad = str(batch_data.expiry_date)
                dias_restantes = date_diff(batch_data.expiry_date, today())
                if dias_restantes < 0:
                    item_name = item_meta.get("item_name") or item_code
                    return {
                        "valido": False,
                        "error_code": "BATCH_EXPIRED",
                        "item_name": item_name,
                        "batch_no": batch_no,
                        "fecha_caducidad": fecha_caducidad,
                        "message_fr": f"✗ STOP — Lot périmé depuis le {batch_data.expiry_date}. Ne pas utiliser.",
                        "alerta_nivel": "CRITICO",
                    }
        else:
            if batch_no.upper() not in ("SIN-LOTE", "NO-LOT", "N/A"):
                return {
                    "valido": False,
                    "error_code": "LOT_NOT_ALLOWED",
                    "message_fr": "✗ Ce matériau ne fonctionne pas avec un lot réel. Scannez l'étiquette 'SIN-LOTE'.",
                }

        # ── Verificar stock disponible del item en MP Aprobada ──
        abbr = frappe.db.get_value("Company", wo_data.company, "abbr")
        wh_mp = f"Materia Prima Aprobada - {abbr}"

        qty_en_almacen = get_stock_lote_almacen(item_code, wh_mp, batch_no)

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
        item_name = item_meta.get("item_name") or item_code

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
# EP4 — REPORTAR CONSUMO REAL (Post-mezcla)
# ═══════════════════════════════════════════════════════════════════════════
#
# Al terminar la mezcla, el operario confirma si hubo cantidades extra.
# El backend calcula desviaciones vs BOM teórica y registra el consumo.
#
# Ruta: POST /api/method/gcma_kiosco.api.kiosco.reportar_consumo
# Test: curl -X POST http://localhost:8080/api/method/gcma_kiosco.api.kiosco.reportar_consumo \
#         -d "work_order=MFG-WO-2026-00001" \
#         -d 'extras=[]'
# ═══════════════════════════════════════════════════════════════════════════

def _parse_json_param(raw_value, default):
    import json as _json

    if raw_value in (None, ""):
        return default

    if isinstance(raw_value, (dict, list)):
        return raw_value

    try:
        return _json.loads(raw_value)
    except (TypeError, ValueError):
        return default


def _normalize_consumos_extra(consumos_extra=None, extras=None):
    extras_map = {}

    payload = consumos_extra
    if not payload:
        payload = _parse_json_param(extras, [])

    if isinstance(payload, list):
        for row in payload:
            key = (row.get("item_code") or row.get("item_name") or "").strip()
            qty = flt(row.get("qty_extra", row.get("qty", 0)))
            if key and qty > 0:
                extras_map[key] = qty
    elif isinstance(payload, dict):
        for key, qty in payload.items():
            if key and flt(qty) > 0:
                extras_map[key] = flt(qty)

    return extras_map


def _normalize_lotes_usados(lotes_usados=None):
    payload = _parse_json_param(lotes_usados, {})
    if not isinstance(payload, dict):
        return {}

    result = {}
    for key, batch_no in payload.items():
        key = (key or "").strip()
        batch_no = (batch_no or "").strip()
        if key and batch_no:
            result[key] = batch_no
    return result


def _resolve_item_key_maps(wo_doc):
    item_names = {}
    for row in wo_doc.required_items:
        item_name = frappe.db.get_value("Item", row.item_code, "item_name") or row.item_code
        item_names[row.item_code] = item_name
    name_to_code = {name: code for code, name in item_names.items()}
    return item_names, name_to_code


def _resolve_source_warehouse(item_code: str, company_abbr: str, preferred: str | None = None, batch_no: str = None):
    candidates = []
    if preferred:
        candidates.append(preferred)
    candidates.append(f"Materia Prima Aprobada - {company_abbr}")
    candidates.append(f"Cuarentena MP - {company_abbr}")

    seen = set()
    for warehouse in candidates:
        if warehouse and warehouse not in seen:
            seen.add(warehouse)
            qty = get_stock_lote_almacen(item_code, warehouse, batch_no)
            if qty > 0:
                return warehouse

    bins = frappe.get_all(
        "Bin",
        filters={"item_code": item_code, "actual_qty": [">", 0]},
        fields=["warehouse", "actual_qty"],
        order_by="actual_qty desc",
    )
    if not batch_no and bins:
        return bins[0].warehouse
    
    # If batch specific, need to check entries directly since Bin may not have it
    if batch_no:
        from gcma_kiosco.api.stock_utils import get_stock_lote_detallado
        detailed_stock = get_stock_lote_detallado(item_code, batch_no)
        if detailed_stock:
             return detailed_stock[0]["warehouse"]

    return preferred


def _build_consumption_plan(wo_doc, lotes_usados_map, extras_map):
    item_names, name_to_code = _resolve_item_key_maps(wo_doc)
    plan = []
    desviaciones = []
    alerta = False

    for row in wo_doc.required_items:
        item_code = row.item_code
        item_name = item_names[item_code]
        extra_qty = flt(extras_map.get(item_code, extras_map.get(item_name, 0)))
        qty_teorica = flt(row.required_qty) - flt(row.consumed_qty)

        if qty_teorica > 0 and extra_qty > qty_teorica:
            frappe.local.response["http_status_code"] = 422
            return None, {
                "success": False,
                "error_code": "EXTRA_QTY_ABSURD",
                "item_name": item_name,
                "qty_teorica": round(qty_teorica, 2),
                "qty_extra": round(extra_qty, 2),
                "message_fr": (
                    f"Saisie incohérente pour '{item_name}' : extra {round(extra_qty, 2)} "
                    f"> quantité théorique {round(qty_teorica, 2)}. Vérifiez la valeur saisie."
                ),
            }

        has_batch_no = cint(frappe.db.get_value("Item", item_code, "has_batch_no"))
        batch_no = lotes_usados_map.get(item_code) or lotes_usados_map.get(item_name)

        if has_batch_no and not batch_no:
            frappe.local.response["http_status_code"] = 400
            return None, {
                "success": False,
                "error_code": "MISSING_BATCH",
                "item_name": item_name,
                "message_fr": f"Lot manquant pour '{item_name}'. Refaire le scan avant de clôturer.",
            }

        if not has_batch_no:
            batch_no = None

        qty_real = round(qty_teorica + extra_qty, 2)
        diferencia_kg = round(extra_qty, 2)
        diferencia_pct = round((extra_qty / qty_teorica) * 100, 1) if qty_teorica else 0

        if abs(diferencia_kg) > 0.01:
            desviaciones.append({
                "item_name": item_name,
                "qty_teorica": round(qty_teorica, 2),
                "qty_real": qty_real,
                "diferencia_kg": diferencia_kg,
                "diferencia_pct": diferencia_pct,
            })
            if abs(diferencia_pct) > 10:
                alerta = True

        plan.append({
            "item_code": item_code,
            "item_name": item_name,
            "qty_teorica": round(qty_teorica, 2),
            "qty_real": qty_real,
            "uom": row.stock_uom,
            "has_batch_no": has_batch_no,
            "batch_no": batch_no,
            "preferred_source_warehouse": row.source_warehouse,
        })

    return {
        "items": plan,
        "desviaciones": desviaciones,
        "alerta": alerta,
    }, None


def _build_transfer_entry(wo_doc, consumption_plan):
    company_abbr = frappe.db.get_value("Company", wo_doc.company, "abbr")
    stock_entry = frappe.get_doc(
        erpnext_make_stock_entry(wo_doc.name, "Material Transfer for Manufacture", qty=flt(wo_doc.qty) - flt(wo_doc.produced_qty))
    )

    plan_map = {row["item_code"]: row for row in consumption_plan["items"]}
    filtered_items = []
    for row in stock_entry.items:
        if row.item_code not in plan_map or row.is_finished_item:
            continue

        plan_row = plan_map[row.item_code]
        row.qty = plan_row["qty_real"]
        row.transfer_qty = plan_row["qty_real"]
        row.t_warehouse = wo_doc.wip_warehouse
        row.s_warehouse = _resolve_source_warehouse(
            row.item_code,
            company_abbr,
            plan_row["preferred_source_warehouse"],
            plan_row["batch_no"],
        )
        row.batch_no = None
        row.serial_no = None
        filtered_items.append(row)

    stock_entry.set("items", filtered_items)
    stock_entry.from_warehouse = None
    stock_entry.to_warehouse = wo_doc.wip_warehouse
    stock_entry.fg_completed_qty = 0
    stock_entry.purpose = "Material Transfer for Manufacture"
    stock_entry.stock_entry_type = "Material Transfer for Manufacture"
    _attach_manual_batch_bundles(stock_entry, consumption_plan)
    return stock_entry


def _build_manufacture_entry(wo_doc, consumption_plan):
    stock_entry = frappe.get_doc(
        erpnext_make_stock_entry(wo_doc.name, "Manufacture", qty=flt(wo_doc.qty) - flt(wo_doc.produced_qty), target_warehouse=wo_doc.fg_warehouse)
    )
    plan_map = {row["item_code"]: row for row in consumption_plan["items"]}

    for row in stock_entry.items:
        if row.is_finished_item:
            row.t_warehouse = wo_doc.fg_warehouse
            continue

        if row.item_code not in plan_map:
            continue

        plan_row = plan_map[row.item_code]
        row.qty = plan_row["qty_real"]
        row.transfer_qty = plan_row["qty_real"]
        row.s_warehouse = wo_doc.wip_warehouse
        row.batch_no = None
        row.serial_no = None

    stock_entry.from_warehouse = wo_doc.wip_warehouse
    stock_entry.to_warehouse = wo_doc.fg_warehouse
    stock_entry.purpose = "Manufacture"
    stock_entry.stock_entry_type = "Manufacture"
    _attach_manual_batch_bundles(stock_entry, consumption_plan)
    return stock_entry


def _attach_manual_batch_bundles(stock_entry, consumption_plan):
    plan_map = {row["item_code"]: row for row in consumption_plan["items"]}
    posting_datetime = get_datetime(f"{stock_entry.posting_date} {stock_entry.posting_time}")

    for row in stock_entry.items:
        plan_row = plan_map.get(row.item_code)
        if not plan_row or not plan_row["has_batch_no"]:
            continue

        bundle_doc = SerialBatchCreation(
            {
                "item_code": row.item_code,
                "warehouse": row.s_warehouse,
                "posting_datetime": posting_datetime,
                "voucher_type": stock_entry.doctype,
                "voucher_detail_no": row.name,
                "qty": flt(row.transfer_qty) * -1,
                "type_of_transaction": "Outward",
                "company": stock_entry.company,
                "do_not_submit": True,
            }
        ).make_serial_and_batch_bundle(
            batch_nos={plan_row["batch_no"]: abs(flt(row.transfer_qty))}
        )

        row.serial_and_batch_bundle = bundle_doc.name
        row.use_serial_batch_fields = 0


def _insert_kiosco_comment(work_order, consumption_plan, transfer_name, manufacture_name):
    resumen_texto = (
        f"Consommation enregistrée via Kiosco — {len(consumption_plan['items'])} matériaux\n"
        f"Transfert WIP: {transfer_name}\n"
        f"Manufacture: {manufacture_name}\n"
    )
    for c in consumption_plan["items"]:
        resumen_texto += f"  • {c['item_name']}: {c['qty_real']} {c['uom']}"
        if c["batch_no"]:
            resumen_texto += f" (lot: {c['batch_no']})"
        if c['qty_real'] != c['qty_teorica']:
            diff = round(c['qty_real'] - c['qty_teorica'], 2)
            resumen_texto += f" (théorique: {c['qty_teorica']}, écart: +{diff})"
        resumen_texto += "\n"

    frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Info",
        "reference_doctype": "Work Order",
        "reference_name": work_order,
        "content": resumen_texto,
    }).insert(ignore_permissions=True)


def _insert_and_submit_stock_entry(stock_entry):
    stock_entry.insert(ignore_permissions=True)
    stock_entry.reload()

    needs_cleanup = False
    for row in stock_entry.items:
        if row.serial_and_batch_bundle and (row.batch_no or row.serial_no):
            row.batch_no = None
            row.serial_no = None
            needs_cleanup = True

    if needs_cleanup:
        stock_entry.save(ignore_permissions=True)

    stock_entry.submit()
    return stock_entry


@contextmanager
def _run_as_system_user():
    original_user = frappe.session.user if getattr(frappe, "session", None) else None

    if original_user and original_user != "Administrator":
        frappe.set_user("Administrator")

    try:
        yield
    finally:
        if original_user and frappe.session.user != original_user:
            frappe.set_user(original_user)


@frappe.whitelist()
def reportar_consumo(
    work_order: str = None,
    lotes_usados=None,
    consumos_extra=None,
    extras=None,
):
    """Cierra contablemente la producción creando los Stock Entry nativos.

    Soporta el contrato nuevo:
      - lotes_usados: dict item_code/item_name -> batch_no
      - consumos_extra: dict item_code/item_name -> qty extra

    y mantiene compatibilidad con el frontend anterior:
      - extras: JSON string de [{item_name, qty_extra}]
    """
    profile_error = _require_kiosk_profile("production")
    if profile_error:
        return profile_error

    if not work_order:
        frappe.local.response["http_status_code"] = 400
        return {
            "success": False,
            "error_code": "MISSING_PARAMS",
            "message_fr": "Paramètre 'work_order' obligatoire.",
        }

    try:
        wo_doc = frappe.get_doc("Work Order", work_order)
    except frappe.DoesNotExistError:
        frappe.local.response["http_status_code"] = 404
        return {
            "success": False,
            "error_code": "WO_NOT_FOUND",
            "message_fr": "Ordre de fabrication introuvable ou non validé.",
        }

    if wo_doc.docstatus != 1 or wo_doc.status not in ("Not Started", "In Process"):
        return {
            "success": False,
            "error_code": "WO_NOT_IN_PROCESS",
            "message_fr": "Cet ordre n'est pas en cours. Vérifiez avec le superviseur.",
        }

    if not wo_doc.fg_warehouse or "Cuarentena PT" not in wo_doc.fg_warehouse:
        frappe.local.response["http_status_code"] = 422
        return {
            "success": False,
            "error_code": "INVALID_TARGET_WAREHOUSE",
            "message_fr": "L'entrepôt de produit fini doit être la quarantaine PT.",
        }

    lotes_usados_map = _normalize_lotes_usados(lotes_usados)
    extras_map = _normalize_consumos_extra(consumos_extra, extras)

    consumption_plan, error_response = _build_consumption_plan(wo_doc, lotes_usados_map, extras_map)
    if error_response:
        return error_response

    try:
        with _run_as_system_user():
            transfer_entry = _build_transfer_entry(wo_doc, consumption_plan)
            transfer_entry = _insert_and_submit_stock_entry(transfer_entry)

            manufacture_entry = _build_manufacture_entry(wo_doc, consumption_plan)
            manufacture_entry = _insert_and_submit_stock_entry(manufacture_entry)

            _insert_kiosco_comment(work_order, consumption_plan, transfer_entry.name, manufacture_entry.name)
        frappe.db.commit()

        total_teo = sum(row["qty_teorica"] for row in consumption_plan["items"])
        total_extra = sum(row["diferencia_kg"] for row in consumption_plan["desviaciones"])
        merma_total = round((total_extra / total_teo) * 100, 1) if total_teo else 0

        result = {
            "success": True,
            "work_order": work_order,
            "stock_entry_transfer": transfer_entry.name,
            "stock_entry_manufacture": manufacture_entry.name,
            "resumen": {
                "qty_producida": flt(wo_doc.qty) - flt(wo_doc.produced_qty),
                "desviaciones": consumption_plan["desviaciones"],
                "merma_total_pct": merma_total,
                "estado": "Manufacturé",
            },
            "message_fr": "Consommation enregistrée et lot fabriqué avec succès.",
        }

        if consumption_plan["alerta"]:
            result["alerta"] = True
            result["alerta_nivel"] = "WARNING"
            items_alerta = [d["item_name"] for d in consumption_plan["desviaciones"] if abs(d["diferencia_pct"]) > 10]
            result["message_fr"] = (
                f"Consommation enregistrée et lot fabriqué. ⚠ Écart supérieur à 10% sur {', '.join(items_alerta)}."
            )

        return result

    except frappe.ValidationError as err:
        frappe.db.rollback()
        frappe.local.response["http_status_code"] = 422
        return {
            "success": False,
            "error_code": "ERP_VALIDATION_ERROR",
            "message_fr": f"Transaction refusée par ERPNext : {frappe.safe_decode(str(err))}",
        }
    except Exception:
        frappe.db.rollback()
        frappe.log_error(
            title=f"Erreur reportar_consumo — WO {work_order}",
            message=frappe.get_traceback(),
        )
        frappe.local.response["http_status_code"] = 500
        return {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message_fr": "Erreur interne lors de la clôture de production. Contactez l'administrateur.",
        }


# ═══════════════════════════════════════════════════════════════════════════
# EP5 — INFO LOTE (consulta rápida)
# ═══════════════════════════════════════════════════════════════════════════


@frappe.whitelist()
def info_lote(batch_no: str = None, item_code: str = None):
    """Consulta rápida de lote para planta/laboratorio.

    Devuelve metadatos del lote y stock agregado por almacén.
    """
    profile_error = _require_kiosk_profile("production", "quality")
    if profile_error:
        return profile_error

    if not batch_no:
        frappe.local.response["http_status_code"] = 400
        return {
            "success": False,
            "error_code": "MISSING_PARAMS",
            "message_fr": "Paramètre 'batch_no' obligatoire.",
        }

    batch_no = str(batch_no).strip()
    item_code = str(item_code).strip() if item_code else None

    try:
        batch_data = frappe.db.get_value(
            "Batch",
            batch_no,
            ["batch_id", "item", "expiry_date"],
            as_dict=True,
        )

        if not batch_data:
            frappe.local.response["http_status_code"] = 404
            return {
                "success": False,
                "error_code": "BATCH_NOT_FOUND",
                "message_fr": f"Lot '{batch_no}' introuvable.",
            }

        if item_code and batch_data.item != item_code:
            frappe.local.response["http_status_code"] = 422
            return {
                "success": False,
                "error_code": "BATCH_ITEM_MISMATCH",
                "message_fr": "Le lot indique ne correspond pas a l'article fourni.",
            }

        resolved_item_code = batch_data.item
        item_name = frappe.db.get_value("Item", resolved_item_code, "item_name") or resolved_item_code
        expiry_date = str(batch_data.expiry_date) if batch_data.expiry_date else None
        dias_restantes = date_diff(batch_data.expiry_date, today()) if batch_data.expiry_date else None

        from gcma_kiosco.api.stock_utils import get_stock_lote_detallado
        stock_rows = get_stock_lote_detallado(resolved_item_code, batch_no)
        total_qty = round(sum(flt(row["qty"]) for row in stock_rows), 2)

        return {
            "success": True,
            "lote": {
                "batch_no": batch_no,
                "item_code": resolved_item_code,
                "item_name": item_name,
                "expiry_date": expiry_date,
                "dias_restantes": dias_restantes,
            },
            "stock_por_almacen": stock_rows,
            "total_qty": total_qty,
            "message_fr": "Informations du lot chargees.",
        }

    except Exception:
        frappe.log_error(
            title=f"Erreur info_lote — {batch_no}",
            message=frappe.get_traceback(),
        )
        frappe.local.response["http_status_code"] = 500
        return {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message_fr": "Erreur interne lors de la consultation du lot.",
        }
