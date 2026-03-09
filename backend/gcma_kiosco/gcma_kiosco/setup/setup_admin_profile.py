"""
GCMA — Setup del perfil Administrator para acceso al Desk.

Ejecutar DENTRO del contenedor backend:
    bench --site frontend execute gcma_kiosco.setup.setup_admin_profile.run

Qué hace:
  1. Marca el Setup Wizard como completado (evita el wizard en primer login).
  2. Configura el perfil del usuario Administrator (nombre, idioma, zona horaria).
  3. Garantiza que Administrator tiene el Role "System Manager".
  4. Asigna acceso a los módulos relevantes del proyecto (Manufacturing, Stock,
     Buying, Selling, Accounts, HR) para poder ver Work Orders, Stock Entries,
     BOM, Employees, etc.
  5. Imprime un resumen de verificación.

IMPORTANTE: idempotente — puede ejecutarse varias veces sin daño.
"""

import frappe


def run():
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║       GCMA — Setup Perfil Administrator              ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    _mark_setup_complete()
    _configure_system_settings()
    _configure_administrator_user()
    _assign_roles()
    _enable_modules()
    _set_homepage()

    frappe.db.commit()

    print("\n✅  Setup completado. Accede en: http://localhost:8080")
    print("    Usuario:   Administrator")
    print("    Password:  admin")
    print("")


# ─────────────────────────────────────────────────────────────────────────────

def _mark_setup_complete():
    """Marca el Setup Wizard de ERPNext como ya completado."""
    print("── 1/6  Marcando Setup Wizard como completado…")
    frappe.db.set_single_value("System Settings", "setup_complete", 1)
    # Algunas versiones de ERPNext usan este flag adicional (ignorar si no existe)
    try:
        frappe.db.set_single_value("System Settings", "is_setup_complete", 1)
    except Exception:
        pass
    print("   ✓ Setup Wizard: completado")


def _configure_system_settings():
    """Configura país, moneda y zona horaria del sistema."""
    print("── 2/6  Configurando System Settings…")
    settings = frappe.get_single("System Settings")
    settings.country = "Morocco"
    settings.language = "en"
    settings.time_zone = "Africa/Casablanca"
    settings.date_format = "dd-mm-yyyy"
    settings.currency = "MAD"
    settings.float_precision = 2
    settings.save(ignore_permissions=True)
    print("   ✓ País: Morocco | Moneda: MAD | TZ: Africa/Casablanca")


def _configure_administrator_user():
    """Actualiza el perfil del usuario Administrator."""
    print("── 3/6  Configurando usuario Administrator…")
    user = frappe.get_doc("User", "Administrator")
    user.first_name = "System"
    user.last_name = "Administrator"
    user.full_name = "System Administrator"
    user.language = "en"
    user.time_zone = "Africa/Casablanca"
    user.send_welcome_email = 0
    # Asegurar que no está bloqueado
    user.enabled = 1
    user.save(ignore_permissions=True)
    print("   ✓ Administrator: nombre y zona horaria configurados")


def _assign_roles():
    """Garantiza que Administrator tiene los roles clave."""
    print("── 4/6  Verificando roles de Administrator…")
    user = frappe.get_doc("User", "Administrator")

    roles_needed = [
        "System Manager",
        "Manufacturing Manager",
        "Manufacturing User",
        "Stock Manager",
        "Stock User",
        "Accounts Manager",
        "HR Manager",
    ]

    existing_roles = {r.role for r in user.get("roles", [])}
    added = []

    for role in roles_needed:
        if role not in existing_roles:
            if frappe.db.exists("Role", role):
                user.append("roles", {"role": role})
                added.append(role)

    if added:
        user.save(ignore_permissions=True)
        print(f"   + Roles añadidos: {', '.join(added)}")
    else:
        print("   ✓ Todos los roles ya asignados")


def _enable_modules():
    """Activa los módulos ERPNext necesarios para el proyecto."""
    print("── 5/6  Activando módulos…")

    modules = [
        "Manufacturing",
        "Stock",
        "Buying",
        "Selling",
        "Accounts",
        "HR",
        "CRM",
    ]

    # Verificar si existe el doctype "Module Def" para habilitarlos
    for mod in modules:
        if frappe.db.exists("Module Def", mod):
            frappe.db.set_value("Module Def", mod, "app_name", "erpnext")

    # Deshabilitar el bloqueo de módulos para Administrator (si aplica)
    if frappe.db.exists("doctype", "User Module Def"):
        frappe.db.delete("User Module Def", {"user": "Administrator"})

    print(f"   ✓ Módulos: {', '.join(modules)}")


def _set_homepage():
    """Configura la home page del desk para evitar redirects."""
    print("── 6/6  Configurando home page…")
    try:
        ws = frappe.get_single("Website Settings")
        ws.home_page = "desk"
        ws.save(ignore_permissions=True)
    except Exception:
        pass

    # Borrar caché para aplicar cambios inmediatamente
    frappe.clear_cache()
    print("   ✓ Home page → desk | Caché limpiada")
