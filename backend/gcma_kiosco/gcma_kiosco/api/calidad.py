"""
GCMA Kiosco — Endpoints REST para el laboratorio / control de calidad.

Rutas base: /api/method/gcma_kiosco.api.calidad.<nombre_metodo>

Objetivo del bloque:
  - Consultar los lotes de PT presentes en cuarentena
  - Registrar inspecciones de calidad de forma nativa en ERPNext v16
  - Liberar automáticamente el lote aprobado hacia almacén vendible
"""

from contextlib import contextmanager

import frappe
from frappe.utils import flt, get_datetime, nowtime, today
from gcma_kiosco.api.kiosco import _require_kiosk_profile


COMPANY = "Peintures du Maroc SARL"
ABBR = "PDM"
WH_QA_PT = f"Cuarentena PT - {ABBR}"
WH_FG = f"Producto Terminado - {ABBR}"
LAB_PARAMETER_GROUP = "Laboratoire PT"


def _sum_batch_movements(rows):
    total = 0.0
    for row in rows:
        qty = flt(row.get("qty") or row.get("actual_qty"))
        if row.get("is_outward"):
            total -= abs(qty)
        else:
            total += qty
    return total


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


def _normalize_result(aprobada=None, resultado=None):
    if isinstance(aprobada, str):
        aprobada = aprobada.strip().lower() in {"1", "true", "yes", "oui", "approuve", "approved"}
    elif aprobada is not None:
        aprobada = bool(aprobada)

    if aprobada is not None:
        return aprobada

    result_text = (resultado or "Approved").strip().lower()
    if result_text in {"approved", "approuve", "approuvé", "ok", "accepted", "accepte", "accepté"}:
        return True
    if result_text in {"rejected", "rejete", "rejeté", "nok", "refuse", "refusé"}:
        return False

    frappe.throw("Résultat qualité invalide.")


def _normalize_parametros(parametros):
    payload = _parse_json_param(parametros, {})
    rows = []

    if isinstance(payload, dict):
        for parameter, value in payload.items():
            if parameter is None:
                continue
            rows.append(
                {
                    "parameter": str(parameter).strip(),
                    "value": value,
                    "numeric": isinstance(value, (int, float)),
                }
            )
    elif isinstance(payload, list):
        for row in payload:
            parameter = (row.get("parameter") or row.get("specification") or row.get("name") or "").strip()
            value = row.get("value", row.get("reading_value"))
            numeric = row.get("numeric")
            if numeric is None:
                numeric = isinstance(value, (int, float))
            if parameter:
                rows.append(
                    {
                        "parameter": parameter,
                        "value": value,
                        "numeric": bool(numeric),
                    }
                )

    return [row for row in rows if row["parameter"]]


def _ensure_quality_parameter_group(group_name: str = LAB_PARAMETER_GROUP):
    existing = frappe.db.get_value(
        "Quality Inspection Parameter Group",
        {"group_name": group_name},
        "name",
    )
    if existing:
        return existing

    doc = frappe.new_doc("Quality Inspection Parameter Group")
    doc.group_name = group_name
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_quality_parameter(parameter_name: str, group_name: str = LAB_PARAMETER_GROUP):
    existing = frappe.db.get_value(
        "Quality Inspection Parameter",
        {"parameter": parameter_name},
        "name",
    )
    if existing:
        return existing

    group = _ensure_quality_parameter_group(group_name)
    doc = frappe.new_doc("Quality Inspection Parameter")
    doc.parameter = parameter_name
    doc.parameter_group = group
    doc.insert(ignore_permissions=True)
    return doc.name


def _get_quarantine_balance(item_code: str, batch_no: str, warehouse: str = WH_QA_PT):
    bundle_rows = frappe.db.sql(
        """
        SELECT
            sbe.qty,
            sbe.is_outward
        FROM `tabSerial and Batch Entry` sbe
        INNER JOIN `tabSerial and Batch Bundle` bundle ON bundle.name = sbe.parent
        WHERE bundle.company = %s
          AND sbe.warehouse = %s
          AND sbe.item_code = %s
          AND sbe.batch_no = %s
          AND sbe.is_cancelled = 0
        """,
        (COMPANY, warehouse, item_code, batch_no),
        as_dict=True,
    )

    legacy_rows = frappe.db.sql(
        """
        SELECT actual_qty
        FROM `tabStock Ledger Entry`
        WHERE company = %s
          AND warehouse = %s
          AND item_code = %s
          AND batch_no = %s
          AND is_cancelled = 0
          AND IFNULL(serial_and_batch_bundle, '') = ''
        """,
        (COMPANY, warehouse, item_code, batch_no),
        as_dict=True,
    )

    return _sum_batch_movements(bundle_rows) + sum(flt(row.actual_qty) for row in legacy_rows)


