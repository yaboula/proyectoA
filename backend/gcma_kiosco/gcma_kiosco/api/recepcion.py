"""
GCMA Kiosco — Endpoints de recepcion de materias primas.

Rutas base: /api/method/gcma_kiosco.api.recepcion.<nombre_metodo>
"""

from __future__ import annotations

import ast
import json
from collections import OrderedDict
from contextlib import contextmanager

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, flt, getdate, today

from gcma_kiosco.api.kiosco import _require_kiosk_profile
from gcma_kiosco.api.stock_utils import get_stock_lote_almacen


@contextmanager
def _run_as_system_user():
    original_user = frappe.session.user if getattr(frappe, "session", None) else None
    original_sid = frappe.session.sid if getattr(frappe, "session", None) else None
    original_cache = getattr(frappe.local, "cache", None)
    original_form_dict = getattr(frappe.local, "form_dict", None)
    original_jenv = getattr(frappe.local, "jenv", None)
    original_session_data = frappe._dict(getattr(frappe.local.session, "data", {}) or {}) if getattr(frappe.local, "session", None) else frappe._dict()
    original_role_permissions = getattr(frappe.local, "role_permissions", None)
    original_new_doc_templates = getattr(frappe.local, "new_doc_templates", None)
    original_user_perms = getattr(frappe.local, "user_perms", None)
    previous_ignore_permissions = getattr(frappe.flags, "ignore_permissions", False)
    previous_ignore_links = getattr(frappe.flags, "ignore_links", False)
    previous_ignore_validate = getattr(frappe.flags, "ignore_validate", False)

    elevated = bool(original_user and original_user != "Administrator")

    if elevated:
        frappe.session.user = "Administrator"
        frappe.local.session.user = "Administrator"
        frappe.session.sid = original_sid
        frappe.local.cache = {}
        frappe.local.form_dict = frappe._dict()
        frappe.local.jenv = None
        frappe.local.session.data = frappe._dict()
        frappe.local.role_permissions = {}
        frappe.local.new_doc_templates = {}
        frappe.local.user_perms = None

    frappe.flags.ignore_permissions = True
    frappe.flags.ignore_links = True
    frappe.flags.ignore_validate = previous_ignore_validate

    try:
        yield
    finally:
        if elevated:
            frappe.session.user = original_user
            frappe.local.session.user = original_user
            frappe.session.sid = original_sid
            frappe.local.cache = original_cache if original_cache is not None else {}
            frappe.local.form_dict = original_form_dict if original_form_dict is not None else frappe._dict()
            frappe.local.jenv = original_jenv
            frappe.local.session.data = original_session_data
            frappe.local.role_permissions = original_role_permissions if original_role_permissions is not None else {}
            frappe.local.new_doc_templates = original_new_doc_templates if original_new_doc_templates is not None else {}
            frappe.local.user_perms = original_user_perms

        frappe.flags.ignore_permissions = previous_ignore_permissions
        frappe.flags.ignore_links = previous_ignore_links
        frappe.flags.ignore_validate = previous_ignore_validate


def _get_quarantine_mp_warehouse(company: str) -> str:
    abbr = frappe.db.get_value("Company", company, "abbr")
    if not abbr:
        raise frappe.ValidationError(_("Company without abbreviation"))
    return f"Cuarentena MP - {abbr}"


def _get_approved_mp_warehouse(company: str) -> str:
    abbr = frappe.db.get_value("Company", company, "abbr")
    if not abbr:
        raise frappe.ValidationError(_("Company without abbreviation"))
    return f"Materia Prima Aprobada - {abbr}"


def _parse_items_recibidos(items_recibidos) -> list[dict]:
    payload = items_recibidos

    if isinstance(payload, str):
        payload = payload.strip()
        if not payload:
            return []
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            parsed = None
            try:
                parsed = frappe.parse_json(payload)
            except Exception:
                parsed = None

            if parsed is None:
                try:
                    parsed = ast.literal_eval(payload)
                except Exception as exc:
                    raise frappe.ValidationError("INVALID_ITEMS_JSON") from exc

            payload = parsed

    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            try:
                payload = ast.literal_eval(payload)
            except Exception:
                pass

    if isinstance(payload, dict):
        payload = [payload]

    if not isinstance(payload, list):
        raise frappe.ValidationError("INVALID_ITEMS_TYPE")

    normalized = []
    for row in payload:
        if not isinstance(row, dict):
            raise frappe.ValidationError("INVALID_ITEM_ROW")

        item_code = str(row.get("item_code") or "").strip()
        qty = flt(row.get("qty"))
        supplier_batch = str(row.get("supplier_batch") or "").strip()
        expiry_date = row.get("expiry_date")

        if not item_code:
            raise frappe.ValidationError("MISSING_ITEM_CODE")
        if qty <= 0:
            raise frappe.ValidationError("INVALID_QTY")

        normalized_row = {
            "item_code": item_code,
            "qty": qty,
            "supplier_batch": supplier_batch or None,
            "expiry_date": str(getdate(expiry_date)) if expiry_date else None,
        }
        normalized.append(normalized_row)

    return normalized


