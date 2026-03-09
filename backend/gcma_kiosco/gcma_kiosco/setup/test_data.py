"""
GCMA — Test Data: Stock ampliado y Work Order para pruebas de EP2/EP3.

Ejecutar con:
    bench execute gcma_kiosco.setup.test_data.run

Prerequisito: haber ejecutado seed_data.run y seed_data.submit_bom
"""

import frappe
from frappe.utils import today, add_days, add_years


COMPANY = "Peintures du Maroc SARL"
ABBR = "PDM"
WH_MP = f"Materia Prima Aprobada - {ABBR}"
WH_WIP = f"Planta Mezclas WIP - {ABBR}"
PT_CODE = "PT-PIN-BLC-MAT-20L"


def _exists(doctype: str, name: str) -> bool:
    return frappe.db.exists(doctype, name)


# ═══════════════════════════════════════════════════════════════════════════
# 1. STOCK AMPLIADO — 2000 Kg de cada MP con lotes y caducidad
# ═══════════════════════════════════════════════════════════════════════════

def create_test_stock():
    """Inyecta 2000 Kg de cada Materia Prima en MP Aprobada con lotes válidos.

    Lotes nuevos (independientes de los del seed) con caducidad a 1 año.
    Idempotente: verifica si los lotes ya existen.
    """
    print("\n──── 1/2  Stock Ampliado para Tests ────")

    posting_date = today()
    expiry_date = add_years(posting_date, 1)

    batches_mp = [
        # (item_code, batch_id, qty_kg, basic_rate MAD/Kg)
        ("MP-RES-ALK-G70",   "LOTE-TEST-RES-001",  2000.0,  25.00),
        ("MP-PIG-TIO2-R902", "LOTE-TEST-PIG-001",  2000.0,  18.00),
        ("MP-SOL-WSPI-STD",  "LOTE-TEST-SOL-001",  2000.0,  12.00),
        ("MP-H2O-DESMIN",    "LOTE-TEST-H2O-001",  2000.0,   0.50),
    ]

    # ── Crear Batches ──
    for item_code, batch_id, _, _ in batches_mp:
        if not _exists("Batch", batch_id):
            batch = frappe.new_doc("Batch")
            batch.batch_id = batch_id
            batch.item = item_code
            batch.expiry_date = expiry_date
            batch.insert(ignore_permissions=True)
            print(f"  + Batch '{batch_id}' creado (caduca {expiry_date}).")
        else:
            print(f"  ✓ Batch '{batch_id}' ya existe.")

    # ── Verificar si ya se inyectó este stock (por remarks) ──
    existing_se = frappe.db.exists("Stock Entry", {
        "remarks": "Test Data — Stock ampliado 2000 Kg por MP",
        "docstatus": 1,
    })
    if existing_se:
        print("  ✓ Stock Entry de test ya existe. Saltando inyección.")
        return

    # ── Stock Entry: Material Receipt ──
    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = "Material Receipt"
    se.company = COMPANY
    se.posting_date = posting_date
    se.set_posting_time = 1
    se.posting_time = "09:00:00"
    se.remarks = "Test Data — Stock ampliado 2000 Kg por MP"

    for item_code, batch_id, qty, rate in batches_mp:
        se.append("items", {
            "item_code": item_code,
            "qty": qty,
            "t_warehouse": WH_MP,
            "batch_no": batch_id,
            "basic_rate": rate,
        })

    se.insert(ignore_permissions=True)
    se.submit()
    print(f"  + Stock Entry '{se.name}' creado y submitted.")

    for item_code, batch_id, qty, _ in batches_mp:
        print(f"    • {item_code}: {qty:,.0f} Kg ({batch_id})")

    frappe.db.commit()


# ═══════════════════════════════════════════════════════════════════════════
# 2. WORK ORDER — 50 cubetas de PT-PIN-BLC-MAT-20L en estado In Process
# ═══════════════════════════════════════════════════════════════════════════

def create_test_work_order():
    """Crea una Work Order para 50 unidades de PT y la pone In Process.

    Prerequisito: BOM submitted para PT-PIN-BLC-MAT-20L.
    Idempotente: verifica si ya existe una WO In Process para este item.
    """
    print("\n──── 2/2  Work Order de Prueba ────")

    # Verificar si ya existe una WO en proceso
    existing_wo = frappe.db.exists("Work Order", {
        "production_item": PT_CODE,
        "status": "In Process",
        "company": COMPANY,
        "docstatus": 1,
    })
    if existing_wo:
        print(f"  ✓ Work Order In Process ya existe: {existing_wo}")
        return

    # Obtener la BOM activa
    bom_name = frappe.db.get_value(
        "BOM",
        {"item": PT_CODE, "is_active": 1, "is_default": 1, "docstatus": 1},
        "name",
    )
    if not bom_name:
        print("  ✗ No hay BOM submitted. Ejecuta primero: bench execute gcma_kiosco.setup.seed_data.submit_bom")
        return

    # ── Crear Work Order ──
    wo = frappe.new_doc("Work Order")
    wo.production_item = PT_CODE
    wo.company = COMPANY
    wo.qty = 50
    wo.bom_no = bom_name
    wo.wip_warehouse = WH_WIP
    wo.fg_warehouse = f"Cuarentena PT - {ABBR}"
    wo.stock_uom = "Nos"
    wo.planned_start_date = today()
    wo.use_multi_level_bom = 0

    wo.insert(ignore_permissions=True)
    wo.submit()
    print(f"  + Work Order '{wo.name}' creada y submitted (status: {wo.status}).")

    # ── Pasar a In Process usando Start (via set_value + update status) ──
    # En ERPNext, una WO pasa a "In Process" cuando se crea un Job Card
    # o se marca manualmente. Usamos el mecanismo directo:
    frappe.db.set_value("Work Order", wo.name, "status", "In Process")
    frappe.db.commit()
    print(f"  + Work Order '{wo.name}' → status = In Process.")

    # ── Resumen ──
    bom_doc = frappe.get_doc("BOM", bom_name)
    print(f"  Producto: {PT_CODE} × 50 cubetas")
    print(f"  BOM: {bom_name}")
    print(f"  Materiales requeridos (para 50 uds):")
    for item in bom_doc.items:
        total_qty = item.qty * 50
        print(f"    • {item.item_code}: {total_qty:,.1f} {item.uom}")


# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT — bench execute gcma_kiosco.setup.test_data.run
# ═══════════════════════════════════════════════════════════════════════════

def run():
    """Ejecuta la creación de stock de prueba y Work Order."""
    print("=" * 60)
    print("  GCMA — Test Data (Stock + Work Order)")
    print("=" * 60)

    create_test_stock()
    create_test_work_order()

    print("\n" + "=" * 60)
    print("  ✓ TEST DATA COMPLETADO")
    print("  → Ejecuta EP2: GET get_tareas?company=Peintures du Maroc SARL")
    print("  → Ejecuta EP3: POST validar_material con qr_data del lote")
    print("=" * 60)
