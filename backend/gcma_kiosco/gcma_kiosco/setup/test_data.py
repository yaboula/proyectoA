"""
GCMA — Test Data para pruebas manuales de caos, Poka-Yoke y E2E contable.

Ejecutar con:
    bench execute gcma_kiosco.setup.test_data.run

Prerequisito: haber ejecutado seed_data.run y seed_data.submit_bom

El flujo hace reset de la demo anterior y vuelve a crear un entorno repetible:
  1. Elimina WO / Stock Entries / Comments de test previos
  2. Inyecta stock válido para happy path
  3. Inyecta fixtures de caos (lote caducado + PT con lote propio)
  4. Crea una Work Order fresca en estado In Process
"""

import frappe
from frappe.utils import today, add_days, add_years


COMPANY = "Peintures du Maroc SARL"
ABBR = "PDM"
WH_MP = f"Materia Prima Aprobada - {ABBR}"
WH_WIP = f"Planta Mezclas WIP - {ABBR}"
WH_QA_PT = f"Cuarentena PT - {ABBR}"
PT_CODE = "PT-PIN-BLC-MAT-20L"

TEST_STOCK_REMARK = "Test Data — Stock ampliado 2000 Kg por MP"
CHAOS_STOCK_REMARK = "Test Data — Stock caos / edge cases"
KIOSCO_COMMENT_PREFIX = "Consommation enregistrée via Kiosco"

VALID_BATCHES = [
    ("MP-RES-ALK-G70", "LOTE-TEST-RES-001", 2000.0, 25.00),
    ("MP-PIG-TIO2-R902", "LOTE-TEST-PIG-001", 2000.0, 18.00),
    ("MP-SOL-WSPI-STD", "LOTE-TEST-SOL-001", 2000.0, 12.00),
    ("MP-H2O-DESMIN", "LOTE-TEST-H2O-001", 2000.0, 0.50),
]


def _exists(doctype: str, name: str) -> bool:
    return frappe.db.exists(doctype, name)


def _ensure_batch(item_code: str, batch_id: str, expiry_date=None):
    if _exists("Batch", batch_id):
        batch = frappe.get_doc("Batch", batch_id)
        batch.item = item_code
        batch.expiry_date = expiry_date
        batch.save(ignore_permissions=True)
        print(f"  ✓ Batch '{batch_id}' ya existe / actualizado.")
        return

    batch = frappe.new_doc("Batch")
    batch.batch_id = batch_id
    batch.item = item_code
    if expiry_date:
        batch.expiry_date = expiry_date
    batch.insert(ignore_permissions=True)
    print(f"  + Batch '{batch_id}' creado.")


def _cancel_and_delete(doctype: str, name: str):
    if not _exists(doctype, name):
        return

    doc = frappe.get_doc(doctype, name)
    if getattr(doc, "docstatus", 0) == 1:
        doc.cancel()

    frappe.delete_doc(doctype, name, ignore_permissions=True, force=1)


def _stock_entry_reset_priority(stock_entry_name: str) -> tuple[int, str]:
    purpose, remarks = frappe.db.get_value(
        "Stock Entry",
        stock_entry_name,
        ["purpose", "remarks"],
    ) or (None, None)

    if purpose == "Manufacture":
        return (0, stock_entry_name)
    if purpose == "Material Transfer for Manufacture":
        return (1, stock_entry_name)
    if remarks == CHAOS_STOCK_REMARK:
        return (2, stock_entry_name)
    if remarks == TEST_STOCK_REMARK:
        return (3, stock_entry_name)
    return (4, stock_entry_name)


def reset_demo_state():
    """Limpia la demo previa para volver a un estado repetible."""
    print("\n──── 1/4  Reset de Demo Anterior ────")

    work_orders = frappe.get_all(
        "Work Order",
        filters={"production_item": PT_CODE, "company": COMPANY},
        pluck="name",
    )

    if frappe.db.exists("DocType", "Job Card") and work_orders:
        job_cards = frappe.get_all(
            "Job Card",
            filters={"work_order": ["in", work_orders]},
            pluck="name",
        )
        for job_card in job_cards:
            _cancel_and_delete("Job Card", job_card)
            print(f"  - Job Card '{job_card}' eliminada.")

    stock_entries = set(
        frappe.get_all(
            "Stock Entry",
            filters={"remarks": ["in", [TEST_STOCK_REMARK, CHAOS_STOCK_REMARK]]},
            pluck="name",
        )
    )
    if work_orders:
        stock_entries.update(
            frappe.get_all(
                "Stock Entry",
                filters={"work_order": ["in", work_orders]},
                pluck="name",
            )
        )

    for stock_entry in sorted(stock_entries, key=_stock_entry_reset_priority):
        _cancel_and_delete("Stock Entry", stock_entry)
        print(f"  - Stock Entry '{stock_entry}' eliminada.")

    if work_orders:
        comments = frappe.get_all(
            "Comment",
            filters={
                "reference_doctype": "Work Order",
                "reference_name": ["in", work_orders],
            },
            fields=["name", "content"],
        )
        for comment in comments:
            if (comment.content or "").startswith(KIOSCO_COMMENT_PREFIX):
                frappe.delete_doc("Comment", comment.name, ignore_permissions=True, force=1)
                print(f"  - Comment '{comment.name}' eliminado.")

    for work_order in work_orders:
        _cancel_and_delete("Work Order", work_order)
        print(f"  - Work Order '{work_order}' eliminada.")

    for _, batch_id, _, _ in VALID_BATCHES:
        if _exists("Batch", batch_id):
            frappe.delete_doc("Batch", batch_id, ignore_permissions=True, force=1)
            print(f"  - Batch '{batch_id}' eliminado.")

    for batch_id in ["LOTE-CHAOS-RES-EXP-001", "LOTE-CHAOS-PT-001"]:
        if _exists("Batch", batch_id):
            frappe.delete_doc("Batch", batch_id, ignore_permissions=True, force=1)
            print(f"  - Batch '{batch_id}' eliminado.")

    frappe.db.commit()