def _parse_conteo_fisico(conteo) -> list[dict]:
    payload = conteo

    if isinstance(payload, str):
        payload = payload.strip()
        if not payload:
            return []
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            parsed = None
            try:
                parsed = frappe.parse_json(payload)
            except Exception:
                parsed = None

            if parsed is None:
                try:
                    parsed = ast.literal_eval(payload)
                except Exception as exc:
                    raise frappe.ValidationError("INVALID_CONTEO_JSON") from exc

            payload = parsed

    if isinstance(payload, dict):
        payload = [payload]

    if not isinstance(payload, list):
        raise frappe.ValidationError("INVALID_CONTEO_TYPE")

    aggregated: OrderedDict[tuple[str, str], dict] = OrderedDict()
    for row in payload:
        if not isinstance(row, dict):
            raise frappe.ValidationError("INVALID_CONTEO_ROW")

        item_code = str(row.get("item_code") or "").strip()
        batch_no = str(row.get("batch_no") or "").strip()
        qty_fisica = flt(row.get("qty_fisica"))

        if not item_code:
            raise frappe.ValidationError("MISSING_ITEM_CODE")
        if not batch_no:
            raise frappe.ValidationError("MISSING_BATCH_NO")
        if qty_fisica <= 0:
            raise frappe.ValidationError("INVALID_QTY")

        key = (item_code, batch_no)
        if key not in aggregated:
            aggregated[key] = {
                "item_code": item_code,
                "batch_no": batch_no,
                "qty_fisica": 0.0,
            }
        aggregated[key]["qty_fisica"] += qty_fisica

    return list(aggregated.values())


def _get_company_from_warehouse(warehouse: str) -> str | None:
    if not warehouse:
        return None
    return frappe.db.get_value("Warehouse", warehouse, "company")


def _get_pending_po_items(po_names: list[str], warehouse: str | None = None) -> dict[str, list[dict]]:
    if not po_names:
        return {}

    rows = frappe.get_all(
        "Purchase Order Item",
        filters={"parent": ["in", po_names], "parenttype": "Purchase Order"},
        fields=[
            "name",
            "parent",
            "item_code",
            "item_name",
            "qty",
            "received_qty",
            "uom",
            "stock_uom",
            "conversion_factor",
            "warehouse",
            "schedule_date",
        ],
        order_by="idx asc",
    )

    item_codes = sorted({row.item_code for row in rows if row.item_code})
    item_meta = {
        row.name: row
        for row in frappe.get_all(
            "Item",
            filters={"name": ["in", item_codes]},
            fields=["name", "item_name", "has_batch_no", "is_stock_item", "has_expiry_date"],
        )
    }

    result: dict[str, list[dict]] = {}
    for row in rows:
        meta = item_meta.get(row.item_code)
        if not meta or not cint(meta.is_stock_item):
            continue

        qty_pending = flt(row.qty) - flt(row.received_qty)
        if qty_pending <= 0:
            continue

        effective_warehouse = row.warehouse
        if warehouse and effective_warehouse and effective_warehouse != warehouse:
            continue

        result.setdefault(row.parent, []).append(
            {
                "po_item_name": row.name,
                "item_code": row.item_code,
                "item_name": row.item_name or meta.item_name,
                "qty_pending": qty_pending,
                "uom": row.uom or row.stock_uom,
                "stock_uom": row.stock_uom,
                "conversion_factor": flt(row.conversion_factor) or 1.0,
                "warehouse": effective_warehouse,
                "schedule_date": str(row.schedule_date) if row.schedule_date else None,
                "has_batch_no": cint(meta.has_batch_no),
                "has_expiry_date": cint(meta.has_expiry_date),
            }
        )

    return result


def _build_pr_from_po(po_name: str, selected_rows: dict[str, dict], target_warehouse: str):
    pr_item_meta = frappe.get_meta("Purchase Receipt Item")

    def condition(source):
        return source.name in selected_rows

    def postprocess_item(source, target, source_parent):
        request_row = selected_rows[source.name]
        qty = flt(request_row["qty"])
        target.qty = qty
        target.received_qty = 0
        target.stock_qty = qty * (flt(source.conversion_factor) or 1.0)
        target.warehouse = target_warehouse
        target.rejected_warehouse = None

        if pr_item_meta.has_field("supplier_batch_no") and request_row.get("supplier_batch"):
            target.supplier_batch_no = request_row["supplier_batch"]
        if pr_item_meta.has_field("expiry_date") and request_row.get("expiry_date"):
            target.expiry_date = request_row["expiry_date"]

    pr = get_mapped_doc(
        "Purchase Order",
        po_name,
        {
            "Purchase Order": {
                "doctype": "Purchase Receipt",
                "validation": {"docstatus": ["=", 1]},
            },
            "Purchase Order Item": {
                "doctype": "Purchase Receipt Item",
                "field_map": {
                    "name": "purchase_order_item",
                    "parent": "purchase_order",
                },
                "condition": condition,
                "postprocess": postprocess_item,
            },
        },
    )

    pr.set_warehouse = target_warehouse
    pr.items = [row for row in pr.items if getattr(row, "purchase_order_item", None) in selected_rows]
    return pr


