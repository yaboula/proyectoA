import json
from datetime import date

import frappe
from frappe.utils import add_days, today

from gcma_kiosco.api.stock_utils import get_stock_lote_almacen

SITE = "frontend"
SITES_PATH = "/home/frappe/frappe-bench/sites"
TARGET_WAREHOUSE = "Materia Prima Aprobada - PDM"
TARGET_CUSTOMER = "Droguerie Atlas"


def _find_batched_item_with_stock(warehouse: str):
    items = frappe.db.sql(
        """
        select b.item as item_code
        from `tabBatch` b
                inner join `tabItem` i on i.name = b.item
        where ifnull(b.disabled, 0) = 0
                    and ifnull(i.disabled, 0) = 0
                    and ifnull(i.is_sales_item, 0) = 1
        group by b.item
        having count(*) >= 2
        order by b.item asc
        """,
        as_dict=True,
    )

    for item in items:
        rows = []
        batches = frappe.get_all(
            "Batch",
            filters={"item": item.item_code, "disabled": 0},
            fields=["name", "expiry_date", "creation"],
            order_by="expiry_date asc, creation asc",
        )
        for b in batches:
            stock = float(get_stock_lote_almacen(item.item_code, warehouse, b.name) or 0)
            if stock > 0:
                rows.append({
                    "name": b.name,
                    "expiry_date": b.expiry_date,
                    "stock": stock,
                })

        if len(rows) >= 2:
            rows.sort(key=lambda r: (r["expiry_date"] or date(9999, 12, 31), r["name"]))
            return {
                "item_code": item.item_code,
                "oldest": rows[0],
                "newest": rows[-1],
            }

    return None


def _find_any_batched_item_with_stock(warehouse: str):
    items = frappe.db.sql(
        """
        select b.item as item_code
        from `tabBatch` b
        inner join `tabItem` i on i.name = b.item
        where ifnull(b.disabled, 0) = 0
          and ifnull(i.disabled, 0) = 0
        group by b.item
        having count(*) >= 2
        order by b.item asc
        """,
        as_dict=True,
    )

    for item in items:
        rows = []
        batches = frappe.get_all(
            "Batch",
            filters={"item": item.item_code, "disabled": 0},
            fields=["name", "expiry_date", "creation"],
            order_by="expiry_date asc, creation asc",
        )
        for b in batches:
            stock = float(get_stock_lote_almacen(item.item_code, warehouse, b.name) or 0)
            if stock > 0:
                rows.append(
                    {
                        "name": b.name,
                        "expiry_date": b.expiry_date,
                        "stock": stock,
                    }
                )

        if len(rows) >= 2:
            rows.sort(key=lambda r: (r["expiry_date"] or date(9999, 12, 31), r["name"]))
            return {
                "item_code": item.item_code,
                "oldest": rows[0],
                "newest": rows[-1],
            }

    return None


def _ensure_sales_order(customer: str, item_code: str, warehouse: str):
    existing = frappe.db.sql(
        """
        select so.name
        from `tabSales Order` so
        inner join `tabSales Order Item` soi on soi.parent = so.name
        where so.docstatus = 1
          and soi.item_code = %(item_code)s
          and ifnull(soi.warehouse, '') = %(warehouse)s
          and so.customer = %(customer)s
          and ifnull(so.status, '') not in ('Closed', 'Completed', 'Cancelled')
        order by so.modified desc
        limit 1
        """,
        {"item_code": item_code, "warehouse": warehouse, "customer": customer},
        as_dict=True,
    )
    if existing:
        return existing[0].name, False

    company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value("Company", {}, "name")
    if not company:
        raise RuntimeError("No default company found")

    so = frappe.get_doc(
        {
            "doctype": "Sales Order",
            "customer": customer,
            "company": company,
            "transaction_date": today(),
            "delivery_date": add_days(today(), 1),
            "order_type": "Sales",
            "set_warehouse": warehouse,
            "items": [
                {
                    "item_code": item_code,
                    "qty": 2,
                    "rate": 1,
                    "delivery_date": add_days(today(), 1),
                    "warehouse": warehouse,
                }
            ],
        }
    )
    so.insert(ignore_permissions=True)
    so.submit()
    return so.name, True


def _find_or_create_delivery_note(so_name: str):
    existing = frappe.db.sql(
        """
        select name
        from `tabDelivery Note`
        where docstatus = 1
          and ifnull(status, '') not in ('Closed', 'Completed')
        order by modified desc
        limit 1
        """,
        as_dict=True,
    )
    if existing:
        return existing[0].name, False

    # Try to generate from Sales Order mapper first.
    try:
        from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

        dn = make_delivery_note(so_name)
        dn.set_posting_time = 1
        dn.posting_date = today()
        dn.posting_time = "10:00:00"
        dn.insert(ignore_permissions=True)
        dn.submit()
        return dn.name, True
    except Exception:
        frappe.db.rollback()

    # Fallback: create minimal submitted DN using latest customer/item from SO.
    soi = frappe.get_all(
        "Sales Order Item",
        filters={"parent": so_name},
        fields=["item_code", "warehouse", "qty", "rate", "amount", "name"],
        limit=1,
    )
    if not soi:
        raise RuntimeError("No Sales Order Item found to build Delivery Note")

    so = frappe.get_doc("Sales Order", so_name)
    line = soi[0]

    dn = frappe.get_doc(
        {
            "doctype": "Delivery Note",
            "customer": so.customer,
            "company": so.company,
            "posting_date": today(),
            "set_posting_time": 1,
            "posting_time": "10:00:00",
            "items": [
                {
                    "item_code": line.item_code,
                    "qty": 1,
                    "rate": line.rate or 1,
                    "against_sales_order": so_name,
                    "so_detail": line.name,
                    "warehouse": line.warehouse,
                }
            ],
        }
    )
    dn.insert(ignore_permissions=True)
    dn.submit()
    return dn.name, True


def main():
    frappe.init(site=SITE, sites_path=SITES_PATH)
    frappe.connect()
    try:
        out = {"prepared": False, "notes": []}

        fefo = _find_batched_item_with_stock(TARGET_WAREHOUSE)
        item_marked_sales_temporarily = False

        if not fefo:
            # QA fallback: sandbox stock suele estar en MP no marcadas para venta.
            fefo = _find_any_batched_item_with_stock(TARGET_WAREHOUSE)
            if fefo:
                frappe.db.set_value("Item", fefo["item_code"], "is_sales_item", 1)
                item_marked_sales_temporarily = True

        if not fefo:
            out["notes"].append("No batched item with >=2 batches and stock found")
            print(json.dumps(out, ensure_ascii=True, indent=2, default=str))
            return

        so_name, so_created = _ensure_sales_order(TARGET_CUSTOMER, fefo["item_code"], TARGET_WAREHOUSE)
        dn_name, dn_created = _find_or_create_delivery_note(so_name)

        frappe.db.commit()

        out.update(
            {
                "prepared": True,
                "warehouse": TARGET_WAREHOUSE,
                "customer": TARGET_CUSTOMER,
                "item_code": fefo["item_code"],
                "oldest_batch": fefo["oldest"],
                "newest_batch": fefo["newest"],
                "sales_order": so_name,
                "sales_order_created": so_created,
                "delivery_note": dn_name,
                "delivery_note_created": dn_created,
                "item_marked_sales_temporarily": item_marked_sales_temporarily,
            }
        )
        print(json.dumps(out, ensure_ascii=True, indent=2, default=str))
    finally:
        frappe.destroy()


if __name__ == "__main__":
    main()
