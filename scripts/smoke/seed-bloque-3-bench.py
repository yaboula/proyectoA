"""
Seed data Bloque 3 — Comercial B2B & Logística.
VERSION para bench console.

EJECUTAR:
  docker cp seed-bloque-3-bench.py frappe_docker-backend-1:/tmp/seed-bloque-3-bench.py
  docker exec -u frappe frappe_docker-backend-1 bash -c \
    "cd /home/frappe/frappe-bench && bench --site frontend console < /tmp/seed-bloque-3-bench.py"
"""

from frappe.utils import add_days, flt, today, now_datetime

# ── Constantes ────────────────────────────────────────────────────────────────
BADGE_COM   = "COM-2026-BADGE-00099"
BADGE_CHO   = "CHOFER-2026-BADGE-00088"
EMAIL_COM   = "comercial.b3@gcma.local"
EMAIL_CHO   = "chofer.b3@gcma.local"
CUST_NAME   = "Droguerie Atlas Test"   # nombre real del Customer (docname)
ITEM_A      = "PT-TEST-B3-ITEM-A"
ITEM_B      = "PT-TEST-B3-ITEM-B"
BATCH_NEAR  = "B3-FEFO-NEAR-001"
BATCH_FAR   = "B3-FEFO-FAR-001"
BATCH_B     = "B3-FEFO-B-001"
LOYALTY_PG  = "GCMA Loyalty 2026"

_company   = frappe.db.get_single_value("Global Defaults", "default_company") or "Peintures du Maroc SARL"
_warehouse = frappe.db.get_value("Warehouse", {"company": _company, "is_group": 0}, "name")
_selling_pl = frappe.db.get_value("Price List", {"selling": 1, "currency": "MAD"}, "name") or frappe.db.get_value("Price List", {"selling": 1}, "name") or "Standard Selling"
print(f"\n[SEED B3] company={_company!r}  warehouse={_warehouse!r}  pl={_selling_pl!r}\n")

# ── 1. Users ──────────────────────────────────────────────────────────────────
print("[1/9] Users...")
for email, first, last, roles in [
    (EMAIL_COM, "Youssef", "Alaoui", ["Sales User", "Stock User"]),
    (EMAIL_CHO, "Khalid",  "Benali", ["Stock User"]),
]:
    if not frappe.db.exists("User", email):
        u = frappe.new_doc("User")
        u.email, u.first_name, u.last_name = email, first, last
        u.language, u.new_password = "fr", "poc-test-2026"
        u.send_welcome_email, u.user_type = 0, "System User"
        for r in roles:
            if frappe.db.exists("Role", r):
                u.append("roles", {"role": r})
        u.insert(ignore_permissions=True)
        print(f"  [CREATE] User {email}")
    else:
        print(f"  [EXISTS] User {email}")

# ── 1b. Ampliar opciones de custom_kiosk_profile ──────────────────────────────
print("\n[1b/9] Actualizando opciones de custom_kiosk_profile...")
cf = frappe.db.get_value("Custom Field", {"dt": "Employee", "fieldname": "custom_kiosk_profile"}, "name")
if cf:
    current_opts = frappe.db.get_value("Custom Field", cf, "options") or ""
    new_profiles = ["production", "quality", "comercial", "logistica", "reception"]
    existing = [o.strip() for o in current_opts.splitlines() if o.strip()]
    added = [p for p in new_profiles if p not in existing]
    if added:
        new_opts = "\n".join(existing + added)
        frappe.db.set_value("Custom Field", cf, "options", new_opts)
        frappe.clear_cache()
        print(f"  [UPDATE] Añadidos: {added}")
    else:
        print(f"  [EXISTS] Opciones ya incluyen comercial/logistica")
else:
    print(f"  [WARN]   Custom Field custom_kiosk_profile no encontrado")

# ── 2. Employees (usan company inline) ───────────────────────────────────────
print("\n[2/9] Employees (badge kiosco)...")
for email, first, last, badge, profile in [
    (EMAIL_COM, "Youssef", "Alaoui", BADGE_COM, "comercial"),
    (EMAIL_CHO, "Khalid",  "Benali", BADGE_CHO, "logistica"),
]:
    existing = frappe.db.get_value("Employee", {"user_id": email}, "name")
    if not existing:
        # Insertar vía SQL directo para evitar el UnboundLocalError de Frappe 16
        emp_name = frappe.generate_hash(length=10)
        now = now_datetime()
        try:
            frappe.db.sql("""
                insert into tabEmployee
                  (name, employee_name, first_name, last_name, company, status, gender,
                   date_of_birth, date_of_joining, user_id,
                   custom_qr_badge_token, custom_kiosk_profile,
                   creation, modified, owner, modified_by, docstatus)
                values (%s,%s,%s,%s,%s,'Active','Male',
                   '1990-01-01','2024-01-01',%s,%s,%s,%s,%s,
                   'Administrator','Administrator',0)
            """, (emp_name, f"{first} {last}", first, last, _company,
                  email, badge, profile, now, now))
            print(f"  [CREATE] Employee {badge} profile={profile} (via SQL)")
        except Exception as e:
            print(f"  [WARN]   Employee SQL insert: {str(e)[:100]}")
    else:
        frappe.db.sql("""
            update tabEmployee
            set custom_qr_badge_token=%s, custom_kiosk_profile=%s
            where name=%s
        """, (badge, profile, existing))
        print(f"  [UPDATE] Employee {badge} profile={profile}")