def _get_batch_from_bundle(bundle_name: str | None) -> str | None:
    if not bundle_name:
        return None

    rows = frappe.get_all(
        "Serial and Batch Entry",
        filters={"parent": bundle_name},
        fields=["batch_no"],
        limit=1,
    )
    return rows[0].batch_no if rows else None


def _create_incoming_quality_inspection(pr_doc, row, request_row: dict, actor_user: str) -> str | None:
    requires_qi = cint(frappe.db.get_value("Item", row.item_code, "inspection_required_before_purchase"))
    if not requires_qi:
        return None

    qi = frappe.new_doc("Quality Inspection")
    qi.inspection_type = "Incoming"
    qi.item_code = row.item_code
    qi.sample_size = flt(row.qty)
    qi.report_date = today()
    qi.company = pr_doc.company
    qi.manual_inspection = 1
    qi.inspected_by = actor_user
    qi.verified_by = actor_user
    qi.status = "Accepted"
    qi.reference_type = "Purchase Receipt"
    qi.reference_name = pr_doc.name
    qi.remarks = (
        f"Inspection auto generee pour reception kiosque. "
        f"Lot fournisseur: {request_row.get('supplier_batch') or 'N/A'}."
    )
    qi.flags.ignore_permissions = True
    qi.insert(ignore_permissions=True)
    qi.flags.ignore_permissions = True
    qi.submit()
    return qi.name


def _update_batch_metadata(batch_no: str | None, request_row: dict):
    if not batch_no or not frappe.db.exists("Batch", batch_no):
        return

    batch = frappe.get_doc("Batch", batch_no)
    batch_meta = frappe.get_meta("Batch")
    changed = False

    if request_row.get("expiry_date"):
        batch.expiry_date = request_row["expiry_date"]
        changed = True

    if request_row.get("supplier_batch"):
        for fieldname in ("supplier_batch_no", "custom_supplier_batch", "reference_batch"):
            if batch_meta.has_field(fieldname):
                setattr(batch, fieldname, request_row["supplier_batch"])
                changed = True
                break

    if changed:
        batch.save(ignore_permissions=True)


def _build_generated_batches(pr_doc, selected_rows: dict[str, dict]) -> list[dict]:
    generated = []

    for row in pr_doc.items:
        request_row = selected_rows.get(getattr(row, "purchase_order_item", None))
        if not request_row:
            continue

        batch_no = getattr(row, "batch_no", None) or _get_batch_from_bundle(getattr(row, "serial_and_batch_bundle", None))
        _update_batch_metadata(batch_no, request_row)

        generated.append(
            {
                "item_code": row.item_code,
                "item_name": row.item_name,
                "batch_no": batch_no,
                "qty": flt(row.qty),
                "uom": row.uom,
                "expiry_date": request_row.get("expiry_date"),
                "supplier_batch": request_row.get("supplier_batch"),
            }
        )

    return generated


def bootstrap_recepcion_sandbox():
    """Crea una Purchase Order abierta reutilizable para smoke tests de recepcion."""
    company = "Peintures du Maroc SARL"
    supplier = "ChimEurope SARL"
    warehouse = _get_quarantine_mp_warehouse(company)
    po_name = frappe.db.get_value(
        "Purchase Order",
        {
            "company": company,
            "supplier": supplier,
            "docstatus": 1,
            "status": ["!=", "Closed"],
            "per_received": ["<", 100],
        },
        "name",
    )
    if po_name:
        return {"po_name": po_name, "created": False}

    po = frappe.new_doc("Purchase Order")
    po.company = company
    po.supplier = supplier
    po.schedule_date = today()
    po.transaction_date = today()
    po.currency = "MAD"
    po.buying_price_list = "Standard Buying MAD"
    po.set_warehouse = warehouse
    po.tc_name = None
    po.remarks = "Sandbox reception smoke autogenerated"

    for item_code, qty, rate in [
        ("MP-RES-ALK-G70", 250.0, 25.0),
        ("ENV-BID-20L-BLC", 40.0, 8.0),
    ]:
        item_meta = frappe.db.get_value("Item", item_code, ["item_name", "stock_uom"], as_dict=True)
        po.append(
            "items",
            {
                "item_code": item_code,
                "item_name": item_meta.item_name,
                "qty": qty,
                "schedule_date": today(),
                "rate": rate,
                "uom": item_meta.stock_uom,
                "stock_uom": item_meta.stock_uom,
                "warehouse": warehouse,
            },
        )

    po.insert(ignore_permissions=True)
    po.submit()
    return {"po_name": po.name, "created": True}


