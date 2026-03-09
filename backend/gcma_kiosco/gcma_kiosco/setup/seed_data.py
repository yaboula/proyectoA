"""
GCMA — Seed Data para PoC Sandbox (Sección 3.1 de la Data Foundation).

Ejecutar con:
    bench execute gcma_kiosco.setup.seed_data.run

Idempotente: cada función verifica si el registro existe antes de crearlo.
Orden de ejecución: UoMs → Companies → Warehouses → Item Groups → Items →
                     Suppliers → Customers → Price Lists → Item Prices →
                     QI Templates → BOM.

IMPORTANTE: Este script carga SOLO la empresa PDM (Pinturas) para el PoC.
            PEM se cargará en su propio script de seed (seed_data_pem.py)
            para mantener paridad garantizada (Guardrail G2).
"""

import frappe
from frappe.utils import today, add_days


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _exists(doctype: str, name: str) -> bool:
    """Verifica existencia de un registro por name."""
    return frappe.db.exists(doctype, name)


def _get_or_create(doctype: str, name: str, **fields):
    """Crea un documento si no existe.  Devuelve el name."""
    if _exists(doctype, name):
        frappe.logger().info(f"  ✓ {doctype} '{name}' ya existe — skip.")
        return name
    doc = frappe.new_doc(doctype)
    doc.update(fields)
    # Para doctypes con name auto, forzamos el name si coincide
    if hasattr(doc, "name") and "name" not in fields:
        pass  # Se nombra por naming_series o campo propio
    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
    frappe.logger().info(f"  + {doctype} '{doc.name}' creado.")
    return doc.name


# ═══════════════════════════════════════════════════════════════════════════
# 1. UoMs
# ═══════════════════════════════════════════════════════════════════════════

def create_uoms():
    """Crea las UoMs custom que no existen en ERPNext por defecto."""
    print("\n──── 1/15  Unidades de Medida ────")
    uoms = [
        # (name, must_be_whole_number)
        ("Kg", 0),
        ("g", 0),
        ("Litre", 0),
        ("Nos", 1),
        ("Bidon 200L", 1),
        ("Bidon 60L", 1),
        ("Sac 25Kg", 1),
        ("Palette", 1),
    ]
    for uom_name, whole in uoms:
        if not _exists("UOM", uom_name):
            doc = frappe.new_doc("UOM")
            doc.uom_name = uom_name
            doc.must_be_whole_number = whole
            doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
            print(f"  + UoM '{uom_name}' creada.")
        else:
            print(f"  ✓ UoM '{uom_name}' ya existe.")


# ═══════════════════════════════════════════════════════════════════════════
# 1b. PREREQUISITOS ERPNext (datos base que normalmente crea el Setup Wizard)
# ═══════════════════════════════════════════════════════════════════════════

