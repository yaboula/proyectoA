"""Fix Item Prices for B3 test items in Tarif Droguerie."""
import frappe
from frappe.utils import now_datetime

price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Tarif Droguerie"
print("Active price list:", price_list)

# Check what Item Price records exist
for code in ["PT-TEST-B3-ITEM-A", "PT-TEST-B3-ITEM-B"]:
    rows = frappe.db.sql(
        "SELECT name, price_list, price_list_rate, selling FROM `tabItem Price` WHERE item_code=%s",
        code, as_dict=True
    )
    print(f"\n{code} existing prices:")
    for r in rows:
        print(f"  {r.name}: list={r.price_list} rate={r.price_list_rate} selling={r.selling}")

# Fix: delete any bad 0-rate records and insert correct ones
prices = {
    "PT-TEST-B3-ITEM-A": 120.0,
    "PT-TEST-B3-ITEM-B": 180.0,
}

now = now_datetime()
for code, rate in prices.items():
    # Delete existing records for this price_list (including bad ones)
    frappe.db.sql(
        "DELETE FROM `tabItem Price` WHERE item_code=%s AND price_list=%s",
        (code, price_list)
    )
    # Insert fresh
    ip_name = frappe.generate_hash(length=10)
    frappe.db.sql("""
        INSERT INTO `tabItem Price`
          (name, item_code, price_list, price_list_rate, selling, currency,
           creation, modified, owner, modified_by, docstatus)
        VALUES (%s, %s, %s, %s, 1, 'MAD', %s, %s, 'Administrator', 'Administrator', 0)
    """, (ip_name, code, price_list, rate, now, now))
    print(f"[OK] {code} -> {rate} MAD in {price_list}")

frappe.db.commit()

# Final verify
print("\n=== Final check ===")
for code in ["PT-TEST-B3-ITEM-A", "PT-TEST-B3-ITEM-B"]:
    row = frappe.db.sql(
        "SELECT price_list_rate FROM `tabItem Price` WHERE item_code=%s AND price_list=%s AND selling=1",
        (code, price_list), as_dict=True
    )
    print(f"  {code}: {row[0].price_list_rate if row else 'STILL MISSING'}")
print("DONE")