def smoke_probe_recepcion_registro():
    """Helper de bench para aislar fallos internos de registrar_recepcion."""
    bootstrap = bootstrap_recepcion_sandbox()
    po_name = bootstrap["po_name"]
    user_id = frappe.db.get_value("Employee", {"custom_qr_badge_token": "OP-2026-BADGE-00042"}, "user_id")
    if user_id:
        frappe.set_user(user_id)
    return registrar_recepcion(
        po_name=po_name,
        items_recibidos=[
            {
                "item_code": "MP-RES-ALK-G70",
                "qty": 1,
                "supplier_batch": "FOURN-PROBE",
                "expiry_date": str(getdate(today())),
            }
        ],
    )


def get_latest_recepcion_error():
    rows = frappe.get_all(
        "Error Log",
        filters={"method": ["like", "%registrar_recepcion%"]},
        fields=["name", "creation", "method", "error"],
        order_by="creation desc",
        limit=1,
    )
    return rows[0] if rows else {}


def inspect_latest_recepcion_receipt():
    latest_name = frappe.db.get_value(
        "Purchase Receipt",
        {"remarks": ["like", "%Sandbox reception smoke autogenerated%"]},
        "name",
        order_by="creation desc",
    )
    if not latest_name:
        return {}

    receipt = frappe.get_doc("Purchase Receipt", latest_name)
    items = []
    for row in receipt.items:
        items.append(
            {
                "name": row.name,
                "item_code": row.item_code,
                "batch_no": getattr(row, "batch_no", None),
                "serial_and_batch_bundle": getattr(row, "serial_and_batch_bundle", None),
                "quality_inspection": getattr(row, "quality_inspection", None),
            }
        )

    bundles = frappe.get_all(
        "Serial and Batch Entry",
        filters={"voucher_no": latest_name},
        fields=["parent", "batch_no", "qty", "voucher_detail_no"],
        order_by="creation desc",
    )
    return {"purchase_receipt": latest_name, "items": items, "bundle_entries": bundles}


def bootstrap_cuarentena_transfer_sandbox():
    """Prepara un lote con saldo en Cuarentena MP para smoke de traslado."""
    company = "Peintures du Maroc SARL"
    source_warehouse = _get_quarantine_mp_warehouse(company)
    target_warehouse = _get_approved_mp_warehouse(company)
    item_code = "MP-RES-ALK-G70"
    batch_no = "LOTE-QA-RECEP-0001"

    if not frappe.db.exists("Batch", batch_no):
        batch = frappe.new_doc("Batch")
        batch.batch_id = batch_no
        batch.item = item_code
        batch.expiry_date = getdate("2027-12-31")
        batch.insert(ignore_permissions=True)

    current_qty = get_stock_lote_almacen(item_code, source_warehouse, batch_no)
    if current_qty < 50:
        delta_qty = 50 - current_qty
        with _run_as_system_user():
            stock_entry = frappe.new_doc("Stock Entry")
            stock_entry.stock_entry_type = "Material Receipt"
            stock_entry.purpose = "Material Receipt"
            stock_entry.company = company
            stock_entry.posting_date = today()
            stock_entry.set_posting_time = 1
            stock_entry.remarks = "Bootstrap cuarentena transfer sandbox"
            stock_entry.append(
                "items",
                {
                    "item_code": item_code,
                    "qty": delta_qty,
                    "t_warehouse": source_warehouse,
                    "basic_rate": 25,
                    "batch_no": batch_no,
                    "use_serial_batch_fields": 1,
                },
            )
            stock_entry.insert(ignore_permissions=True)
            stock_entry.submit()

    return {
        "item_code": item_code,
        "batch_no": batch_no,
        "source_warehouse": source_warehouse,
        "target_warehouse": target_warehouse,
        "available_qty": get_stock_lote_almacen(item_code, source_warehouse, batch_no),
    }