# ── 3. Customer B2B ───────────────────────────────────────────────────────────
print("\n[3/9] Customer B2B...")
cust = frappe.db.get_value("Customer", {"customer_name": CUST_NAME}, "name")
if not cust:
    cg   = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Commercial"
    terr = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "Maroc"
    c = frappe.new_doc("Customer")
    c.customer_name, c.customer_type = CUST_NAME, "Company"
    c.customer_group, c.territory = cg, terr
    c.default_currency = "MAD"
    c.insert(ignore_permissions=True)
    cust = c.name
    print(f"  [CREATE] {CUST_NAME} -> name={cust!r}")
else:
    print(f"  [EXISTS] {CUST_NAME} -> name={cust!r}")

print(f"  >> Para el smoke test usa: CUSTOMER_ID = {cust!r}")

# ── 4. User Permission: comercial → Customer ───────────────────────────────────
print("\n[4/9] User Permission (portal tenant)...")
existing_perm = frappe.db.get_value(
    "User Permission",
    {"user": EMAIL_COM, "allow": "Customer", "for_value": cust},
    "name",
)
if not existing_perm:
    try:
        up = frappe.new_doc("User Permission")
        up.user = EMAIL_COM
        up.allow = "Customer"
        up.for_value = cust
        up.apply_to_all_doctypes = 1
        up.insert(ignore_permissions=True)
        print(f"  [CREATE] {EMAIL_COM} -> Customer -> {cust!r}")
    except Exception as e:
        print(f"  [WARN]   User Permission: {e}")
else:
    print(f"  [EXISTS] User Permission {EMAIL_COM} -> {cust!r}")

# ── 5. Items ──────────────────────────────────────────────────────────────────
print("\n[5/9] Items FEFO...")
ig = frappe.db.get_value("Item Group", {"is_group": 0}, "name") or "Products"
for code, name in [(ITEM_A, "Peinture Test B3 Item A"), (ITEM_B, "Peinture Test B3 Item B")]:
    if not frappe.db.exists("Item", code):
        it = frappe.new_doc("Item")
        it.item_code, it.item_name = code, name
        it.item_group = ig
        it.has_batch_no, it.create_new_batch = 1, 0
        it.is_stock_item, it.stock_uom = 1, "Nos"
        it.insert(ignore_permissions=True)
        print(f"  [CREATE] {code}")
    else:
        print(f"  [EXISTS] {code}")

# ── 6. Batches ────────────────────────────────────────────────────────────────
print("\n[6/9] Batches FEFO...")
for bid, item, days in [(BATCH_NEAR, ITEM_A, 30), (BATCH_FAR, ITEM_A, 180), (BATCH_B, ITEM_B, 45)]:
    if not frappe.db.exists("Batch", bid):
        b = frappe.new_doc("Batch")
        b.batch_id, b.item = bid, item
        b.expiry_date = add_days(today(), days)
        b.manufacturing_date = today()
        b.insert(ignore_permissions=True)
        print(f"  [CREATE] {bid}  item={item}  exp=+{days}d")
    else:
        print(f"  [EXISTS] {bid}")

# ── 7. Stock via SLE directo (evita bug Frappe 16 en SE validation) ───────────
print("\n[7/9] Stock directo en SLE...")
for item, batch, qty in [(ITEM_A, BATCH_NEAR, 50), (ITEM_A, BATCH_FAR, 50), (ITEM_B, BATCH_B, 50)]:
    current = frappe.db.sql(
        "select ifnull(sum(actual_qty),0) from `tabStock Ledger Entry` "
        "where item_code=%s and batch_no=%s and warehouse=%s and is_cancelled=0",
        (item, batch, _warehouse),
    )
    current_qty = flt(current[0][0]) if current else 0
    if current_qty < qty:
        needed = qty - current_qty
        try:
            # Intentar Material Receipt normal
            se = frappe.new_doc("Stock Entry")
            se.stock_entry_type = "Material Receipt"
            se.company = _company
            se.posting_date = today()
            row = se.append("items", {})
            row.item_code = item
            row.qty = needed
            row.uom = "Nos"
            row.stock_uom = "Nos"
            row.t_warehouse = _warehouse
            row.batch_no = batch
            row.basic_rate = 100.0
            row.valuation_rate = 100.0
            row.amount = needed * 100.0
            se.insert(ignore_permissions=True)
            se.submit()
            print(f"  [STOCK]  {item}/{batch} +{needed:.0f} Nos")
        except Exception as e:
            print(f"  [WARN]   Stock Entry {item}/{batch}: {str(e)[:80]}")
            # Fallback: insertar SLE directamente para que el stock exista
            try:
                frappe.db.sql("""
                    insert into `tabStock Ledger Entry`
                      (name, item_code, warehouse, batch_no, actual_qty, qty_after_transaction,
                       valuation_rate, stock_value, stock_value_difference,
                       posting_date, posting_time, voucher_type, voucher_no,
                       company, is_cancelled, creation, modified, owner, modified_by, docstatus)
                    values (%s,%s,%s,%s,%s,%s, 100,5000,5000,
                       %s,'00:00:00','Stock Entry','SEED-B3-MANUAL',
                       %s,0,%s,%s,'Administrator','Administrator',1)
                """, (
                    frappe.generate_hash(length=10),
                    item, _warehouse, batch, needed, needed,
                    today(), _company,
                    now_datetime(), now_datetime(),
                ))
                print(f"  [SLE]    {item}/{batch} +{needed:.0f} Nos (via SQL fallback)")
            except Exception as e2:
                print(f"  [ERR]    SLE fallback: {str(e2)[:80]}")
    else:
        print(f"  [OK]     {item}/{batch}: {current_qty:.0f} Nos ya en stock")

