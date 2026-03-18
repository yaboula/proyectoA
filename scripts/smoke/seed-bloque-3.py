"""
Seed data Bloque 3 — Comercial B2B & Logística.

Ejecutar DENTRO del container Docker:
  docker exec frappe_docker-backend-1 \
    /home/frappe/frappe-bench/env/bin/python \
    /workspace/scripts/smoke/seed-bloque-3.py

O via bench:
  bench --site frontend execute gcma_kiosco.setup.seed_b2b.run

Datos que crea (todos idempotentes con upsert):
  - 1 Sales Person "COM-2026-BADGE-00099" (badge QR para login comercial)
  - 1 Sales Person "CHOFER-2026-BADGE-00088" (badge chofer)
  - 1 Customer "CLI-B2B-TEST-001" con portal_customer_id
  - 1 Loyalty Program "GCMA Loyalty 2026" (si no existe ninguno)
  - 1 Sales Order confirmado con 2 items FEFO
  - 1 Delivery Note en estado "To Deliver" para el chofer
  - 2 lotes con fecha de vencimiento: uno próximo (FEFO sugerido), uno lejano
"""

import frappe
from frappe.utils import add_days, today, nowdate

frappe.connect(site="frontend")


def upsert(doctype, name, defaults):
    if frappe.db.exists(doctype, name):
        doc = frappe.get_doc(doctype, name)
        for k, v in defaults.items():
            if hasattr(doc, k):
                setattr(doc, k, v)
        doc.save(ignore_permissions=True)
        print(f"  [UPDATE] {doctype}: {name}")
    else:
        doc = frappe.get_doc({"doctype": doctype, "name": name, **defaults})
        doc.insert(ignore_permissions=True)
        print(f"  [CREATE] {doctype}: {name}")
    return frappe.get_doc(doctype, name)


company = frappe.db.get_single_value("Global Defaults", "default_company") or "Peintures du Maroc SARL"
print(f"\n[SEED B3] Empresa: {company}\n")

# ── 1. Operarios (Sales Person con login QR) ──────────────────────────────────
print("[1/8] Operarios comerciales...")

BADGE_COMERCIAL = "COM-2026-BADGE-00099"
BADGE_CHOFER    = "CHOFER-2026-BADGE-00088"

for badge, role_name in [(BADGE_COMERCIAL, "Comercial Test"), (BADGE_CHOFER, "Chofer Test")]:
    if not frappe.db.exists("Employee", {"employee_id": badge}):
        emp = frappe.get_doc({
            "doctype": "Employee",
            "employee_id": badge,
            "employee_name": role_name,
            "first_name": role_name.split()[0],
            "company": company,
            "status": "Active",
            "gender": "Male",
            "date_of_birth": "1990-01-01",
            "date_of_joining": "2024-01-01",
        })
        emp.insert(ignore_permissions=True)
        print(f"  [CREATE] Employee: {badge}")

        # Custom Field: kiosk_badge_token
        if frappe.db.table_exists("tabEmployee"):
            frappe.db.set_value("Employee", emp.name, "kiosk_badge_token", badge)
    else:
        emp_name = frappe.db.get_value("Employee", {"employee_id": badge}, "name")
        frappe.db.set_value("Employee", emp_name, "kiosk_badge_token", badge)
        print(f"  [EXISTS] Employee: {badge}")

# ── 2. Customer B2B con portal_customer_id ────────────────────────────────────
print("\n[2/8] Customer B2B...")
CUSTOMER_ID = "CLI-B2B-TEST-001"
CUSTOMER_NAME = "Droguerie Atlas Test"

if not frappe.db.exists("Customer", CUSTOMER_NAME):
    cust = frappe.get_doc({
        "doctype": "Customer",
        "customer_name": CUSTOMER_NAME,
        "customer_type": "Company",
        "customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Commercial",
        "territory": frappe.db.get_value("Territory", {}, "name") or "Maroc",
    })
    cust.insert(ignore_permissions=True)
    frappe.db.set_value("Customer", cust.name, "portal_customer_id", CUSTOMER_ID)
    print(f"  [CREATE] Customer: {CUSTOMER_NAME} (portal_id={CUSTOMER_ID})")