def _get_quarantine_lots(warehouse: str):
    lots_map = {}

    bundle_rows = frappe.db.sql(
        """
        SELECT
            sbe.item_code,
            item.item_name,
            sbe.batch_no,
            item.stock_uom AS uom,
            sbe.qty,
            sbe.is_outward,
            sbe.posting_datetime
        FROM `tabSerial and Batch Entry` sbe
        INNER JOIN `tabSerial and Batch Bundle` bundle ON bundle.name = sbe.parent
        INNER JOIN `tabItem` item ON item.name = sbe.item_code
        WHERE bundle.company = %s
          AND sbe.warehouse = %s
          AND sbe.is_cancelled = 0
          AND IFNULL(sbe.batch_no, '') != ''
        ORDER BY sbe.posting_datetime ASC, sbe.creation ASC
        """,
        (COMPANY, warehouse),
        as_dict=True,
    )

    legacy_rows = frappe.db.sql(
        """
        SELECT
            sle.item_code,
            item.item_name,
            sle.batch_no,
            item.stock_uom AS uom,
            sle.actual_qty,
            sle.posting_date
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabItem` item ON item.name = sle.item_code
        WHERE sle.company = %s
          AND sle.warehouse = %s
          AND sle.is_cancelled = 0
          AND IFNULL(sle.batch_no, '') != ''
          AND IFNULL(sle.serial_and_batch_bundle, '') = ''
        ORDER BY sle.posting_date ASC, sle.creation ASC
        """,
        (COMPANY, warehouse),
        as_dict=True,
    )

    for row in bundle_rows:
        key = (row.item_code, row.batch_no)
        lot = lots_map.setdefault(
            key,
            {
                "item_code": row.item_code,
                "item_name": row.item_name,
                "batch_no": row.batch_no,
                "uom": row.uom,
                "qty": 0.0,
                "fecha_fabricacion": None,
            },
        )
        qty = flt(row.qty)
        if row.is_outward:
            lot["qty"] -= abs(qty)
        else:
            lot["qty"] += qty
            posting_dt = row.posting_datetime
            posting_date = get_datetime(posting_dt).date().isoformat() if posting_dt else None
            if posting_date and (not lot["fecha_fabricacion"] or posting_date < lot["fecha_fabricacion"]):
                lot["fecha_fabricacion"] = posting_date

    for row in legacy_rows:
        key = (row.item_code, row.batch_no)
        lot = lots_map.setdefault(
            key,
            {
                "item_code": row.item_code,
                "item_name": row.item_name,
                "batch_no": row.batch_no,
                "uom": row.uom,
                "qty": 0.0,
                "fecha_fabricacion": None,
            },
        )
        lot["qty"] += flt(row.actual_qty)
        posting_date = row.posting_date.isoformat() if row.posting_date else None
        if flt(row.actual_qty) > 0 and posting_date and (not lot["fecha_fabricacion"] or posting_date < lot["fecha_fabricacion"]):
            lot["fecha_fabricacion"] = posting_date

    lotes = []
    for lot in lots_map.values():
        if flt(lot["qty"]) > 0.000001:
            lot["qty"] = round(flt(lot["qty"]), 2)
            lotes.append(lot)

    lotes.sort(key=lambda row: (row.get("fecha_fabricacion") or "", row["batch_no"]))
    return lotes


def _get_quarantine_reference_stock_entry(item_code: str, batch_no: str, warehouse: str = WH_QA_PT):
        bundle_row = frappe.db.sql(
                """
                SELECT sbe.voucher_no
                FROM `tabSerial and Batch Entry` sbe
                INNER JOIN `tabSerial and Batch Bundle` bundle ON bundle.name = sbe.parent
                WHERE bundle.company = %s
                    AND sbe.warehouse = %s
                    AND sbe.item_code = %s
                    AND sbe.batch_no = %s
                    AND sbe.is_cancelled = 0
                    AND IFNULL(sbe.is_outward, 0) = 0
                    AND sbe.voucher_type = 'Stock Entry'
                ORDER BY sbe.posting_datetime DESC, sbe.creation DESC
                LIMIT 1
                """,
                (COMPANY, warehouse, item_code, batch_no),
                as_dict=True,
        )
        if bundle_row:
                return bundle_row[0].voucher_no

        legacy_row = frappe.db.sql(
                """
                SELECT voucher_no
                FROM `tabStock Ledger Entry`
                WHERE company = %s
                    AND warehouse = %s
                    AND item_code = %s
                    AND batch_no = %s
                    AND is_cancelled = 0
                    AND IFNULL(serial_and_batch_bundle, '') = ''
                    AND actual_qty > 0
                    AND voucher_type = 'Stock Entry'
                ORDER BY posting_date DESC, creation DESC
                LIMIT 1
                """,
                (COMPANY, warehouse, item_code, batch_no),
                as_dict=True,
        )
        return legacy_row[0].voucher_no if legacy_row else None