def create_erpnext_prerequisites():
    """Crea datos base que ERPNext necesita y que el Setup Wizard no creó."""
    print("\n──── 1b/15  Prerequisitos ERPNext (base data) ────")

    # Warehouse Types
    for wtype in ["Transit"]:
        if not _exists("Warehouse Type", wtype):
            doc = frappe.new_doc("Warehouse Type")
            doc.name = wtype
            doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
            print(f"  + Warehouse Type '{wtype}' creado.")
        else:
            print(f"  ✓ Warehouse Type '{wtype}' ya existe.")

    # Root Item Group — "All Item Groups"
    if not _exists("Item Group", "All Item Groups"):
        root = frappe.new_doc("Item Group")
        root.item_group_name = "All Item Groups"
        root.is_group = 1
        root.insert(ignore_permissions=True, ignore_if_duplicate=True)
        print("  + Item Group raíz 'All Item Groups' creado.")
    else:
        print("  ✓ Item Group raíz 'All Item Groups' ya existe.")

    # Stock Settings — para que Stock Entry funcione
    if frappe.db.exists("DocType", "Stock Settings"):
        ss = frappe.get_doc("Stock Settings")
        if not ss.stock_uom:
            ss.stock_uom = "Kg"
            ss.save(ignore_permissions=True)
            print("  + Stock Settings: stock_uom = Kg")
        else:
            print(f"  ✓ Stock Settings: stock_uom = {ss.stock_uom}")

    # Root Customer Group
    if not _exists("Customer Group", "All Customer Groups"):
        doc = frappe.new_doc("Customer Group")
        doc.customer_group_name = "All Customer Groups"
        doc.is_group = 1
        doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
        print("  + Customer Group raíz 'All Customer Groups' creado.")
    else:
        print("  ✓ Customer Group raíz ya existe.")

    # Root Territory
    if not _exists("Territory", "All Territories"):
        doc = frappe.new_doc("Territory")
        doc.territory_name = "All Territories"
        doc.is_group = 1
        doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
        print("  + Territory raíz 'All Territories' creado.")
    else:
        print("  ✓ Territory raíz ya existe.")

    # Root Supplier Group — si no existe
    if not _exists("Supplier Group", "All Supplier Groups"):
        doc = frappe.new_doc("Supplier Group")
        doc.supplier_group_name = "All Supplier Groups"
        doc.is_group = 1
        doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
        print("  + Supplier Group raíz 'All Supplier Groups' creado.")
    else:
        print("  ✓ Supplier Group raíz ya existe.")

    # Currencies MAD y EUR
    for cur in ["MAD", "EUR"]:
        if not _exists("Currency", cur):
            doc = frappe.new_doc("Currency")
            doc.currency_name = cur
            doc.enabled = 1
            doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
            print(f"  + Currency '{cur}' creada.")
        else:
            print(f"  ✓ Currency '{cur}' ya existe.")

    # Genders — requeridos por Employee
    for g in ["Male", "Female", "Other"]:
        if not _exists("Gender", g):
            doc = frappe.new_doc("Gender")
            doc.gender = g
            doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
            print(f"  + Gender '{g}' creado.")
        else:
            print(f"  ✓ Gender '{g}' ya existe.")

    # Designation — para Manufacturing roles (puede no existir en v16 sin HRMS)
    if frappe.db.exists("DocType", "Designation"):
        for d_name in ["Opérateur", "Chef de Ligne", "Responsable QC"]:
            if not _exists("Designation", d_name):
                try:
                    doc = frappe.new_doc("Designation")
                    doc.designation = d_name
                    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
                    print(f"  + Designation '{d_name}' creada.")
                except Exception:
                    # Si el schema cambió, no bloquear el seed
                    print(f"  ⚠ Designation '{d_name}' no se pudo crear (no bloquea).")

    # Stock Entry Types — requeridos por Stock Entry
    stock_entry_types = [
        {"name": "Material Receipt", "purpose": "Material Receipt"},
        {"name": "Material Issue", "purpose": "Material Issue"},
        {"name": "Material Transfer", "purpose": "Material Transfer"},
        {"name": "Manufacture", "purpose": "Manufacture"},
        {"name": "Repack", "purpose": "Repack"},
        {"name": "Send to Subcontractor", "purpose": "Send to Subcontractor"},
        {"name": "Material Transfer for Manufacture", "purpose": "Material Transfer for Manufacture"},
        {"name": "Material Consumption for Manufacture", "purpose": "Material Consumption for Manufacture"},
    ]
    for stype in stock_entry_types:
        if not _exists("Stock Entry Type", stype["name"]):
            doc = frappe.new_doc("Stock Entry Type")
            doc.name = stype["name"]
            doc.purpose = stype["purpose"]
            doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
            print(f"  + Stock Entry Type '{stype['name']}' creado.")
        else:
            print(f"  ✓ Stock Entry Type '{stype['name']}' ya existe.")

    # Fiscal Year — requerido para submit de Stock Entry
    import datetime
    current_year = datetime.date.today().year
    for yr in [current_year, current_year + 1]:
        fy_name = str(yr)
        if not _exists("Fiscal Year", fy_name):
            fy = frappe.new_doc("Fiscal Year")
            fy.year = fy_name
            fy.year_start_date = f"{yr}-01-01"
            fy.year_end_date = f"{yr}-12-31"
            fy.insert(ignore_permissions=True, ignore_if_duplicate=True)
            print(f"  + Fiscal Year '{fy_name}' creado.")
        else:
            print(f"  ✓ Fiscal Year '{fy_name}' ya existe.")

    frappe.db.commit()


# ═══════════════════════════════════════════════════════════════════════════
# 2. COMPANIES  (GCMA padre + PDM hija)
# ═══════════════════════════════════════════════════════════════════════════

def create_companies():
    """Crea la empresa padre GCMA y la empresa operativa PDM."""
    print("\n──── 2/15  Empresas ────")

    # -- Empresa padre (solo consolidación) --
    if not _exists("Company", "Groupe Chimique MA"):
        parent = frappe.new_doc("Company")
        parent.company_name = "Groupe Chimique MA"
        parent.abbr = "GCMA"
        parent.default_currency = "MAD"
        parent.country = "Morocco"
        parent.is_group = 1
        parent.insert(ignore_permissions=True)
        print("  + Company 'Groupe Chimique MA' creada.")
    else:
        print("  ✓ Company 'Groupe Chimique MA' ya existe.")

    # Asegurar que la empresa padre sea grupo (necesario si ya existía sin is_group)
    gcma = frappe.get_doc("Company", "Groupe Chimique MA")
    if not gcma.is_group:
        gcma.is_group = 1
        gcma.save(ignore_permissions=True)
        print("  ↻ Company 'Groupe Chimique MA' actualizada a is_group=1.")

    # -- Empresa operativa PDM --
    if not _exists("Company", "Peintures du Maroc SARL"):
        pdm = frappe.new_doc("Company")
        pdm.company_name = "Peintures du Maroc SARL"
        pdm.abbr = "PDM"
        pdm.default_currency = "MAD"
        pdm.country = "Morocco"
        pdm.parent_company = "Groupe Chimique MA"
        pdm.insert(ignore_permissions=True)
        print("  + Company 'Peintures du Maroc SARL' creada.")
    else:
        print("  ✓ Company 'Peintures du Maroc SARL' ya existe.")


# ═══════════════════════════════════════════════════════════════════════════
# 3. WAREHOUSES  (6 nodos lógicos para PDM)
# ═══════════════════════════════════════════════════════════════════════════

