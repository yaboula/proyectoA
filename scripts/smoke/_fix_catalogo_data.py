"""Fix catalogue data: prices + stock for B3 test items."""
import frappe
from frappe.utils import today, now_datetime

price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Tarif Droguerie"
company = frappe.db.get_single_value("Global Defaults", "default_company") or "Peintures du Maroc SARL"
# Use the expedition/picking warehouse where seed put stock
warehouse = "Expedicion / Picking - PDM"
# Fallback to first non-group warehouse if above doesn't exist
if not frappe.db.exists("Warehouse", warehouse):
    wh_list = frappe.db.sql(
        "SELECT name FROM `tabWarehouse` WHERE company=%s AND is_group=0 ORDER BY name LIMIT 1",
        company
    )
    warehouse = wh_list[0][0] if wh_list else None

print(f"Price list: {price_list}")
print(f"Warehouse: {warehouse}")

items_to_fix = [
    {"code": "PT-TEST-B3-ITEM-A", "price": 120.0, "qty": 50},
    {"code": "PT-TEST-B3-ITEM-B", "price": 180.0, "qty": 50},
]

for item_data in items_to_fix:
    code = item_data["code"]
    price = item_data["price"]
    qty = item_data["qty"]

    # 1. Add Item Price in active price list
    existing = frappe.db.exists("Item Price", {"item_code": code, "price_list": price_list, "selling": 1})
    if existing:
        frappe.db.set_value("Item Price", existing, "price_list_rate", price)
        print(f"[UPDATE] {code} price -> {price} MAD in {price_list}")
    else:
        ip = frappe.new_doc("Item Price")
        ip.item_code = code
        ip.price_list = price_list
        ip.price_list_rate = price
        ip.selling = 1
        ip.currency = "MAD"
        ip.insert(ignore_permissions=True)
        print(f"[CREATE] {code} price -> {price} MAD in {price_list}")

    # 2. Check bin stock
    bin_qty_rows = frappe.db.sql(
        "SELECT SUM(actual_qty) as total FROM `tabBin` WHERE item_code=%s", code, as_dict=True
    )
    current_qty = float(bin_qty_rows[0].total or 0) if bin_qty_rows else 0.0
    print(f"  Current bin total qty: {current_qty}")

    if current_qty < 1 and warehouse:
        # Try Stock Reconciliation
        try:
            sr = frappe.new_doc("Stock Reconciliation")
            sr.company = company
            sr.posting_date = today()
            sr.posting_time = "08:00:00"
            sr.purpose = "Opening Stock"
            sr.append("items", {
                "item_code": code,
                "warehouse": warehouse,
                "qty": qty,
                "valuation_rate": round(price * 0.6, 2),
            })
            sr.insert(ignore_permissions=True)
            sr.submit()
            frappe.db.commit()
            print(f"  [OK] Stock Reconciliation: {qty} units in {warehouse}")
        except Exception as e1:
            print(f"  [WARN] SR failed: {str(e1)[:120]}")
            frappe.db.rollback()
            # Direct bin upsert
            try:
                existing_bin = frappe.db.exists("Bin", {"item_code": code, "warehouse": warehouse})
                now = now_datetime()
                if existing_bin:
                    frappe.db.sql(
                        "UPDATE `tabBin` SET actual_qty=%s, projected_qty=%s WHERE item_code=%s AND warehouse=%s",
                        (qty, qty, code, warehouse)
                    )
                else:
                    bin_name = frappe.generate_hash(length=10)
                    frappe.db.sql(
                        "INSERT INTO `tabBin` (name, item_code, warehouse, actual_qty, projected_qty, "
                        "creation, modified, owner, modified_by) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,'Administrator','Administrator')",
                        (bin_name, code, warehouse, qty, qty, now, now)
                    )
                frappe.db.commit()
                print(f"  [FALLBACK] Direct bin update: {code} = {qty}")
            except Exception as e2:
                print(f"  [ERROR] Bin update failed: {str(e2)[:120]}")

frappe.db.commit()
print("\n=== Verification ===")
for item_data in items_to_fix:
    code = item_data["code"]
    prow = frappe.db.sql(
        "SELECT price_list_rate FROM `tabItem Price` WHERE item_code=%s AND price_list=%s AND selling=1",
        (code, price_list), as_dict=True
    )
    brow = frappe.db.sql(
        "SELECT warehouse, actual_qty FROM `tabBin` WHERE item_code=%s AND actual_qty > 0", code, as_dict=True
    )
    pval = prow[0].price_list_rate if prow else "MISSING"
    bval = [(r.warehouse, r.actual_qty) for r in brow]
    print(f"  {code}: price={pval} | bins={bval}")
print("DONE")
