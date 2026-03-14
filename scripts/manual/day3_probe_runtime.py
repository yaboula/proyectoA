import json
from datetime import date

import frappe

SITE = "frontend"
SITES_PATH = "/home/frappe/frappe-bench/sites"


def rowdicts(rows):
    return [dict(r) for r in rows]


def main() -> None:
    frappe.init(site=SITE, sites_path=SITES_PATH)
    frappe.connect()
    try:
        result = {}

        result["warehouses"] = rowdicts(
            frappe.db.sql(
                """
                select name
                from `tabWarehouse`
                where disabled = 0
                order by name asc
                limit 10
                """,
                as_dict=True,
            )
        )

        result["pending_delivery_notes"] = rowdicts(
            frappe.db.sql(
                """
                select name, customer, posting_date, docstatus, status
                from `tabDelivery Note`
                where docstatus in (0, 1)
                  and ifnull(status, '') not in ('Completed', 'Closed')
                order by posting_date desc, modified desc
                limit 10
                """,
                as_dict=True,
            )
        )

        result["fefo_sales_order_candidates"] = rowdicts(
            frappe.db.sql(
                """
                select distinct so.name as sales_order, soi.item_code, soi.warehouse, so.set_warehouse
                from `tabSales Order` so
                inner join `tabSales Order Item` soi on soi.parent = so.name
                where so.docstatus = 1
                  and ifnull(so.status, '') not in ('Closed', 'Completed', 'Cancelled')
                  and exists (
                    select 1 from `tabBatch` b where b.item = soi.item_code and ifnull(b.disabled, 0) = 0
                  )
                order by so.modified desc
                limit 20
                """,
                as_dict=True,
            )
        )

        # Helpful fallback: any batched item with >=2 active batches.
        result["batched_items_with_multiple_batches"] = rowdicts(
            frappe.db.sql(
                """
                select b.item as item_code, count(*) as total_batches
                from `tabBatch` b
                where ifnull(b.disabled, 0) = 0
                group by b.item
                having count(*) >= 2
                order by total_batches desc, b.item asc
                limit 20
                """,
                as_dict=True,
            )
        )

        print(json.dumps(result, ensure_ascii=True, indent=2, default=str))
    finally:
        frappe.destroy()


if __name__ == "__main__":
    main()