def create_test_stock():
    """Inyecta stock válido para el happy path del kiosco."""
    print("\n──── 2/4  Stock Happy Path ────")

    posting_date = today()
    expiry_date = add_years(posting_date, 1)

    for item_code, batch_id, _, _ in VALID_BATCHES:
        _ensure_batch(item_code, batch_id, expiry_date)

    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = "Material Receipt"
    se.company = COMPANY
    se.posting_date = posting_date
    se.set_posting_time = 1
    se.posting_time = "09:00:00"
    se.remarks = TEST_STOCK_REMARK

    for item_code, batch_id, qty, rate in VALID_BATCHES:
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


def create_chaos_fixtures():
    """Crea datos específicos para edge cases manuales."""
    print("\n──── 3/4  Fixtures de Caos ────")

    posting_date = today()
    _ensure_batch("MP-RES-ALK-G70", "LOTE-CHAOS-RES-EXP-001", add_days(posting_date, -1))
    _ensure_batch(PT_CODE, "LOTE-CHAOS-PT-001", add_years(posting_date, 1))

    # El lote caducado debe existir para EP3, pero ERPNext bloquea recibir stock
    # en un batch vencido. Por eso solo inyectamos stock para el QR de material
    # equivocado (PT) y dejamos el batch expirado como metadata de validación.

    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = "Material Receipt"
    se.company = COMPANY
    se.posting_date = posting_date
    se.set_posting_time = 1
    se.posting_time = "09:10:00"
    se.remarks = CHAOS_STOCK_REMARK

    se.append("items", {
        "item_code": PT_CODE,
        "qty": 5.0,
        "t_warehouse": WH_QA_PT,
        "batch_no": "LOTE-CHAOS-PT-001",
        "basic_rate": 280.00,
    })

    se.insert(ignore_permissions=True)
    se.submit()
    print(f"  + Stock Entry '{se.name}' creado y submitted.")
    print("  + QR caos listo: PT-PIN-BLC-MAT-20L|LOTE-CHAOS-PT-001")
    print("  + QR lote caducado listo: MP-RES-ALK-G70|LOTE-CHAOS-RES-EXP-001")


def create_test_work_order():
    """Crea una Work Order fresca para el flujo manual completo."""
    print("\n──── 4/4  Work Order de Prueba ────")

    bom_name = frappe.db.get_value(
        "BOM",
        {"item": PT_CODE, "is_active": 1, "is_default": 1, "docstatus": 1},
        "name",
    )
    if not bom_name:
        raise frappe.ValidationError(
            "No hay BOM submitted. Ejecuta primero: bench execute gcma_kiosco.setup.seed_data.submit_bom"
        )

    wo = frappe.new_doc("Work Order")
    wo.production_item = PT_CODE
    wo.company = COMPANY
    wo.qty = 50
    wo.bom_no = bom_name
    wo.wip_warehouse = WH_WIP
    wo.fg_warehouse = WH_QA_PT
    wo.stock_uom = "Nos"
    wo.planned_start_date = today()
    wo.use_multi_level_bom = 0
    wo.insert(ignore_permissions=True)
    wo.submit()
    frappe.db.set_value("Work Order", wo.name, "status", "In Process")
    frappe.db.commit()

    print(f"  + Work Order '{wo.name}' creada y puesta en In Process.")
    return wo.name


def print_test_matrix(work_order: str):
    print("\n" + "=" * 68)
    print("  ✓ ENTORNO DE PRUEBAS PREPARADO")
    print(f"  Work Order demo: {work_order}")
    print("\n  QRs manuales para caos / Poka-Yoke:")
    print("    Happy path:")
    print("      • MP-RES-ALK-G70|LOTE-TEST-RES-001")
    print("      • MP-PIG-TIO2-R902|LOTE-TEST-PIG-001")
    print("      • MP-SOL-WSPI-STD|LOTE-TEST-SOL-001")
    print("      • MP-H2O-DESMIN|LOTE-TEST-H2O-001")
    print("    Edge cases:")
    print("      • Tarjeta empleado como basura: OP-2026-BADGE-00042")
    print("      • Material equivocado: PT-PIN-BLC-MAT-20L|LOTE-CHAOS-PT-001")
    print("      • Lote caducado: MP-RES-ALK-G70|LOTE-CHAOS-RES-EXP-001")
    print("      • Batch inexistente: MP-RES-ALK-G70|LOTE-INEXISTENTE-999")
    print("      • Batch cruzado: MP-RES-ALK-G70|LOTE-TEST-PIG-001")
    print("\n  Verificación contable esperada:")
    print("    • EP4 debe crear automáticamente un Stock Entry de transferencia a WIP")
    print("      y un Stock Entry de Manufacture ligados a la Work Order.")
    print("    • Tras finalizar desde el kiosco, verificar:")
    print("      1. Work Order = Completed")
    print("      2. MP transferida/consumida en los almacenes correctos")
    print("      3. FG entra en Cuarentena PT - PDM, no en ventas")
    print("=" * 68)


def run():
    """Resetea e inyecta un entorno repetible para pruebas manuales."""
    print("=" * 68)
    print("  GCMA — Test Data (Reset + Chaos + Work Order)")
    print("=" * 68)

    reset_demo_state()
    create_test_stock()
    create_chaos_fixtures()
    work_order = create_test_work_order()
    print_test_matrix(work_order)