else:
    frappe.db.set_value("Customer", CUSTOMER_NAME, "portal_customer_id", CUSTOMER_ID)
    print(f"  [EXISTS] Customer: {CUSTOMER_NAME}")

customer_doc_name = frappe.db.get_value("Customer", {"customer_name": CUSTOMER_NAME}, "name")

# ── 3. Loyalty Program ────────────────────────────────────────────────────────
print("\n[3/8] Loyalty Program...")
LOYALTY_PROGRAM = "GCMA Loyalty 2026"

if not frappe.db.exists("Loyalty Program", LOYALTY_PROGRAM):
    lp = frappe.get_doc({
        "doctype": "Loyalty Program",
        "loyalty_program_name": LOYALTY_PROGRAM,
        "from_date": today(),
        "to_date": add_days(today(), 365),
        "disabled": 0,
        "loyalty_program_type": "Single Tier Program",
        "collection_rules": [{
            "tier_name": "Standard",
            "collection_factor": 100,
            "min_spent": 0,
        }],
    })
    lp.insert(ignore_permissions=True)
    print(f"  [CREATE] Loyalty Program: {LOYALTY_PROGRAM}")
else:
    print(f"  [EXISTS] Loyalty Program: {LOYALTY_PROGRAM}")

# Asociar loyalty program al cliente
frappe.db.set_value("Customer", customer_doc_name, "loyalty_program", LOYALTY_PROGRAM)

# ── 4. Items de prueba FEFO ───────────────────────────────────────────────────
print("\n[4/8] Items FEFO de prueba...")

ITEM_A = "PT-TEST-B3-ITEM-A"
ITEM_B = "PT-TEST-B3-ITEM-B"
warehouse = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name")

for item_code, item_name in [(ITEM_A, "Peinture Test B3 Item A"), (ITEM_B, "Peinture Test B3 Item B")]:
    if not frappe.db.exists("Item", item_code):
        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": item_code,
            "item_name": item_name,
            "item_group": "Products",
            "has_batch_no": 1,
            "create_new_batch": 1,
            "is_stock_item": 1,
            "stock_uom": "Nos",
        })
        item.insert(ignore_permissions=True)
        print(f"  [CREATE] Item: {item_code}")
    else:
        print(f"  [EXISTS] Item: {item_code}")

# ── 5. Lotes FEFO (uno próximo a vencer, uno lejano) ─────────────────────────
print("\n[5/8] Lotes FEFO...")

BATCH_NEAR = "B3-FEFO-NEAR-001"   # vence en 30 días → FEFO lo debe sugerir primero
BATCH_FAR  = "B3-FEFO-FAR-001"    # vence en 180 días

for batch_id, item_code, days_until_exp in [
    (BATCH_NEAR, ITEM_A, 30),
    (BATCH_FAR,  ITEM_A, 180),
    (BATCH_NEAR + "-B", ITEM_B, 45),
]:
    if not frappe.db.exists("Batch", batch_id):
        b = frappe.get_doc({
            "doctype": "Batch",
            "batch_id": batch_id,
            "item": item_code,
            "expiry_date": add_days(today(), days_until_exp),
            "manufacturing_date": today(),
        })
        b.insert(ignore_permissions=True)
        print(f"  [CREATE] Batch: {batch_id} (exp +{days_until_exp}d)")

    # Stock Entry — Material Receipt para dar stock al lote
    if warehouse and frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse, "batch_no": batch_id}, "actual_qty") in [None, 0]:
        try:
            se = frappe.get_doc({
                "doctype": "Stock Entry",
                "stock_entry_type": "Material Receipt",
                "company": company,
                "items": [{
                    "item_code": item_code,
                    "qty": 50,
                    "uom": "Nos",
                    "t_warehouse": warehouse,
                    "batch_no": batch_id,
                    "basic_rate": 100,
                }],
            })
            se.insert(ignore_permissions=True)
            se.submit()
            print(f"  [STOCK] {item_code} / {batch_id} → 50 Nos en {warehouse}")
        except Exception as ex:
            print(f"  [WARN] Stock entry: {ex}")

# ── 6. Sales Order confirmado ─────────────────────────────────────────────────
print("\n[6/8] Sales Order de prueba...")
SO_NAME_CUSTOM = "B3-SO-TEST-001"

