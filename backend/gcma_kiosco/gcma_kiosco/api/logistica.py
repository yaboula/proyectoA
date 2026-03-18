"""
GCMA / Maroc B2B — Endpoints logisticos (Sprint 09-10).

Contrato API objetivo:
- GET  /api/method/maroc_b2b.api.logistica.get_pick_list
- POST /api/method/maroc_b2b.api.logistica.validar_scan_fefo
- GET  /api/method/maroc_b2b.api.logistica.get_entregas_pendientes_chofer
- POST /api/method/maroc_b2b.api.logistica.registrar_pod
"""

from __future__ import annotations

import base64
from datetime import date
from typing import Any

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


def _get_so_items_pending(sales_order: str) -> list[dict[str, Any]]:
    """Devuelve las líneas del SO con cantidad pendiente de picking (qty - delivered_qty)."""
    rows = frappe.get_all(
        "Sales Order Item",
        filters={"parent": sales_order, "parenttype": "Sales Order"},
        fields=["name", "item_code", "item_name", "qty", "delivered_qty", "warehouse"],
    )
    pending = []
    for row in rows:
        qty_pedida = flt(row.qty)
        qty_entregada = flt(row.delivered_qty)
        qty_pendiente = max(0.0, qty_pedida - qty_entregada)
        if qty_pendiente > 0:
            pending.append(
                {
                    "item_code": row.item_code,
                    "item_name": row.item_name or row.item_code,
                    "qty_pedida": flt(qty_pedida, 3),
                    "qty_entregada": flt(qty_entregada, 3),
                    "qty_pendiente": flt(qty_pendiente, 3),
                    "warehouse": row.warehouse or "",
                }
            )
    return pending


def _enrich_with_fefo_batch(item: dict[str, Any], warehouse: str) -> dict[str, Any]:
    """Añade la sugerencia de lote FEFO al dict del item."""
    best = _get_oldest_batch_with_stock(item["item_code"], warehouse)
    item["lote_fefo_sugerido"] = best["name"] if best else None
    item["lote_expiry"] = str(best["expiry_date"]) if best and best.get("expiry_date") and best["expiry_date"].year != 9999 else None
    item["lote_stock_disponible"] = flt(best["stock"], 3) if best else 0.0
    return item


@frappe.whitelist()
def get_pick_list(sales_order: str):
    """Sprint 09 — Lista de picking FEFO para un Sales Order."""
    if not sales_order:
        frappe.throw(_("Parametro obligatorio: sales_order"), frappe.ValidationError)

    if not frappe.db.exists("Sales Order", sales_order):
        frappe.throw(_("Sales Order no existe: {0}").format(sales_order), frappe.DoesNotExistError)

    so = frappe.db.get_value(
        "Sales Order",
        sales_order,
        ["customer", "status", "docstatus", "set_warehouse"],
        as_dict=True,
    )

    if so.docstatus == 2:
        frappe.throw(_("Sales Order cancelado"), frappe.ValidationError)

    pending_items = _get_so_items_pending(sales_order)

    enriched = []
    for item in pending_items:
        warehouse = item["warehouse"] or so.set_warehouse or ""
        item["warehouse"] = warehouse
        enriched.append(_enrich_with_fefo_batch(item, warehouse))

    return {
        "sales_order": sales_order,
        "customer": so.customer,
        "status": so.status,
        "items": enriched,
        "total_items_pendientes": len(enriched),
    }


@frappe.whitelist()
def validar_scan_fefo(sales_order: str, item_code: str, batch_scanned: str, qty_ya_escaneada: str = "0"):
    """Contrato 2.1 — Poka-Yoke FEFO + control de cantidad para cada bip del picking."""
    if not sales_order or not item_code or not batch_scanned:
        frappe.throw(_("Parametros obligatorios: sales_order, item_code, batch_scanned"), frappe.ValidationError)

    if not frappe.db.exists("Sales Order", sales_order):
        frappe.throw(_("Sales Order no existe"), frappe.ValidationError)

    acumulado = max(0.0, flt(qty_ya_escaneada))

    so_item = _get_sales_order_item(sales_order, item_code)
    warehouse = _get_dispatch_warehouse(so_item, sales_order)

    qty_pedida = flt(so_item.qty)
    qty_entregada = flt(so_item.delivered_qty)
    qty_pendiente = max(0.0, qty_pedida - qty_entregada)

    # Control de cantidad: el acumulado ya alcanza o supera lo pedido
    if acumulado >= qty_pendiente:
        frappe.throw(
            _("Quantite deja atteinte ({0}/{1}). Finalisez cet article.").format(
                int(acumulado), int(qty_pendiente)
            ),
            frappe.ValidationError,
        )

    # Verificar que el siguiente scan no exceda el pedido
    if acumulado + 1 > qty_pendiente:
        frappe.throw(
            _("Quantite excedee: {0} scannes pour {1} commandes.").format(
                int(acumulado + 1), int(qty_pendiente)
            ),
            frappe.ValidationError,
        )

    scanned = _get_batch_for_item(batch_scanned, item_code)
    scanned_stock = flt(get_stock_lote_almacen(item_code, warehouse, scanned.name))
    if scanned_stock <= 0:
        frappe.throw(_("Lot scanne sans stock disponible en expedition"), frappe.ValidationError)

    expected = _get_oldest_batch_with_stock(item_code, warehouse)
    if not expected:
        frappe.throw(_("Aucun stock disponible pour cet article"), frappe.ValidationError)

    if expected["name"] != scanned.name:
        message = (
            _("Violation FEFO: Le lot {0} (stock: {1}) doit etre extrait en premier.").format(
                expected["name"], flt(expected["stock"], 2)
            )
        )
        frappe.throw(message, frappe.ValidationError)

    nuevo_acumulado = acumulado + 1
    qty_restante = max(0.0, qty_pendiente - nuevo_acumulado)
    cierre_parcial = qty_restante == 0

    return {
        "status": "ok",
        "batch_validado": scanned.name,
        "qty_escaneada_total": flt(nuevo_acumulado, 2),
        "qty_pendiente": flt(qty_pendiente, 2),
        "qty_restante": flt(qty_restante, 2),
        "cierre_parcial": cierre_parcial,
    }


@frappe.whitelist()
def get_entregas_pendientes_chofer(limit: int = 50):
    """Sprint 10 — Entregas pendientes del turno para el chofer autenticado."""
    limit_value = max(1, min(int(flt(limit, 0)), 200))

    rows = frappe.get_all(
        "Delivery Note",
        filters={
            "docstatus": ["in", [0, 1]],
            "status": ["not in", ["Completed", "Closed", "Cancelled"]],
        },
        fields=[
            "name",
            "customer",
            "customer_name",
            "posting_date",
            "status",
            "docstatus",
            "set_warehouse",
            "total_qty",
            "grand_total",
        ],
        order_by="posting_date asc, name asc",
        limit=limit_value,
    )

    enriched = []
    for row in rows:
        estado_pwa = None
        if row.get("name"):
            estado_pwa = frappe.db.get_value("Delivery Note", row.name, "estado_entrega_pwa")

        enriched.append(
            {
                "name": row.name,
                "customer": row.customer,
                "customer_name": row.customer_name or row.customer,
                "posting_date": str(row.posting_date) if row.posting_date else None,
                "status": row.status,
                "docstatus": row.docstatus,
                "estado_entrega_pwa": estado_pwa or "Pendiente",
                "total_qty": flt(row.total_qty, 2),
                "grand_total": flt(row.grand_total, 2),
            }
        )

    return {
        "total": len(enriched),
        "entregas": enriched,
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