def create_warehouses():
    """Crea el árbol de 6 almacenes lógicos de PDM bajo su nodo Company."""
    print("\n──── 3/15  Almacenes PDM ────")
    company = "Peintures du Maroc SARL"
    abbr = "PDM"

    warehouses = [
        f"Cuarentena MP - {abbr}",
        f"Materia Prima Aprobada - {abbr}",
        f"Planta Mezclas WIP - {abbr}",
        f"Cuarentena PT - {abbr}",
        f"Producto Terminado - {abbr}",
        f"Expedición / Picking - {abbr}",
    ]

    # Nodo padre — ERPNext crea "All Warehouses - PDM" automáticamente al crear Company
    parent_wh = f"All Warehouses - {abbr}"

    for wh_name in warehouses:
        if not _exists("Warehouse", wh_name):
            wh = frappe.new_doc("Warehouse")
            wh.warehouse_name = wh_name.replace(f" - {abbr}", "")
            wh.company = company
            wh.parent_warehouse = parent_wh
            wh.is_group = 0
            wh.insert(ignore_permissions=True, ignore_if_duplicate=True)
            print(f"  + Warehouse '{wh_name}' creado.")
        else:
            print(f"  ✓ Warehouse '{wh_name}' ya existe.")


# ═══════════════════════════════════════════════════════════════════════════
# 4. ITEM GROUPS  (Árbol jerárquico)
# ═══════════════════════════════════════════════════════════════════════════

def create_item_groups():
    """Crea la jerarquía de Item Groups de 3 niveles."""
    print("\n──── 4/15  Item Groups ────")

    # Nivel 1 — bajo All Item Groups
    level_1 = [
        "Materias Primas",
        "Material de Envasado",
        "Producto Terminado",
        "Subproducto / Scrap",
        "Consumibles de Planta",
    ]

    for name in level_1:
        if not _exists("Item Group", name):
            ig = frappe.new_doc("Item Group")
            ig.item_group_name = name
            ig.parent_item_group = "All Item Groups"
            ig.is_group = 1
            ig.insert(ignore_permissions=True, ignore_if_duplicate=True)
            print(f"  + Item Group L1 '{name}' creado.")
        else:
            print(f"  ✓ Item Group L1 '{name}' ya existe.")

    # Nivel 2 — MP
    mp_children = [
        "Resinas y Ligantes",
        "Pigmentos y Cargas",
        "Solventes y Diluyentes",
        "Tensioactivos y Surfactantes",
        "Perfumes y Colorantes",
        "Aditivos Químicos",
    ]
    for name in mp_children:
        if not _exists("Item Group", name):
            ig = frappe.new_doc("Item Group")
            ig.item_group_name = name
            ig.parent_item_group = "Materias Primas"
            ig.is_group = 0
            ig.insert(ignore_permissions=True, ignore_if_duplicate=True)
            print(f"  + Item Group L2 '{name}' creado.")
        else:
            print(f"  ✓ Item Group L2 '{name}' ya existe.")

    # Nivel 2 — Envases
    env_children = [
        "Bidones y Cubetas",
        "Botellas PET/HDPE",
        "Tapas y Cierres",
        "Etiquetas",
        "Embalaje Secundario",
    ]
    for name in env_children:
        if not _exists("Item Group", name):
            ig = frappe.new_doc("Item Group")
            ig.item_group_name = name
            ig.parent_item_group = "Material de Envasado"
            ig.is_group = 0
            ig.insert(ignore_permissions=True, ignore_if_duplicate=True)
            print(f"  + Item Group L2 '{name}' creado.")
        else:
            print(f"  ✓ Item Group L2 '{name}' ya existe.")

    # Nivel 2 — PT (grupos, porque tendrán hijos)
    pt_children = [
        "Pinturas",
        "Limpieza",
    ]
    for name in pt_children:
        if not _exists("Item Group", name):
            ig = frappe.new_doc("Item Group")
            ig.item_group_name = name
            ig.parent_item_group = "Producto Terminado"
            ig.is_group = 1
            ig.insert(ignore_permissions=True, ignore_if_duplicate=True)
            print(f"  + Item Group L2 '{name}' creado.")
        else:
            print(f"  ✓ Item Group L2 '{name}' ya existe.")

    # Nivel 3 — Subtipos de Pinturas
    pintura_children = ["Pintura Mate", "Pintura Satinada", "Esmalte", "Imprimación"]
    for name in pintura_children:
        if not _exists("Item Group", name):
            ig = frappe.new_doc("Item Group")
            ig.item_group_name = name
            ig.parent_item_group = "Pinturas"
            ig.is_group = 0
            ig.insert(ignore_permissions=True, ignore_if_duplicate=True)
            print(f"  + Item Group L3 '{name}' creado.")
        else:
            print(f"  ✓ Item Group L3 '{name}' ya existe.")


# ═══════════════════════════════════════════════════════════════════════════
# 5. ITEMS — Materias Primas
# ═══════════════════════════════════════════════════════════════════════════

