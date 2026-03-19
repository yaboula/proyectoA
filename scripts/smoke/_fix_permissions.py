"""
Fix permissions for comercial.b3@gcma.local:
1. Check if Accounts User role has write permission on Payment Entry
2. Properly assign Accounts User role to the user (reload user_permissions cache)
3. Clear permission cache
"""
import frappe

user_email = "comercial.b3@gcma.local"

# 1. Check current roles in DB
rows = frappe.db.sql(
    "SELECT role FROM `tabHas Role` WHERE parent=%s",
    user_email
)
print("Current roles in DB:", [r[0] for r in rows])

# 2. Check if Accounts User has write on Payment Entry
pe_perms = frappe.db.sql(
    "SELECT role, `write`, `create` FROM `tabDocPerm` "
    "WHERE parent='Payment Entry' AND role='Accounts User'",
    as_dict=True
)
print("DocPerm for Accounts User on Payment Entry:", pe_perms)

# 3. Check all roles with write on Payment Entry
all_perms = frappe.db.sql(
    "SELECT role, `write`, `create` FROM `tabDocPerm` "
    "WHERE parent='Payment Entry' AND (`write`=1 OR `create`=1)",
    as_dict=True
)
print("All roles with write/create on Payment Entry:", all_perms)

# 4. Ensure the role is properly saved via Frappe ORM (not just SQL)
# First check if it exists
user_doc = frappe.get_doc("User", user_email)
existing_roles = [r.role for r in user_doc.roles]
print("User roles via ORM:", existing_roles)

roles_to_add = ["Accounts User", "Sales Manager"]
changed = False
for role_name in roles_to_add:
    if role_name not in existing_roles:
        user_doc.append("roles", {"role": role_name})
        print(f"Adding role: {role_name}")
        changed = True
    else:
        print(f"Role already present: {role_name}")

if changed:
    user_doc.save(ignore_permissions=True)
    frappe.db.commit()
    print("Saved user with new roles")

# 5. Clear the permissions cache for this user
frappe.clear_cache(user=user_email)
print("Cache cleared for user")

# 6. Now test has_permission for this user
frappe.set_user(user_email)
result = frappe.has_permission("Payment Entry", ptype="create", throw=False)
print(f"has_permission('Payment Entry', 'create') for {user_email}: {result}")
frappe.set_user("Administrator")

print("DONE - permissions should be fixed")
