import frappe

user_email = "comercial.b3@gcma.local"
roles_to_add = ["Accounts User", "Sales Manager"]

for role_name in roles_to_add:
    exists = frappe.db.exists("Has Role", {"parent": user_email, "role": role_name})
    if not exists:
        frappe.db.sql(
            "INSERT INTO `tabHas Role` (name, creation, modified, modified_by, owner, parent, parentfield, parenttype, role) "
            "VALUES (%s, NOW(), NOW(), 'Administrator', 'Administrator', %s, 'roles', 'User', %s)",
            (frappe.generate_hash(length=10), user_email, role_name)
        )
        print("INSERTED role:", role_name, "for", user_email)
    else:
        print("EXISTS:", role_name)

frappe.db.commit()
print("DONE")