def _build_quality_readings(parameters, approved: bool):
    reading_status = "Accepted" if approved else "Rejected"
    rows = []

    for parameter in parameters:
        parameter_name = parameter["parameter"]
        value = parameter.get("value")
        numeric = bool(parameter.get("numeric"))
        specification = _ensure_quality_parameter(parameter_name)

        row = {
            "specification": specification,
            "manual_inspection": 1,
            "numeric": 1 if numeric else 0,
            "status": reading_status,
        }

        if value is not None:
            if numeric:
                row["reading_1"] = str(value)
            else:
                row["reading_value"] = str(value)

        rows.append(row)

    return rows


def _build_quality_remarks(parameters, approved: bool, reference_name: str | None = None, remarks: str | None = None):
    lines = ["Inspection laboratoire via Kiosco Qualité"]
    lines.append(f"Résultat: {'Approuvé' if approved else 'Rejeté'}")

    if reference_name:
        lines.append(f"Document de référence: {reference_name}")

    if remarks:
        lines.append(f"Remarques: {remarks}")

    if parameters:
        lines.append("Mesures enregistrées:")
        for row in parameters:
            lines.append(f"- {row['parameter']}: {row.get('value')}")

    return "\n".join(lines)


def _build_release_stock_entry(item_code: str, batch_no: str, qty: float):
    stock_entry = frappe.new_doc("Stock Entry")
    stock_entry.stock_entry_type = "Material Transfer"
    stock_entry.purpose = "Material Transfer"
    stock_entry.company = COMPANY
    stock_entry.posting_date = today()
    stock_entry.set_posting_time = 1
    stock_entry.posting_time = nowtime()
    stock_entry.remarks = f"Libération QC du lot {batch_no}"

    stock_entry.append(
        "items",
        {
            "item_code": item_code,
            "qty": qty,
            "s_warehouse": WH_QA_PT,
            "t_warehouse": WH_FG,
            "batch_no": batch_no,
            "use_serial_batch_fields": 1,
        },
    )

    return stock_entry


def _build_quality_inspection(item_code: str, batch_no: str, qty: float, parameters, approved: bool, remarks: str | None = None, reference_name: str | None = None):
    qi = frappe.new_doc("Quality Inspection")
    qi.inspection_type = "Outgoing"
    qi.item_code = item_code
    qi.batch_no = batch_no
    qi.sample_size = qty
    qi.report_date = today()
    qi.company = COMPANY
    qi.manual_inspection = 1
    qi.inspected_by = frappe.session.user
    qi.verified_by = frappe.session.user
    qi.status = "Accepted" if approved else "Rejected"

    if reference_name:
        qi.reference_type = "Stock Entry"
        qi.reference_name = reference_name

    for row in _build_quality_readings(parameters, approved):
        qi.append("readings", row)

    qi.remarks = _build_quality_remarks(parameters, approved, reference_name, remarks)
    return qi


@frappe.whitelist()
def get_lotes_cuarentena(warehouse: str = None):
    """Devuelve los lotes de PT actualmente presentes en cuarentena."""
    profile_error = _require_kiosk_profile("quality")
    if profile_error:
        return profile_error

    target_warehouse = warehouse or WH_QA_PT

    try:
        lotes = _get_quarantine_lots(target_warehouse)

        return {
            "success": True,
            "warehouse": target_warehouse,
            "lotes": lotes,
            "total": len(lotes),
        }

    except Exception:
        frappe.log_error(
            title="Erreur get_lotes_cuarentena",
            message=frappe.get_traceback(),
        )
        frappe.local.response["http_status_code"] = 500
        return {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message_fr": "Erreur interne lors de la consultation des lots en quarantaine.",
        }


