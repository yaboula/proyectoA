import frappe

# 1. Crear Modes of Payment si no existen
modos = ["Espece", "Cheque", "Virement", "Efectivo"]
for modo in modos:
    if not frappe.db.exists("Mode of Payment", modo):
        doc = frappe.new_doc("Mode of Payment")
        doc.mode_of_payment = modo
        doc.type = "Cash" if modo in ["Espece", "Efectivo"] else "Bank"
        try:
            doc.insert(ignore_permissions=True)
            print("CREATED Mode of Payment:", modo)
        except Exception as e:
            print("WARN MOP:", modo, str(e)[:80])
    else:
        print("EXISTS Mode of Payment:", modo)

frappe.db.commit()

# 2. Verificar columnas de tabLoyalty Point Entry
try:
    result = frappe.db.sql("SHOW COLUMNS FROM `tabLoyalty Point Entry`", as_dict=True)
    print("\nLoyalty Point Entry columns:")
    for row in result:
        print(" -", row.get("Field"))
except Exception as e:
    print("LPE schema error:", str(e)[:100])

print("DONE")
