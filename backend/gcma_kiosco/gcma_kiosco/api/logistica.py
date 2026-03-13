"""
GCMA / Maroc B2B — Endpoints logisticos (Sprint 09).

Contrato API objetivo:
- POST /api/method/maroc_b2b.api.logistica.validar_scan_fefo
"""

from __future__ import annotations

import base64
from datetime import date

import frappe
from frappe import _
from frappe.utils import flt

from gcma_kiosco.api.stock_utils import get_stock_lote_almacen


def _decode_b64_payload(payload: str, label: str) -> bytes:
    if not payload or not isinstance(payload, str):
        frappe.throw(_("Parametro obligatorio: {0}").format(label), frappe.ValidationError)

    raw = payload.strip()
    if "," in raw and ";base64" in raw:
        raw = raw.split(",", 1)[1]

    try:
        return base64.b64decode(raw, validate=True)
    except Exception:
        frappe.throw(_("Base64 invalido en {0}").format(label), frappe.ValidationError)


def _save_attachment(content: bytes, filename: str, doctype: str, docname: str) -> str:
    file_doc = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": filename,
            "is_private": 1,
            "content": content,
            "attached_to_doctype": doctype,
            "attached_to_name": docname,
        }
    )
    file_doc.insert(ignore_permissions=True)
    return file_doc.file_url


def _far_future() -> date:
    return date(9999, 12, 31)


def _get_sales_order_item(sales_order: str, item_code: str):
    row = frappe.db.get_value(
        "Sales Order Item",
        {"parent": sales_order, "item_code": item_code, "parenttype": "Sales Order"},
        ["name", "qty", "delivered_qty", "warehouse"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Item no pertenece al pedido indicado"), frappe.ValidationError)
    return row


def _get_dispatch_warehouse(so_item, sales_order: str) -> str:
    if so_item.warehouse:
        return so_item.warehouse

    so_warehouse = frappe.db.get_value("Sales Order", sales_order, "set_warehouse")
    if so_warehouse:
        return so_warehouse

    frappe.throw(_("No se pudo determinar warehouse de expedicion para FEFO"), frappe.ValidationError)


def _get_batch_for_item(batch_no: str, item_code: str):
    batch = frappe.db.get_value(
        "Batch",
        batch_no,
        ["name", "item", "expiry_date", "disabled"],
        as_dict=True,
    )
    if not batch:
        frappe.throw(_("Lote escaneado no existe"), frappe.ValidationError)
    if batch.item != item_code:
        frappe.throw(_("Lote escaneado no corresponde al SKU"), frappe.ValidationError)
    if int(batch.disabled or 0) == 1:
        frappe.throw(_("Lote escaneado esta deshabilitado"), frappe.ValidationError)
    return batch


def _get_oldest_batch_with_stock(item_code: str, warehouse: str):
    batches = frappe.get_all(
        "Batch",
        filters={"item": item_code},
        fields=["name", "expiry_date", "disabled"],
        order_by="expiry_date asc, creation asc",
    )

    active_rows = []
    for batch in batches:
        if int(batch.disabled or 0) == 1:
            continue

        stock = flt(get_stock_lote_almacen(item_code, warehouse, batch.name))
        if stock <= 0:
            continue

        active_rows.append(
            {
                "name": batch.name,
                "expiry_date": batch.expiry_date or _far_future(),
                "stock": stock,
            }
        )

    if not active_rows:
        return None

    active_rows.sort(key=lambda row: (row["expiry_date"], row["name"]))
    return active_rows[0]


@frappe.whitelist()
def validar_scan_fefo(sales_order: str, item_code: str, batch_scanned: str):
    """Contrato 2.1 — Poka-Yoke FEFO para cada bip del picking."""
    if not sales_order or not item_code or not batch_scanned:
        frappe.throw(_("Parametros obligatorios: sales_order, item_code, batch_scanned"), frappe.ValidationError)

    if not frappe.db.exists("Sales Order", sales_order):
        frappe.throw(_("Sales Order no existe"), frappe.ValidationError)

    so_item = _get_sales_order_item(sales_order, item_code)
    warehouse = _get_dispatch_warehouse(so_item, sales_order)

    scanned = _get_batch_for_item(batch_scanned, item_code)
    scanned_stock = flt(get_stock_lote_almacen(item_code, warehouse, scanned.name))
    if scanned_stock <= 0:
        frappe.throw(_("Lote escaneado sin stock disponible en expedicion"), frappe.ValidationError)

    expected = _get_oldest_batch_with_stock(item_code, warehouse)
    if not expected:
        frappe.throw(_("No hay stock disponible para el item escaneado"), frappe.ValidationError)

    if expected["name"] != scanned.name:
        message = (
            f"Violacion FEFO: Existe el {expected['name']} con stock {flt(expected['stock'], 2)}. "
            f"Extraiga ese primero."
        )
        frappe.throw(message, frappe.ValidationError)

    qty_restante_pedido = max(0.0, flt(so_item.qty) - flt(so_item.delivered_qty) - 1.0)

    return {
        "status": "ok",
        "qty_restante_pedido": flt(qty_restante_pedido, 2),
    }


@frappe.whitelist()
def registrar_pod(delivery_note_id: str, b64_signature: str, b64_photo: str):
    """Sprint 10 — Registra firma/foto POD y cierra Delivery Note."""
    if not delivery_note_id:
        frappe.throw(_("Parametro obligatorio: delivery_note_id"), frappe.ValidationError)

    if not frappe.db.exists("Delivery Note", delivery_note_id):
        frappe.throw(_("Delivery Note no existe"), frappe.ValidationError)

    signature_bytes = _decode_b64_payload(b64_signature, "b64_signature")
    photo_bytes = _decode_b64_payload(b64_photo, "b64_photo")

    dn = frappe.get_doc("Delivery Note", delivery_note_id)
    if dn.docstatus == 2:
        frappe.throw(_("Delivery Note cancelado no admite POD"), frappe.ValidationError)

    signature_url = _save_attachment(
        signature_bytes,
        f"{delivery_note_id}-signature.png",
        "Delivery Note",
        delivery_note_id,
    )
    photo_url = _save_attachment(
        photo_bytes,
        f"{delivery_note_id}-photo.jpg",
        "Delivery Note",
        delivery_note_id,
    )

    if dn.meta.has_field("firma_receptor"):
        dn.firma_receptor = signature_url
    if dn.meta.has_field("foto_sello_pod"):
        dn.foto_sello_pod = photo_url
    if dn.meta.has_field("estado_entrega_pwa"):
        dn.estado_entrega_pwa = "Entregado"

    dn.save(ignore_permissions=True)

    if dn.docstatus == 0:
        dn.submit()

    frappe.db.commit()

    return {
        "status": "success",
        "delivery_note": dn.name,
        "estado_entrega_pwa": "Entregado",
        "firma_receptor": signature_url,
        "foto_sello_pod": photo_url,
    }