def create_items_mp():
    """Crea las 4 materias primas del PoC Seed con trazabilidad por lote."""
    print("\n──── 5/15  Items — Materias Primas ────")

    company = "Peintures du Maroc SARL"
    abbr = "PDM"
    cuarentena = f"Cuarentena MP - {abbr}"

    materias_primas = [
        {
            "item_code": "MP-RES-ALK-G70",
            "item_name": "Résine Alkyde G-70",
            "item_group": "Resinas y Ligantes",
            "stock_uom": "Kg",
            "batch_number_series": "LOTE-RES-.YYYY.-.####",
            "shelf_life_in_days": 365,
            "uom_conversions": [
                {"uom": "g", "conversion_factor": 0.001},
                {"uom": "Litre", "conversion_factor": 1.075},
                {"uom": "Bidon 200L", "conversion_factor": 215.0},
            ],
        },
        {
            "item_code": "MP-PIG-TIO2-R902",
            "item_name": "Dioxyde de Titane R-902",
            "item_group": "Pigmentos y Cargas",
            "stock_uom": "Kg",
            "batch_number_series": "LOTE-PIG-.YYYY.-.####",
            "shelf_life_in_days": 730,
            "uom_conversions": [
                {"uom": "g", "conversion_factor": 0.001},
                {"uom": "Sac 25Kg", "conversion_factor": 25.0},
            ],
        },
        {
            "item_code": "MP-SOL-WSPI-STD",
            "item_name": "White Spirit Standard",
            "item_group": "Solventes y Diluyentes",
            "stock_uom": "Kg",
            "batch_number_series": "LOTE-SOL-.YYYY.-.####",
            "shelf_life_in_days": 1095,
            "uom_conversions": [
                {"uom": "g", "conversion_factor": 0.001},
                {"uom": "Litre", "conversion_factor": 0.780},
                {"uom": "Bidon 200L", "conversion_factor": 156.0},
            ],
        },
        {
            "item_code": "MP-H2O-DESMIN",
            "item_name": "Eau Déminéralisée",
            "item_group": "Solventes y Diluyentes",
            "stock_uom": "Kg",
            "batch_number_series": "LOTE-H2O-.YYYY.-.####",
            "shelf_life_in_days": 0,  # No caduca
            "uom_conversions": [
                {"uom": "g", "conversion_factor": 0.001},
                {"uom": "Litre", "conversion_factor": 1.0},
            ],
        },
    ]

    for mp in materias_primas:
        code = mp["item_code"]
        if _exists("Item", code):
            print(f"  ✓ Item '{code}' ya existe.")
            continue

        item = frappe.new_doc("Item")
        item.item_code = code
        item.item_name = mp["item_name"]
        item.item_group = mp["item_group"]
        item.stock_uom = mp["stock_uom"]
        item.is_stock_item = 1
        item.is_purchase_item = 1
        item.is_sales_item = 0
        item.include_item_in_manufacturing = 1
        item.has_batch_no = 1
        item.create_new_batch = 1
        item.batch_number_series = mp["batch_number_series"]
        item.has_expiry_date = 1 if mp["shelf_life_in_days"] > 0 else 0
        item.shelf_life_in_days = mp["shelf_life_in_days"]
        item.inspection_required_before_purchase = 1

        # Default warehouse = Cuarentena MP
        item.append("item_defaults", {
            "company": company,
            "default_warehouse": cuarentena,
        })

        # UoM conversions
        for conv in mp["uom_conversions"]:
            item.append("uoms", {
                "uom": conv["uom"],
                "conversion_factor": conv["conversion_factor"],
            })

        item.insert(ignore_permissions=True, ignore_if_duplicate=True)
        print(f"  + Item MP '{code}' creado.")


# ═══════════════════════════════════════════════════════════════════════════
# 6. ITEMS — Envases
# ═══════════════════════════════════════════════════════════════════════════

def create_items_envases():
    """Crea los 3 envases del PoC: cubeta, tapa, etiqueta. Sin lote ni QC."""
    print("\n──── 6/15  Items — Envases ────")

    company = "Peintures du Maroc SARL"
    abbr = "PDM"

    envases = [
        {
            "item_code": "ENV-BID-20L-BLC",
            "item_name": "Seau Plastique 20L Blanc",
            "item_group": "Bidones y Cubetas",
        },
        {
            "item_code": "ENV-TAP-BID-20L",
            "item_name": "Couvercle Seau 20L",
            "item_group": "Tapas y Cierres",
        },
        {
            "item_code": "ENV-ETQ-PIN-BLC",
            "item_name": "Étiquette Peinture Blanche Mate 20L",
            "item_group": "Etiquetas",
        },
    ]

    for env in envases:
        code = env["item_code"]
        if _exists("Item", code):
            print(f"  ✓ Item '{code}' ya existe.")
            continue

        item = frappe.new_doc("Item")
        item.item_code = code
        item.item_name = env["item_name"]
        item.item_group = env["item_group"]
        item.stock_uom = "Nos"
        item.is_stock_item = 1
        item.is_purchase_item = 1
        item.is_sales_item = 0
        item.include_item_in_manufacturing = 1
        item.has_batch_no = 0
        item.has_expiry_date = 0
        item.inspection_required_before_purchase = 0

        item.append("item_defaults", {
            "company": company,
            "default_warehouse": f"Materia Prima Aprobada - {abbr}",
        })

        item.insert(ignore_permissions=True, ignore_if_duplicate=True)
        print(f"  + Item ENV '{code}' creado.")


# ═══════════════════════════════════════════════════════════════════════════
# 7. ITEMS — Producto Terminado
# ═══════════════════════════════════════════════════════════════════════════