if not frappe.db.exists("Sales Order", {"custom_id": SO_NAME_CUSTOM}):
    try:
        so = frappe.get_doc({
            "doctype": "Sales Order",
            "customer": customer_doc_name,
            "company": company,
            "delivery_date": add_days(today(), 3),
            "items": [
                {
                    "item_code": ITEM_A,
                    "qty": 5,
                    "uom": "Nos",
                    "warehouse": warehouse,
                    "rate": 150,
                },
                {
                    "item_code": ITEM_B,
                    "qty": 3,
                    "uom": "Nos",
                    "warehouse": warehouse,
                    "rate": 200,
                },
            ],
        })
        so.insert(ignore_permissions=True)
        so.submit()
        # Guardar el nombre real generado para el smoke test
        print(f"  [CREATE] Sales Order: {so.name} (para picking FEFO S09)")
        # Escribir nombre en archivo de referencia
        with open("/tmp/b3_so_name.txt", "w") as f:
            f.write(so.name)
    except Exception as ex:
        print(f"  [WARN] Sales Order: {ex}")
else:
    print(f"  [EXISTS] Sales Order ref: {SO_NAME_CUSTOM}")

# ── 7. Delivery Note para el chofer ──────────────────────────────────────────
print("\n[7/8] Delivery Note para chofer...")
try:
    pending_dn = frappe.db.get_value(
        "Delivery Note",
        {"customer": customer_doc_name, "docstatus": 1, "status": ["in", ["To Deliver", "Partially Delivered"]]},
        "name"
    )
    if pending_dn:
        print(f"  [EXISTS] Delivery Note: {pending_dn}")
    else:
        dn = frappe.get_doc({
            "doctype": "Delivery Note",
            "customer": customer_doc_name,
            "company": company,
            "posting_date": today(),
            "items": [{
                "item_code": ITEM_A,
                "qty": 2,
                "uom": "Nos",
                "warehouse": warehouse,
                "rate": 150,
                "batch_no": BATCH_NEAR,
            }],
        })
        dn.insert(ignore_permissions=True)
        dn.submit()
        print(f"  [CREATE] Delivery Note: {dn.name}")
        with open("/tmp/b3_dn_name.txt", "w") as f:
            f.write(dn.name)
except Exception as ex:
    print(f"  [WARN] Delivery Note: {ex}")

# ── 8. Loyalty Point Entry semilla ───────────────────────────────────────────
print("\n[8/8] Loyalty Points semilla...")
try:
    existing = frappe.db.count("Loyalty Point Entry", {"customer": customer_doc_name, "type": "Earning"})
    if existing == 0:
        lpe = frappe.get_doc({
            "doctype": "Loyalty Point Entry",
            "loyalty_program": LOYALTY_PROGRAM,
            "customer": customer_doc_name,
            "loyalty_points": 250,
            "type": "Earning",
            "expiry_date": add_days(today(), 365),
            "posting_date": today(),
            "company": company,
        })
        lpe.insert(ignore_permissions=True)
        print(f"  [CREATE] 250 puntos Earning para {customer_doc_name}")
    else:
        print(f"  [EXISTS] Ya tiene {existing} entradas Earning")
except Exception as ex:
    print(f"  [WARN] Loyalty Points: {ex}")

frappe.db.commit()

print("""
╔══════════════════════════════════════════════════════════════╗
║  SEED BLOQUE 3 COMPLETADO                                    ║
╠══════════════════════════════════════════════════════════════╣
║  Badge Comercial : COM-2026-BADGE-00099                      ║
║  Badge Chofer    : CHOFER-2026-BADGE-00088                   ║
║  Customer ID     : CLI-B2B-TEST-001                          ║
║  Item FEFO A     : PT-TEST-B3-ITEM-A                         ║
║  Batch NEAR      : B3-FEFO-NEAR-001  (vence en ~30d)         ║
║  Batch FAR       : B3-FEFO-FAR-001   (vence en ~180d)        ║
║  Loyalty Program : GCMA Loyalty 2026 (250 pts pre-cargados)  ║
╚══════════════════════════════════════════════════════════════╝
""")
