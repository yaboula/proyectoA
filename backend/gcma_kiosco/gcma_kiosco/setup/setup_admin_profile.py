"""
GCMA — Crea usuario de proyecto dedicado para acceso al Desk ERPNext.

Ejecutar DENTRO del contenedor backend:
    bench --site frontend execute gcma_kiosco.setup.setup_admin_profile.run

Crea el usuario:
    Email:    gcma.dev@gcma.ma
    Password: Gcma2026!
    Rol:      System Manager + Manufacturing Manager + Stock Manager + HR Manager

Este usuario es independiente de Administrator y tiene acceso completo
a los módulos del proyecto: Work Orders, BOM, Stock, Employees, etc.

IMPORTANTE: idempotente — puede ejecutarse varias veces sin daño.
"""

import frappe

# ── Credenciales del usuario de proyecto ──────────────────────────────────────
USER_EMAIL    = "gcma.dev@gcma.ma"
USER_PASSWORD = "Gcma2026!"
USER_ROLES = [
    "System Manager",
    "Manufacturing Manager",
    "Manufacturing User",
    "Stock Manager",
    "Stock User",
    "Accounts Manager",
    "HR Manager",
]
# ─────────────────────────────────────────────────────────────────────────────


def run():
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║       GCMA — Creación de Usuario de Proyecto         ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    _mark_setup_complete()
    _create_gcma_user()
    _set_password()
    _assign_roles()

    frappe.db.commit()
    frappe.clear_cache()

    print("\n✅  Usuario listo. Accede en: http://localhost:8080")
    print(f"    Email:     {USER_EMAIL}")
    print(f"    Password:  {USER_PASSWORD}")
    print("")


# ─────────────────────────────────────────────────────────────────────────────

def _mark_setup_complete():
    """Evita que aparezca el Setup Wizard al entrar."""
    print("── 1/4  Marcando Setup Wizard como completado…")
    # System Settings (Single doctype)
    frappe.db.set_single_value("System Settings", "setup_complete", 1)
    # tabDefaultValue — es lo que ERPNext lee en el boot session
    frappe.db.set_default("setup_complete", "1")
    frappe.db.set_default("desktop:home_page", "Workspace")
    try:
        ws = frappe.get_single("Website Settings")
        ws.home_page = "desk"
        ws.save(ignore_permissions=True)
    except Exception:
        pass
    frappe.db.commit()
    frappe.clear_cache()
    print("   ✓ Setup Wizard desactivado")


def _create_gcma_user():
    """Crea el usuario gcma.dev@gcma.ma si no existe."""
    print(f"── 2/4  Creando usuario {USER_EMAIL}…")

    if frappe.db.exists("User", USER_EMAIL):
        print(f"   ✓ Usuario ya existe — actualizando perfil")
        user = frappe.get_doc("User", USER_EMAIL)
    else:
        user = frappe.new_doc("User")
        user.email = USER_EMAIL

    user.first_name = "GCMA"
    user.last_name = "Dev"
    user.full_name = "GCMA Dev"
    user.username = "gcma_dev"
    user.language = "en"
    user.time_zone = "Africa/Casablanca"
    user.send_welcome_email = 0
    user.enabled = 1
    user.user_type = "System User"
    user.save(ignore_permissions=True)
    print(f"   ✓ Usuario {USER_EMAIL} guardado")


def _set_password():
    """Establece la contraseña del usuario."""
    print("── 3/4  Estableciendo contraseña…")
    from frappe.utils.password import update_password
    update_password(USER_EMAIL, USER_PASSWORD)
    print(f"   ✓ Password configurada")


def _assign_roles():
    """Asigna los roles de proyecto al usuario."""
    print("── 4/4  Asignando roles…")
    user = frappe.get_doc("User", USER_EMAIL)

    existing_roles = {r.role for r in user.get("roles", [])}
    added = []

    for role in USER_ROLES:
        if role not in existing_roles and frappe.db.exists("Role", role):
            user.append("roles", {"role": role})
            added.append(role)

    if added:
        user.save(ignore_permissions=True)
        print(f"   + Roles asignados: {', '.join(added)}")
    else:
        print(f"   ✓ Roles ya asignados: {', '.join(USER_ROLES)}")