@frappe.whitelist()
def aprobar_calidad(item_code: str = None, batch_no: str = None, qty: str | float = None, parametros=None, aprobada=None, resultado: str = None, remarks: str = None):
    """Registra una inspección de laboratorio y libera el lote si está aprobado."""
    profile_error = _require_kiosk_profile("quality")
    if profile_error:
        return profile_error

    if not item_code or not batch_no or qty is None:
        frappe.local.response["http_status_code"] = 400
        return {
            "success": False,
            "error_code": "MISSING_PARAMS",
            "message_fr": "Paramètres obligatoires: item_code, batch_no et qty.",
        }

    qty = flt(qty)
    if qty <= 0:
        frappe.local.response["http_status_code"] = 422
        return {
            "success": False,
            "error_code": "INVALID_QTY",
            "message_fr": "La quantité inspectée doit être supérieure à zéro.",
        }

    parameters = _normalize_parametros(parametros)
    if not parameters:
        frappe.local.response["http_status_code"] = 400
        return {
            "success": False,
            "error_code": "MISSING_PARAMETERS",
            "message_fr": "Aucun paramètre laboratoire reçu. Veuillez saisir au moins une mesure.",
        }

    try:
        approved = _normalize_result(aprobada, resultado)
    except Exception:
        frappe.local.response["http_status_code"] = 422
        return {
            "success": False,
            "error_code": "INVALID_RESULT",
            "message_fr": "Résultat qualité invalide. Utilisez Approved / Rejected.",
        }

    if not frappe.db.exists("Item", item_code):
        frappe.local.response["http_status_code"] = 404
        return {
            "success": False,
            "error_code": "ITEM_NOT_FOUND",
            "message_fr": "Article introuvable.",
        }

    if not frappe.db.exists("Batch", batch_no):
        frappe.local.response["http_status_code"] = 404
        return {
            "success": False,
            "error_code": "BATCH_NOT_FOUND",
            "message_fr": "Lot introuvable.",
        }

    batch_item = frappe.db.get_value("Batch", batch_no, "item")
    if batch_item != item_code:
        frappe.local.response["http_status_code"] = 422
        return {
            "success": False,
            "error_code": "BATCH_ITEM_MISMATCH",
            "message_fr": "Le lot indiqué ne correspond pas à l'article demandé.",
        }

    available_qty = _get_quarantine_balance(item_code, batch_no)
    if available_qty <= 0:
        frappe.local.response["http_status_code"] = 422
        return {
            "success": False,
            "error_code": "NO_STOCK_IN_QUARANTINE",
            "message_fr": "Aucun stock disponible de ce lot en quarantaine.",
        }

    if qty > available_qty:
        frappe.local.response["http_status_code"] = 422
        return {
            "success": False,
            "error_code": "QTY_EXCEEDS_AVAILABLE",
            "message_fr": f"Quantité demandée supérieure au stock en quarantaine ({round(available_qty, 2)} disponible).",
        }

    source_reference_name = _get_quarantine_reference_stock_entry(item_code, batch_no)
    if not source_reference_name:
        frappe.local.response["http_status_code"] = 422
        return {
            "success": False,
            "error_code": "MISSING_REFERENCE_STOCK_ENTRY",
            "message_fr": "Aucun document stock d'origine trouvé pour ce lot en quarantaine.",
        }

    try:
        with _run_as_system_user():
            transfer_entry = None
            if approved:
                transfer_entry = _build_release_stock_entry(item_code, batch_no, qty)
                transfer_entry.insert(ignore_permissions=True)
                transfer_entry.submit()

            inspection = _build_quality_inspection(
                item_code=item_code,
                batch_no=batch_no,
                qty=qty,
                parameters=parameters,
                approved=approved,
                remarks=remarks,
                reference_name=transfer_entry.name if transfer_entry else source_reference_name,
            )
            inspection.insert(ignore_permissions=True)
            inspection.submit()

        frappe.db.commit()

        response = {
            "success": True,
            "quality_inspection": inspection.name,
            "item_code": item_code,
            "batch_no": batch_no,
            "qty": qty,
            "quality_status": inspection.status,
            "message_fr": "Inspection qualité enregistrée.",
        }

        if transfer_entry:
            response["stock_entry"] = transfer_entry.name
            response["message_fr"] = "Inspection qualité approuvée. Lot libéré vers le stock vendable."
        else:
            response["message_fr"] = "Inspection qualité enregistrée. Lot maintenu en quarantaine."

        return response

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
            title=f"Erreur aprobar_calidad — {item_code} / {batch_no}",
            message=frappe.get_traceback(),
        )
        frappe.local.response["http_status_code"] = 500
        return {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message_fr": "Erreur interne lors de la validation qualité. Contactez l'administrateur.",
        }