def create_items_pt():
    """Crea el PT de prueba: Pintura Blanca Mate 20L."""
    print("\n──── 7/15  Items — Producto Terminado ────")

    company = "Peintures du Maroc SARL"
    abbr = "PDM"
    code = "PT-PIN-BLC-MAT-20L"

    if _exists("Item", code):
        print(f"  ✓ Item '{code}' ya existe.")
        return

    item = frappe.new_doc("Item")
    item.item_code = code
    item.item_name = "Peinture Blanche Mate 20L"
    item.item_group = "Pintura Mate"
    item.stock_uom = "Nos"
    item.is_stock_item = 1
    item.is_purchase_item = 0
    item.is_sales_item = 1
    item.include_item_in_manufacturing = 1
    item.has_batch_no = 1
    item.create_new_batch = 1
    item.batch_number_series = "LOT-PIN-.YYYY.-.####"
    item.has_expiry_date = 1
    item.shelf_life_in_days = 730

    item.append("item_defaults", {
        "company": company,
        "default_warehouse": f"Cuarentena PT - {abbr}",
    })

    item.insert(ignore_permissions=True, ignore_if_duplicate=True)
    print(f"  + Item PT '{code}' creado.")


# ═══════════════════════════════════════════════════════════════════════════
# 8. PROVEEDORES
# ═══════════════════════════════════════════════════════════════════════════

def create_suppliers():
    """Dos proveedores PoC: uno europeo (EUR) y uno local (MAD)."""
    print("\n──── 8/15  Proveedores ────")

    # Supplier Groups
    for sg_name in ["Chimie Import", "Emballage Local"]:
        if not _exists("Supplier Group", sg_name):
            sg = frappe.new_doc("Supplier Group")
            sg.supplier_group_name = sg_name
            sg.insert(ignore_permissions=True, ignore_if_duplicate=True)
            print(f"  + Supplier Group '{sg_name}' creado.")

    suppliers = [
        {
            "supplier_name": "ChimEurope SARL",
            "supplier_group": "Chimie Import",
            "default_currency": "EUR",
        },
        {
            "supplier_name": "PlastiMaroc",
            "supplier_group": "Emballage Local",
            "default_currency": "MAD",
        },
    ]

    for s in suppliers:
        name = s["supplier_name"]
        if frappe.db.exists("Supplier", {"supplier_name": name}):
            print(f"  ✓ Supplier '{name}' ya existe.")
            continue
        doc = frappe.new_doc("Supplier")
        doc.supplier_name = name
        doc.supplier_group = s["supplier_group"]
        doc.default_currency = s["default_currency"]
        doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
        print(f"  + Supplier '{name}' creado.")


# ═══════════════════════════════════════════════════════════════════════════
# 9. CLIENTES
# ═══════════════════════════════════════════════════════════════════════════

def create_customers():
    """Dos clientes PoC con grupos y territorios diferenciados."""
    print("\n──── 9/15  Clientes ────")

    # Customer Groups
    for cg_name in ["Droguerie", "Distributeur", "Grossiste"]:
        if not _exists("Customer Group", cg_name):
            cg = frappe.new_doc("Customer Group")
            cg.customer_group_name = cg_name
            cg.parent_customer_group = "All Customer Groups"
            cg.insert(ignore_permissions=True, ignore_if_duplicate=True)
            print(f"  + Customer Group '{cg_name}' creado.")

    # Territories
    for t_name in ["Casablanca", "Rabat"]:
        if not _exists("Territory", t_name):
            t = frappe.new_doc("Territory")
            t.territory_name = t_name
            t.parent_territory = "All Territories"
            t.insert(ignore_permissions=True, ignore_if_duplicate=True)
            print(f"  + Territory '{t_name}' creado.")

    customers = [
        {
            "customer_name": "Droguerie Atlas",
            "customer_group": "Droguerie",
            "territory": "Casablanca",
            "default_currency": "MAD",
        },
        {
            "customer_name": "Distrib Maghreb",
            "customer_group": "Distributeur",
            "territory": "Rabat",
            "default_currency": "MAD",
        },
    ]

    for c in customers:
        name = c["customer_name"]
        if frappe.db.exists("Customer", {"customer_name": name}):
            print(f"  ✓ Customer '{name}' ya existe.")
            continue
        doc = frappe.new_doc("Customer")
        doc.customer_name = name
        doc.customer_group = c["customer_group"]
        doc.territory = c["territory"]
        doc.default_currency = c["default_currency"]
        doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
        print(f"  + Customer '{name}' creado.")


# ═══════════════════════════════════════════════════════════════════════════
# 10. PRICE LISTS
# ═══════════════════════════════════════════════════════════════════════════

def create_price_lists():
    """Crea las 4 listas de precios del PoC."""
    print("\n──── 10/15  Price Lists ────")

    price_lists = [
        {"name": "Standard Buying MAD", "currency": "MAD", "buying": 1, "selling": 0},
        {"name": "Standard Buying EUR", "currency": "EUR", "buying": 1, "selling": 0},
        {"name": "Tarif Droguerie",     "currency": "MAD", "buying": 0, "selling": 1},
        {"name": "Tarif Distributeur",  "currency": "MAD", "buying": 0, "selling": 1},
    ]

    for pl in price_lists:
        if _exists("Price List", pl["name"]):
            print(f"  ✓ Price List '{pl['name']}' ya existe.")
            continue
        doc = frappe.new_doc("Price List")
        doc.price_list_name = pl["name"]
        doc.currency = pl["currency"]
        doc.buying = pl["buying"]
        doc.selling = pl["selling"]
        doc.enabled = 1
        doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
        print(f"  + Price List '{pl['name']}' creada.")