def bootstrap_inventario_ciego_sandbox():
    """Prepara 5 lotes con stock en MP aprobada para smoke de inventario ciego."""
    company = "Peintures du Maroc SARL"
    warehouse = _get_approved_mp_warehouse(company)
    item_code = "MP-RES-ALK-G70"
    batches = []

    for index in range(1, 6):
        batch_no = f"LOTE-CIEGO-2026-{index:04d}"
        target_qty = 10 + index

        if not frappe.db.exists("Batch", batch_no):
            batch = frappe.new_doc("Batch")
            batch.batch_id = batch_no
            batch.item = item_code
            batch.expiry_date = getdate("2027-12-31")
            batch.insert(ignore_permissions=True)

        current_qty = get_stock_lote_almacen(item_code, warehouse, batch_no)
        if current_qty < target_qty:
            delta_qty = target_qty - current_qty
            with _run_as_system_user():
                stock_entry = frappe.new_doc("Stock Entry")
                stock_entry.stock_entry_type = "Material Receipt"
                stock_entry.purpose = "Material Receipt"
                stock_entry.company = company
                stock_entry.posting_date = today()
                stock_entry.set_posting_time = 1
                stock_entry.remarks = f"Bootstrap inventario ciego sandbox {batch_no}"
                stock_entry.append(
                    "items",
                    {
                        "item_code": item_code,
                        "qty": delta_qty,
                        "t_warehouse": warehouse,
                        "basic_rate": 25,
                        "batch_no": batch_no,
                        "use_serial_batch_fields": 1,
                    },
                )
                stock_entry.insert(ignore_permissions=True)
                stock_entry.submit()

        available_qty = get_stock_lote_almacen(item_code, warehouse, batch_no)
        batches.append(
            {
                "item_code": item_code,
                "batch_no": batch_no,
                "qty_fisica": available_qty,
                "current_qty": available_qty,
            }
        )

    return {
        "warehouse": warehouse,
        "conteo": batches,
        "total": len(batches),
    }


def inspect_latest_blind_inventory_reconciliation():
    latest_name = frappe.db.get_value(
        "Stock Reconciliation",
        {"docstatus": 0},
        "name",
        order_by="creation desc",
    )
    if not latest_name:
        return {}

    doc = frappe.get_doc("Stock Reconciliation", latest_name)
    items = []
    for row in doc.items:
        items.append(
            {
                "item_code": row.item_code,
                "warehouse": row.warehouse,
                "batch_no": getattr(row, "batch_no", None),
                "qty": flt(row.qty),
                "current_qty": flt(getattr(row, "current_qty", 0)),
                "quantity_difference": flt(getattr(row, "quantity_difference", 0)),
            }
        )

    return {
        "name": doc.name,
        "company": doc.company,
        "warehouse": getattr(doc, "set_warehouse", None),
        "docstatus": doc.docstatus,
        "items_count": len(items),
        "items": items,
    }


@frappe.whitelist()
def get_compras_pendientes(company: str = None, warehouse: str = None):
    """EP_REC_1 — lista Purchase Orders abiertas con items pendientes de recepcion."""
    profile_error = _require_kiosk_profile("production", "reception")
    if profile_error:
        return profile_error

    if not company:
        frappe.local.response["http_status_code"] = 400
        return {
            "success": False,
            "error_code": "MISSING_COMPANY",
            "message_fr": "Parametre 'company' obligatoire.",
        }

    try:
        purchase_orders = frappe.get_all(
            "Purchase Order",
            filters={
                "company": company,
                "docstatus": 1,
                "status": ["!=", "Closed"],
                "per_received": ["<", 100],
            },
            fields=["name", "supplier", "supplier_name", "transaction_date", "schedule_date", "set_warehouse"],
            order_by="transaction_date desc, name desc",
        )

        po_names = [po.name for po in purchase_orders]
        pending_rows = _get_pending_po_items(po_names, warehouse=warehouse)

        ordenes = []
        for po in purchase_orders:
            items = pending_rows.get(po.name, [])
            if not items:
                continue

            ordenes.append(
                {
                    "po_name": po.name,
                    "supplier": po.supplier,
                    "supplier_name": po.supplier_name,
                    "transaction_date": str(po.transaction_date) if po.transaction_date else None,
                    "schedule_date": str(po.schedule_date) if po.schedule_date else None,
                    "set_warehouse": po.set_warehouse,
                    "items": items,
                }
            )

        return {
            "success": True,
            "company": company,
            "warehouse": warehouse,
            "total": len(ordenes),
            "ordenes": ordenes,
        }
    except Exception:
        frappe.log_error(
            title=f"Erreur get_compras_pendientes — {company}",
            message=frappe.get_traceback(),
        )
        frappe.local.response["http_status_code"] = 500
        return {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message_fr": "Erreur interne lors du chargement des commandes en attente.",
        }


