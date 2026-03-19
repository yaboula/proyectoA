warehouse = frappe.db.get_value("Warehouse", {"company": "Peintures du Maroc SARL", "is_group": 0}, "name")
print(f"Warehouse encontrado: {warehouse}")

for item_code in ["PT-TEST-B3-ITEM-A", "PT-TEST-B3-ITEM-B"]:
    item = frappe.get_doc("Item", item_code)
    defaults_pdm = [r for r in item.item_defaults if r.company == "Peintures du Maroc SARL"]
    if not defaults_pdm:
        row = item.append("item_defaults", {})
        row.company = "Peintures du Maroc SARL"
        row.default_warehouse = warehouse
        item.save(ignore_permissions=True)
        print(f"  [SET] {item_code} -> {warehouse}")
    elif not defaults_pdm[0].default_warehouse:
        defaults_pdm[0].default_warehouse = warehouse
        item.save(ignore_permissions=True)
        print(f"  [UPDATE] {item_code} -> {warehouse}")
    else:
        print(f"  [OK] {item_code} -> {defaults_pdm[0].default_warehouse}")

frappe.db.commit()
print("DONE — ahora recrea el Sales Order en la UI")