# ═══════════════════════════════════════════════════════════════════════════
# 11. BOM — Receta de Pintura Blanca Mate 20L
# ═══════════════════════════════════════════════════════════════════════════

def create_bom():
    """Crea la BOM del PT de prueba: 1 cubeta de Pintura Blanca Mate 20L."""
    print("\n──── 11/15  BOM ────")

    pt_code = "PT-PIN-BLC-MAT-20L"
    company = "Peintures du Maroc SARL"

    # Verificar si ya hay una BOM activa para este item
    existing = frappe.db.exists("BOM", {"item": pt_code, "is_active": 1, "is_default": 1})
    if existing:
        print(f"  ✓ BOM activa para '{pt_code}' ya existe: {existing}")
        return

    bom = frappe.new_doc("BOM")
    bom.item = pt_code
    bom.company = company
    bom.quantity = 1  # 1 cubeta
    bom.is_active = 1
    bom.is_default = 1
    bom.with_operations = 0  # Sin operaciones por ahora

    # ── Ingredientes (Materias Primas) ──
    ingredients = [
        # (item_code, qty_kg, scrap_%)
        ("MP-RES-ALK-G70",    6.0, 2.0),
        ("MP-PIG-TIO2-R902",  8.0, 1.0),
        ("MP-SOL-WSPI-STD",   3.0, 3.0),
        ("MP-H2O-DESMIN",     9.0, 0.0),
    ]

    for item_code, qty, scrap in ingredients:
        bom.append("items", {
            "item_code": item_code,
            "qty": qty,
            "uom": "Kg",
            "stock_uom": "Kg",
            "conversion_factor": 1,
            "rate": 0,  # Se calcula al Submit
            "scrap": scrap,
        })

    # ── Envases (sin merma) ──
    packaging = [
        ("ENV-BID-20L-BLC", 1),
        ("ENV-TAP-BID-20L", 1),
        ("ENV-ETQ-PIN-BLC", 1),
    ]

    for item_code, qty in packaging:
        bom.append("items", {
            "item_code": item_code,
            "qty": qty,
            "uom": "Nos",
            "stock_uom": "Nos",
            "conversion_factor": 1,
            "rate": 0,
        })

    bom.insert(ignore_permissions=True)
    print(f"  + BOM '{bom.name}' creada (Draft).")
    print(f"    ⚠ La BOM se crea en Draft. Para activarla ejecuta:")
    print(f"      bench execute gcma_kiosco.setup.seed_data.submit_bom")


def submit_bom():
    """Envía (Submit) la BOM del PT. Separado porque requiere precios cargados."""
    pt_code = "PT-PIN-BLC-MAT-20L"
    bom_name = frappe.db.get_value(
        "BOM", {"item": pt_code, "is_active": 1, "docstatus": 0}, "name"
    )
    if not bom_name:
        print("  ✗ No hay BOM en Draft para submittear.")
        return
    bom = frappe.get_doc("BOM", bom_name)
    bom.submit()
    frappe.db.commit()
    print(f"  ✓ BOM '{bom_name}' submitted.")


# ═══════════════════════════════════════════════════════════════════════════
# 12. ITEM PRICES — Precios de compra y venta para el PoC
# ═══════════════════════════════════════════════════════════════════════════

def create_item_prices():
    """Carga precios de compra (MAD) y venta para que la BOM pueda ser submitted
    y las Pricing Rules funcionen en el Happy Path."""
    print("\n──── 12/15  Item Prices ────")

    prices = [
        # (item_code, price_list, rate, uom)
        # ── Compra MP (MAD) ──
        ("MP-RES-ALK-G70",    "Standard Buying MAD",  25.00, "Kg"),
        ("MP-PIG-TIO2-R902",  "Standard Buying MAD",  18.00, "Kg"),
        ("MP-SOL-WSPI-STD",   "Standard Buying MAD",  12.00, "Kg"),
        ("MP-H2O-DESMIN",     "Standard Buying MAD",   0.50, "Kg"),
        # ── Compra Envases (MAD) ──
        ("ENV-BID-20L-BLC",   "Standard Buying MAD",   8.00, "Nos"),
        ("ENV-TAP-BID-20L",   "Standard Buying MAD",   1.50, "Nos"),
        ("ENV-ETQ-PIN-BLC",   "Standard Buying MAD",   0.30, "Nos"),
        # ── Compra MP (EUR — para PO multi-moneda) ──
        ("MP-RES-ALK-G70",    "Standard Buying EUR",   2.30, "Kg"),
        ("MP-SOL-WSPI-STD",   "Standard Buying EUR",   1.10, "Kg"),
        # ── Venta PT ──
        ("PT-PIN-BLC-MAT-20L", "Tarif Droguerie",    280.00, "Nos"),
        ("PT-PIN-BLC-MAT-20L", "Tarif Distributeur",  250.00, "Nos"),
    ]

    for item_code, price_list, rate, uom in prices:
        exists = frappe.db.exists("Item Price", {
            "item_code": item_code,
            "price_list": price_list,
        })
        if exists:
            print(f"  ✓ Price '{item_code}' @ '{price_list}' ya existe.")
            continue
        ip = frappe.new_doc("Item Price")
        ip.item_code = item_code
        ip.price_list = price_list
        ip.price_list_rate = rate
        ip.uom = uom
        ip.insert(ignore_permissions=True, ignore_if_duplicate=True)
        print(f"  + Price '{item_code}' @ '{price_list}' = {rate} creado.")