@frappe.whitelist()
def registrar_recepcion(po_name: str = None, items_recibidos=None, warehouse: str = None):
    """EP_REC_2 — crea Purchase Receipt para una recepcion feliz en cuarentena MP."""
    profile_error = _require_kiosk_profile("production", "reception")
    if profile_error:
        return profile_error

    if not po_name or items_recibidos is None:
        frappe.local.response["http_status_code"] = 400
        return {
            "success": False,
            "error_code": "MISSING_PARAMS",
            "message_fr": "Parametres obligatoires: po_name et items_recibidos.",
        }

    try:
        po = frappe.db.get_value(
            "Purchase Order",
            po_name,
            ["name", "company", "docstatus", "status"],
            as_dict=True,
        )
        if not po:
            frappe.local.response["http_status_code"] = 404
            return {
                "success": False,
                "error_code": "PO_NOT_FOUND",
                "message_fr": f"Commande d'achat '{po_name}' introuvable.",
            }
        if cint(po.docstatus) != 1 or po.status == "Closed":
            frappe.local.response["http_status_code"] = 409
            return {
                "success": False,
                "error_code": "PO_NOT_RECEIVABLE",
                "message_fr": "Cette commande n'est pas ouverte a la reception.",
            }

        requested_items = _parse_items_recibidos(items_recibidos)
        if not requested_items:
            frappe.local.response["http_status_code"] = 400
            return {
                "success": False,
                "error_code": "EMPTY_ITEMS",
                "message_fr": "Aucune ligne de reception a enregistrer.",
            }

        target_warehouse = warehouse or _get_quarantine_mp_warehouse(po.company)
        pending_rows = _get_pending_po_items([po_name]).get(po_name, [])
        pending_by_code = {row["item_code"]: row for row in pending_rows}
        selected_rows: dict[str, dict] = {}

        for item in requested_items:
            pending = pending_by_code.get(item["item_code"])
            if not pending:
                frappe.local.response["http_status_code"] = 422
                return {
                    "success": False,
                    "error_code": "ITEM_NOT_PENDING",
                    "message_fr": f"L'article {item['item_code']} n'est pas en attente sur cette commande.",
                }
            if flt(item["qty"]) > flt(pending["qty_pending"]):
                frappe.local.response["http_status_code"] = 422
                return {
                    "success": False,
                    "error_code": "QTY_EXCEEDS_PENDING",
                    "message_fr": f"Quantite recue superieure au reliquat pour {item['item_code']}.",
                }

            selected_rows[pending["po_item_name"]] = {
                **item,
                "item_name": pending["item_name"],
            }

        actor_user = frappe.session.user
        with _run_as_system_user():
            pr = _build_pr_from_po(po_name, selected_rows, target_warehouse)
            pr.flags.ignore_permissions = True
            pr.insert(ignore_permissions=True)

            inspections_by_po_item = {}
            for row in pr.items:
                request_row = selected_rows.get(getattr(row, "purchase_order_item", None))
                if not request_row:
                    continue
                inspection_name = _create_incoming_quality_inspection(pr, row, request_row, actor_user)
                if inspection_name:
                    inspections_by_po_item[getattr(row, "purchase_order_item", None)] = inspection_name

            pr.reload()
            for row in pr.items:
                inspection_name = inspections_by_po_item.get(getattr(row, "purchase_order_item", None))
                if inspection_name:
                    row.quality_inspection = inspection_name

            pr.flags.ignore_permissions = True
            pr.save(ignore_permissions=True)
            pr.flags.ignore_permissions = True
            pr.submit()

        generated_batches = _build_generated_batches(pr, selected_rows)

        return {
            "success": True,
            "purchase_receipt": pr.name,
            "warehouse": target_warehouse,
            "posting_date": str(getattr(pr, "posting_date", today())),
            "lotes_generados": generated_batches,
            "message_fr": "Reception enregistree avec succes.",
        }
    except frappe.ValidationError as exc:
        frappe.db.rollback()
        error_code = str(exc)
        code_map = {
            "INVALID_ITEMS_JSON": (400, "Format JSON invalide pour items_recibidos."),
            "INVALID_ITEMS_TYPE": (400, "items_recibidos doit etre une liste."),
            "INVALID_ITEM_ROW": (400, "Chaque ligne de reception doit etre un objet valide."),
            "MISSING_ITEM_CODE": (400, "Chaque ligne doit contenir item_code."),
            "INVALID_QTY": (400, "Chaque quantite recue doit etre strictement positive."),
        }
        status_code, message = code_map.get(error_code, (422, "Donnees de reception invalides."))
        frappe.local.response["http_status_code"] = status_code
        return {
            "success": False,
            "error_code": error_code,
            "message_fr": message,
        }
    except Exception:
        frappe.db.rollback()
        frappe.log_error(
            title=f"Erreur registrar_recepcion — {po_name}",
            message=frappe.get_traceback(),
        )
        frappe.local.response["http_status_code"] = 500
        return {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message_fr": "Erreur interne pendant l'enregistrement de la reception.",
        }


