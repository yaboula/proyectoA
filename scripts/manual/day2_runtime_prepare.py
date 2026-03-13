import frappe

SITE = "frontend"
MANAGER_USER = "qa.manager.block3@gcma.local"
PORTAL_USER = "qa.portal.block3@gcma.local"
PORTAL_CUSTOMER = "Droguerie Atlas"
MANAGER_ROLES = ["System Manager", "Sales Manager", "Accounts Manager"]


def ensure_role(user: str, role: str) -> bool:
    exists = frappe.db.exists("Has Role", {"parent": user, "role": role, "parenttype": "User"})
    if exists:
        return False

    frappe.get_doc(
        {
            "doctype": "Has Role",
            "parent": user,
            "parentfield": "roles",
            "parenttype": "User",
            "role": role,
        }
    ).insert(ignore_permissions=True)
    return True


def ensure_user_permission(user: str, customer: str) -> bool:
    exists = frappe.db.exists(
        "User Permission",
        {
            "user": user,
            "allow": "Customer",
            "for_value": customer,
        },
    )
    if exists:
        return False

    frappe.get_doc(
        {
            "doctype": "User Permission",
            "user": user,
            "allow": "Customer",
            "for_value": customer,
            "applicable_for": "",
            "apply_to_all_doctypes": 1,
            "hide_descendants": 0,
            "is_default": 1,
        }
    ).insert(ignore_permissions=True)
    return True


def main() -> None:
    frappe.init(site=SITE, sites_path="/home/frappe/frappe-bench/sites")
    frappe.connect()
    created_roles = []
    try:
        for role in MANAGER_ROLES:
            if ensure_role(MANAGER_USER, role):
                created_roles.append(role)

        up_created = ensure_user_permission(PORTAL_USER, PORTAL_CUSTOMER)
        frappe.db.commit()

        print("manager_roles_added=", created_roles)
        print("portal_user_permission_added=", up_created)
    finally:
        frappe.destroy()


if __name__ == "__main__":
    main()