# ═══════════════════════════════════════════════════════════════════════════
# 13. CUSTOM FIELDS — Campo QR Badge en Employee (para login Kiosco)
# ═══════════════════════════════════════════════════════════════════════════

def create_custom_fields():
    """Crea los custom fields necesarios para el Kiosco en doctypes nativos."""
    print("\n──── 13/15  Custom Fields ────")

    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields as _create_cf

    _create_cf({
        "Employee": [
            {
                "fieldname": "custom_qr_badge_token",
                "label": "QR Badge Token (Kiosco)",
                "fieldtype": "Data",
                "insert_after": "employee_name",
                "unique": 1,
                "in_list_view": 1,
                "description": "Token único impreso en el badge QR del operario. Usado por la PWA del Kiosco para autenticación sin contraseña.",
            },
        ],
    })
    print("  + Custom Field 'custom_qr_badge_token' en Employee creado/verificado.")


# ═══════════════════════════════════════════════════════════════════════════
# 14. EMPLEADO DE PRUEBA  (para testear login_operario con Postman)
# ═══════════════════════════════════════════════════════════════════════════

def create_test_employee():
    """Crea un usuario Frappe + empleado con badge QR para probar el Kiosco."""
    print("\n──── 14/15  Empleado de prueba ────")

    company = "Peintures du Maroc SARL"
    user_email = "operario.poc@gcma.local"
    badge_token = "OP-2026-BADGE-00042"

    # -- User --
    if not _exists("User", user_email):
        user = frappe.new_doc("User")
        user.email = user_email
        user.first_name = "Ahmed"
        user.last_name = "Benali"
        user.language = "fr"
        user.new_password = "poc-test-2026"
        user.send_welcome_email = 0
        user.user_type = "System User"
        user.append("roles", {"role": "Manufacturing User"})
        user.append("roles", {"role": "Stock User"})
        user.insert(ignore_permissions=True)
        print(f"  + User '{user_email}' creado (pwd: poc-test-2026).")
    else:
        print(f"  ✓ User '{user_email}' ya existe.")

    # -- Employee --
    existing_emp = frappe.db.exists("Employee", {"user_id": user_email})
    if not existing_emp:
        emp = frappe.new_doc("Employee")
        emp.employee_name = "Ahmed Benali"
        emp.first_name = "Ahmed"
        emp.last_name = "Benali"
        emp.company = company
        emp.status = "Active"
        emp.gender = "Male"
        emp.date_of_birth = "1990-05-15"
        emp.date_of_joining = "2024-01-10"
        emp.user_id = user_email
        emp.custom_qr_badge_token = badge_token
        emp.insert(ignore_permissions=True)
        print(f"  + Employee '{emp.name}' creado con badge '{badge_token}'.")
    else:
        # Asegurar que el badge esté asignado
        frappe.db.set_value("Employee", existing_emp, "custom_qr_badge_token", badge_token)
        print(f"  ✓ Employee ya existe. Badge actualizado a '{badge_token}'.")


# ═══════════════════════════════════════════════════════════════════════════
# 15. STOCK INICIAL — Inventario artificial para PoC inmediato
# ═══════════════════════════════════════════════════════════════════════════