# ── 8. Item Prices ────────────────────────────────────────────────────────────
print("\n[8/9] Item Prices...")
for item, rate in [(ITEM_A, 150.0), (ITEM_B, 200.0)]:
    ep = frappe.db.get_value("Item Price", {"item_code": item, "price_list": _selling_pl, "selling": 1}, "name")
    if not ep:
        ip = frappe.new_doc("Item Price")
        ip.item_code, ip.price_list = item, _selling_pl
        ip.selling, ip.price_list_rate, ip.currency = 1, rate, "MAD"
        ip.insert(ignore_permissions=True)
        print(f"  [CREATE] {item} @ {rate} MAD")
    else:
        print(f"  [EXISTS] {item} @ {rate} MAD")

# ── 9. Loyalty Points (250 pts de semilla) ────────────────────────────────────
print("\n[9/9] Loyalty Program + Points...")
if not frappe.db.exists("Loyalty Program", LOYALTY_PG):
    lp = frappe.new_doc("Loyalty Program")
    lp.loyalty_program_name = LOYALTY_PG
    lp.from_date, lp.to_date = today(), add_days(today(), 365)
    lp.disabled = 0
    lp.loyalty_program_type = "Single Tier Program"
    tier = lp.append("collection_rules", {})
    tier.tier_name = "Standard"
    tier.collection_factor = 100
    tier.min_spent = 0
    lp.insert(ignore_permissions=True)
    print(f"  [CREATE] Loyalty Program: {LOYALTY_PG}")
else:
    print(f"  [EXISTS] Loyalty Program: {LOYALTY_PG}")

lpe_count = frappe.db.sql(
    "select count(*) from `tabLoyalty Point Entry` where customer=%s", (cust,)
)
if flt(lpe_count[0][0]) == 0:
    try:
        frappe.db.sql("""
            insert into `tabLoyalty Point Entry`
              (name, loyalty_program, customer, loyalty_points, expiry_date, posting_date,
               company, creation, modified, owner, modified_by, docstatus)
            values (%s,%s,%s,250,%s,%s,%s,%s,%s,'Administrator','Administrator',1)
        """, (
            frappe.generate_hash(length=10),
            LOYALTY_PG, cust,
            add_days(today(), 365), today(), _company,
            now_datetime(), now_datetime(),
        ))
        print(f"  [CREATE] 250 Loyalty Points para {cust!r}")
    except Exception as e:
        print(f"  [WARN]   Loyalty Points: {e}")
else:
    print(f"  [EXISTS] {int(flt(lpe_count[0][0]))} entradas loyalty ya existen")

frappe.db.commit()

# ── Nota sobre Sales Order ────────────────────────────────────────────────────
so_name = frappe.db.get_value(
    "Sales Order",
    {"customer": cust, "docstatus": 1, "status": ["not in", ["Closed", "Cancelled"]]},
    "name",
)

print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║  SEED BLOQUE 3 COMPLETADO                                            ║
╠══════════════════════════════════════════════════════════════════════╣
║  Badge Comercial : {BADGE_COM:<50}║
║  Badge Chofer    : {BADGE_CHO:<50}║
║  Email Comercial : {EMAIL_COM:<50}║
║  Customer name   : {cust:<50}║
║  Sales Order     : {(so_name or "MANUAL — ver nota abajo"):<50}║
║  Loyalty Program : {LOYALTY_PG:<50}║
║  Batch NEAR (30d): {BATCH_NEAR:<50}║
╚══════════════════════════════════════════════════════════════════════╝

NOTAS:
• En el smoke test usa: -ClienteId {cust!r}
• Si no hay Sales Order, crearlo manualmente en ERPNext UI:
    Customer: {cust}  →  Items: {ITEM_A}(5) + {ITEM_B}(3)  →  Submit
  Luego ejecutar:
    .\\scripts\\smoke\\test-bloque-3.ps1 -SalesOrder "SAL-ORD-2026-XXXXX"
""")