@frappe.whitelist()
def trasladar_lote_aprobado(
    item_code: str = None,
    batch_no: str = None,
    qty_to_move: str | float = None,
    source_warehouse: str = None,
    target_warehouse: str = None,
):
    """EP_REC_3 — traslada un lote desde Cuarentena MP hacia stock aprobado."""
    profile_error = _require_kiosk_profile("production", "quality", "reception")
    if profile_error:
        return profile_error

    if not item_code or not batch_no or qty_to_move is None:
        frappe.local.response["http_status_code"] = 400
        return {
            "success": False,
            "error_code": "MISSING_PARAMS",
            "message_fr": "Parametres obligatoires: item_code, batch_no et qty_to_move.",
        }

    try:
        qty = flt(qty_to_move)
        if qty <= 0:
            frappe.local.response["http_status_code"] = 400
            return {
                "success": False,
                "error_code": "INVALID_QTY",
                "message_fr": "La quantite a transferer doit etre strictement positive.",
            }

        batch = frappe.db.get_value("Batch", batch_no, ["name", "item"], as_dict=True)
        if not batch:
            frappe.local.response["http_status_code"] = 404
            return {
                "success": False,
                "error_code": "BATCH_NOT_FOUND",
                "message_fr": f"Lot '{batch_no}' introuvable.",
            }
        if batch.item != item_code:
            frappe.local.response["http_status_code"] = 422
            return {
                "success": False,
                "error_code": "BATCH_ITEM_MISMATCH",
                "message_fr": "Le lot scanne ne correspond pas a cet article.",
            }

        company = frappe.db.get_value("Item Default", {"parent": item_code}, "company") or "Peintures du Maroc SARL"
        source = source_warehouse or _get_quarantine_mp_warehouse(company)
        target = target_warehouse or _get_approved_mp_warehouse(company)
        available_qty = get_stock_lote_almacen(item_code, source, batch_no)
        if available_qty < qty:
            frappe.local.response["http_status_code"] = 422
            return {
                "success": False,
                "error_code": "INSUFFICIENT_STOCK",
                "message_fr": f"Stock insuffisant en quarantaine. Disponible: {available_qty}.",
                "available_qty": available_qty,
            }

        with _run_as_system_user():
            stock_entry = frappe.new_doc("Stock Entry")
            stock_entry.stock_entry_type = "Material Transfer"
            stock_entry.purpose = "Material Transfer"
            stock_entry.company = company
            stock_entry.posting_date = today()
            stock_entry.set_posting_time = 1
            stock_entry.remarks = f"Transfert quarantaine du lot {batch_no}"
            stock_entry.append(
                "items",
                {
                    "item_code": item_code,
                    "qty": qty,
                    "s_warehouse": source,
                    "t_warehouse": target,
                    "batch_no": batch_no,
                    "use_serial_batch_fields": 1,
                },
            )
            stock_entry.flags.ignore_permissions = True
            stock_entry.insert(ignore_permissions=True)
            stock_entry.flags.ignore_permissions = True
            stock_entry.submit()

        return {
            "success": True,
            "stock_entry": stock_entry.name,
            "item_code": item_code,
            "batch_no": batch_no,
            "qty_moved": qty,
            "source_warehouse": source,
            "target_warehouse": target,
            "message_fr": "Lot transfere vers le stock approuve.",
        }
    except Exception:
        frappe.db.rollback()
        frappe.log_error(
            title=f"Erreur trasladar_lote_aprobado — {item_code} / {batch_no}",
            message=frappe.get_traceback(),
        )
        frappe.local.response["http_status_code"] = 500
        return {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message_fr": "Erreur interne pendant le transfert du lot.",
        }


@frappe.whitelist()
def get_lote_para_impresion(batch_no: str = None):
    """EP_REC_4 — reconstruye los datos de etiqueta para reimpresion Zebra."""
    profile_error = _require_kiosk_profile("production", "quality", "reception")
    if profile_error:
        return profile_error

    if not batch_no:
        frappe.local.response["http_status_code"] = 400
        return {
            "success": False,
            "error_code": "MISSING_PARAMS",
            "message_fr": "Parametre 'batch_no' obligatoire.",
        }

    try:
        batch = frappe.db.get_value(
            "Batch",
            batch_no,
            ["name", "item", "expiry_date"],
            as_dict=True,
        )
        if not batch:
            frappe.local.response["http_status_code"] = 404
            return {
                "success": False,
                "error_code": "BATCH_NOT_FOUND",
                "message_fr": f"Lot '{batch_no}' introuvable.",
            }

        item = frappe.db.get_value("Item", batch.item, ["item_code", "item_name"], as_dict=True)
        return {
            "success": True,
            "etiqueta": {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "batch_no": batch.name,
                "expiry_date": str(batch.expiry_date) if batch.expiry_date else None,
            },
            "message_fr": "Donnees de reimpression chargees.",
        }
    except Exception:
        frappe.log_error(
            title=f"Erreur get_lote_para_impresion — {batch_no}",
            message=frappe.get_traceback(),
        )
        frappe.local.response["http_status_code"] = 500
        return {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message_fr": "Erreur interne lors de la lecture de l'etiquette.",
        }