def create_initial_stock():
    """Inyecta stock artificial en MP Aprobada y Envases.

    Usa Stock Entry (Material Receipt): crea stock 'del aire' con un coste
    de referencia. Esto permite probar Work Orders + API Kiosco sin tener
    que ejecutar manualmente los pasos 1-4 del Happy Path.

    NOTA: En producción real NUNCA se hace esto. El stock real entra solo
    por Purchase Receipt + QC Approval. Esto es SOLO para el sandbox PoC.
    """
    print("\n──── 15/15  Stock Inicial (PoC Artificial) ────")

    company = "Peintures du Maroc SARL"
    abbr = "PDM"
    posting_date = today()

    # Verificar si ya hay stock (idempotencia)
    existing_stock = frappe.db.sql("""
        SELECT SUM(actual_qty) FROM `tabStock Ledger Entry`
        WHERE company = %s AND is_cancelled = 0
    """, company)
    if existing_stock and existing_stock[0][0] and existing_stock[0][0] > 0:
        print("  ✓ Ya hay stock en el sistema. Saltando inyección.")
        return

    # ── Crear Batches para Materias Primas ──
    batches = [
        {
            "batch_id": "LOTE-RES-2026-0001",
            "item": "MP-RES-ALK-G70",
            "expiry_date": add_days(posting_date, 365),
        },
        {
            "batch_id": "LOTE-PIG-2026-0044",
            "item": "MP-PIG-TIO2-R902",
            "expiry_date": add_days(posting_date, 730),
        },
        {
            "batch_id": "LOTE-SOL-2026-0012",
            "item": "MP-SOL-WSPI-STD",
            "expiry_date": add_days(posting_date, 1095),
        },
        {
            "batch_id": "LOTE-H2O-2026-0001",
            "item": "MP-H2O-DESMIN",
            "expiry_date": None,
        },
    ]

    for b in batches:
        if not _exists("Batch", b["batch_id"]):
            batch = frappe.new_doc("Batch")
            batch.batch_id = b["batch_id"]
            batch.item = b["item"]
            if b["expiry_date"]:
                batch.expiry_date = b["expiry_date"]
            batch.insert(ignore_permissions=True)
            print(f"  + Batch '{b['batch_id']}' creado.")
        else:
            print(f"  ✓ Batch '{b['batch_id']}' ya existe.")

    # ── Stock Entry: Material Receipt (MP con lotes) ──
    wh_mp = f"Materia Prima Aprobada - {abbr}"

    mp_stock = [
        # (item_code, batch_no, qty, basic_rate MAD/UoM)
        ("MP-RES-ALK-G70",   "LOTE-RES-2026-0001",  1075.0,  25.00),  # 5 bidon × 215Kg
        ("MP-PIG-TIO2-R902", "LOTE-PIG-2026-0044",   500.0,  18.00),  # 20 sacos × 25Kg
        ("MP-SOL-WSPI-STD",  "LOTE-SOL-2026-0012",   468.0,  12.00),  # 3 bidon × 156Kg
        ("MP-H2O-DESMIN",    "LOTE-H2O-2026-0001",  1000.0,   0.50),  # 1000L ≈ 1000Kg
    ]

    se_mp = frappe.new_doc("Stock Entry")
    se_mp.stock_entry_type = "Material Receipt"
    se_mp.company = company
    se_mp.posting_date = posting_date
    se_mp.set_posting_time = 1
    se_mp.posting_time = "08:00:00"
    se_mp.remarks = "PoC Sandbox — Stock inicial artificial de Materias Primas"

    for item_code, batch_no, qty, rate in mp_stock:
        se_mp.append("items", {
            "item_code": item_code,
            "qty": qty,
            "t_warehouse": wh_mp,
            "batch_no": batch_no,
            "basic_rate": rate,
        })

    se_mp.insert(ignore_permissions=True)
    se_mp.submit()
    print(f"  + Stock Entry MP '{se_mp.name}' creado y submitted.")

    # ── Stock Entry: Material Receipt (Envases sin lote) ──
    env_stock = [
        # (item_code, qty, basic_rate MAD)
        ("ENV-BID-20L-BLC",  200,  8.00),
        ("ENV-TAP-BID-20L",  200,  1.50),
        ("ENV-ETQ-PIN-BLC",  200,  0.30),
    ]

    se_env = frappe.new_doc("Stock Entry")
    se_env.stock_entry_type = "Material Receipt"
    se_env.company = company
    se_env.posting_date = posting_date
    se_env.set_posting_time = 1
    se_env.posting_time = "08:05:00"
    se_env.remarks = "PoC Sandbox — Stock inicial artificial de Envases"

    for item_code, qty, rate in env_stock:
        se_env.append("items", {
            "item_code": item_code,
            "qty": qty,
            "t_warehouse": wh_mp,
            "basic_rate": rate,
        })

    se_env.insert(ignore_permissions=True)
    se_env.submit()
    print(f"  + Stock Entry ENV '{se_env.name}' creado y submitted.")

    print("  ────────────────────────────────────────────")
    print("  Stock inyectado en 'Materia Prima Aprobada - PDM':")
    print("    • Resina ALK G-70:     1,075 Kg  (LOTE-RES-2026-0001)")
    print("    • Titanio TiO2 R-902:    500 Kg  (LOTE-PIG-2026-0044)")
    print("    • White Spirit:          468 Kg  (LOTE-SOL-2026-0012)")
    print("    • Agua Desmin.:        1,000 Kg  (LOTE-H2O-2026-0001)")
    print("    • Cubetas 20L:           200 ud")
    print("    • Tapas:                 200 ud")
    print("    • Etiquetas:             200 ud")
    print("  → Suficiente para ~50 cubetas de pintura.")


# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT — bench execute gcma_kiosco.setup.seed_data.run
# ═══════════════════════════════════════════════════════════════════════════

def run():
    """Ejecuta todo el Seed Data del PoC en orden."""
    print("=" * 68)
    print("  GCMA — Seed Data PoC Sandbox (Data Foundation §3.1)")
    print("  Empresa objetivo: Peintures du Maroc SARL (PDM)")
    print("=" * 68)

    create_uoms()
    create_erpnext_prerequisites()
    create_companies()
    create_warehouses()
    create_item_groups()
    create_items_mp()
    create_items_envases()
    create_items_pt()
    create_suppliers()
    create_customers()
    create_price_lists()
    create_bom()
    create_item_prices()
    create_custom_fields()
    create_test_employee()
    create_initial_stock()

    frappe.db.commit()

    print("\n" + "=" * 68)
    print("  ✓ SEED DATA COMPLETADO — 15 módulos cargados")
    print("  Estado del sistema:")
    print("    ✓ Empresa PDM con 6 almacenes")
    print("    ✓ 8 items (4 MP + 3 ENV + 1 PT)")
    print("    ✓ BOM en Draft (submittear con submit_bom)")
    print("    ✓ Precios de compra y venta cargados")
    print("    ✓ Stock inicial artificial en MP Aprobada")
    print("    ✓ Empleado de prueba: Ahmed Benali (badge OP-2026-BADGE-00042)")
    print("  Próximos pasos:")
    print("    1. bench execute gcma_kiosco.setup.seed_data.submit_bom")
    print("    2. Probar API Kiosco → POST login_operario con badge QR")
    print("    3. Ejecutar Happy Path completo (12 pasos)")
    print("=" * 68)
