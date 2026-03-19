"""Diagnose catalogue stock and prices for B3 test items."""
import frappe

items = ["PT-TEST-B3-ITEM-A", "PT-TEST-B3-ITEM-B", "PT-PIN-BLC-MAT-20L"]

print("=== tabBin stock ===")
for item in items:
    rows = frappe.db.sql(
        "SELECT warehouse, actual_qty FROM `tabBin` WHERE item_code=%s",
        item, as_dict=True
    )
    print(f"{item}:")
    if rows:
        for r in rows:
            print(f"  wh={r.warehouse} qty={r.actual_qty}")
    else:
        print("  NO BIN RECORDS")

print("\n=== Item Price ===")
price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"
print(f"Active price list: {price_list}")
for item in items:
    rows = frappe.db.sql(
        "SELECT price_list, price_list_rate, selling FROM `tabItem Price` WHERE item_code=%s",
        item, as_dict=True
    )
    print(f"{item}:")
    if rows:
        for r in rows:
            print(f"  list={r.price_list} rate={r.price_list_rate} selling={r.selling}")
    else:
        print("  NO PRICE RECORDS")

print("\n=== Stock Ledger (last 3 entries per item) ===")
for item in items:
    rows = frappe.db.sql(
        "SELECT warehouse, actual_qty_after_transaction, posting_date "
        "FROM `tabStock Ledger Entry` WHERE item_code=%s ORDER BY creation DESC LIMIT 3",
        item, as_dict=True
    )
    print(f"{item}:")
    for r in rows:
        print(f"  wh={r.warehouse} qty_after={r.actual_qty_after_transaction} date={r.posting_date}")