@frappe.whitelist()
def subir_conteo_fisico(warehouse: str = None, conteo=None):
    """EP_REC_5 — crea un Stock Reconciliation draft a partir de un conteo ciego."""
    profile_error = _require_kiosk_profile("production", "quality", "reception")
    if profile_error:
        return profile_error

    if not warehouse or conteo is None:
        frappe.local.response["http_status_code"] = 400
        return {
            "success": False,
            "error_code": "MISSING_PARAMS",
            "message_fr": "Parametres obligatoires: warehouse et conteo.",
        }

    try:
        company = _get_company_from_warehouse(warehouse)
        if not company:
            frappe.local.response["http_status_code"] = 404
            return {
                "success": False,
                "error_code": "WAREHOUSE_NOT_FOUND",
                "message_fr": f"Entrepot '{warehouse}' introuvable.",
            }

        conteo_rows = _parse_conteo_fisico(conteo)
        if not conteo_rows:
            frappe.local.response["http_status_code"] = 400
            return {
                "success": False,
                "error_code": "EMPTY_CONTEO",
                "message_fr": "Aucune ligne de comptage a envoyer.",
            }

        prepared_rows = []
        for row in conteo_rows:
            item = frappe.db.get_value(
                "Item",
                row["item_code"],
                ["name", "item_name", "stock_uom"],
                as_dict=True,
            )
            if not item:
                frappe.throw(_("ITEM_NOT_FOUND"), frappe.ValidationError)

            batch = frappe.db.get_value("Batch", row["batch_no"], ["name", "item"], as_dict=True)
            if not batch:
                frappe.throw(_("BATCH_NOT_FOUND"), frappe.ValidationError)
            if batch.item != row["item_code"]:
                frappe.throw(_("BATCH_ITEM_MISMATCH"), frappe.ValidationError)

            current_qty = get_stock_lote_almacen(row["item_code"], warehouse, row["batch_no"])
            qty_fisica = flt(row["qty_fisica"])
            quantity_difference = qty_fisica - current_qty
            if quantity_difference == 0:
                continue

            prepared_rows.append(
                {
                    "item_code": row["item_code"],
                    "item_name": item.item_name,
                    "warehouse": warehouse,
                    "qty": qty_fisica,
                    "stock_uom": item.stock_uom,
                    "batch_no": row["batch_no"],
                    "use_serial_batch_fields": 1,
                    "current_qty": current_qty,
                    "quantity_difference": quantity_difference,
                }
            )

        if not prepared_rows:
            raise frappe.ValidationError("NO_DIFFERENCES_FOUND")

        with _run_as_system_user():
            reconciliation = frappe.new_doc("Stock Reconciliation")
            reconciliation.company = company
            reconciliation.purpose = "Stock Reconciliation"
            reconciliation.posting_date = today()
            reconciliation.set_posting_time = 1
            reconciliation.set_warehouse = warehouse

            for row in prepared_rows:
                reconciliation.append("items", row)

            reconciliation.flags.ignore_permissions = True
            reconciliation.insert(ignore_permissions=True)

        return {
            "success": True,
            "reconciliation_doc": reconciliation.name,
            "warehouse": warehouse,
            "items_count": len(prepared_rows),
            "message_fr": "Comptage envoye en brouillon pour reconciliation.",
        }
    except frappe.ValidationError as exc:
        frappe.db.rollback()
        error_code = str(exc)
        code_map = {
            "INVALID_CONTEO_JSON": (400, "Format JSON invalide pour conteo."),
            "INVALID_CONTEO_TYPE": (400, "conteo doit etre une liste."),
            "INVALID_CONTEO_ROW": (400, "Chaque ligne de comptage doit etre un objet valide."),
            "MISSING_ITEM_CODE": (400, "Chaque ligne doit contenir item_code."),
            "MISSING_BATCH_NO": (400, "Chaque ligne doit contenir batch_no."),
            "INVALID_QTY": (400, "Chaque quantite physique doit etre strictement positive."),
            "ITEM_NOT_FOUND": (404, "Article introuvable dans ERPNext."),
            "BATCH_NOT_FOUND": (404, "Lot introuvable dans ERPNext."),
            "BATCH_ITEM_MISMATCH": (422, "Le lot scanne ne correspond pas a cet article."),
            "NO_DIFFERENCES_FOUND": (422, "Aucune difference detectee entre le comptage physique et le stock systeme."),
            "None of the items have any change in quantity or value.": (422, "Aucune difference detectee entre le comptage physique et le stock systeme."),
        }
        status_code, message = code_map.get(error_code, (422, "Donnees de comptage invalides."))
        frappe.local.response["http_status_code"] = status_code
        return {
            "success": False,
            "error_code": error_code,
            "message_fr": message,
        }
    except Exception:
        frappe.db.rollback()
        frappe.log_error(
            title=f"Erreur subir_conteo_fisico — {warehouse}",
            message=frappe.get_traceback(),
        )
        frappe.local.response["http_status_code"] = 500
        return {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message_fr": "Erreur interne pendant la creation du brouillon de reconciliation.",
        }
