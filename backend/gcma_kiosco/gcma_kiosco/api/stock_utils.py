"""
Módulo Utilitario de Stock para GCMA Kiosco.

Provee la única fuente de la verdad para consultar saldos y movimientos de lotes/ítems 
resolviendo las particularidades de ERPNext v16 (mezcla de Serial and Batch Entry y Stock Ledger Entry).
"""

import frappe
from frappe.utils import flt, get_datetime

def get_stock_lote_almacen(item_code: str, warehouse: str, batch_no: str = None) -> float:
    """
    Consolida el stock de un ítem (y opcionalmente un lote específico) en un almacén dado.
    Si se proporciona `batch_no`, consulta de `Serial and Batch Entry` (con fallback a `SLE`).
    Si no se proporciona `batch_no` (ítem no loteado), simplemente lee el `actual_qty` en la tabla `Bin`.
    """
    if not item_code or not warehouse:
        return 0.0

    # 1. Ítem no loteado -> Consultar tabla Bin directamente (más rápido y seguro)
    if not batch_no:
        qty = frappe.db.get_value(
            "Bin", 
            {"item_code": item_code, "warehouse": warehouse}, 
            "actual_qty"
        )
        return flt(qty)

    # 2. Ítem loteado -> Calcular desde Serial and Batch Entry + SLE Legacy
    bundle_rows = frappe.db.sql(
        """
        SELECT
            SUM(CASE WHEN IFNULL(sbe.is_outward, 0) = 1 THEN -ABS(sbe.qty) ELSE sbe.qty END) AS qty
        FROM `tabSerial and Batch Entry` sbe
        INNER JOIN `tabSerial and Batch Bundle` bundle ON bundle.name = sbe.parent
        WHERE sbe.item_code = %s
          AND sbe.warehouse = %s
          AND sbe.batch_no = %s
          AND sbe.is_cancelled = 0
        """,
        (item_code, warehouse, batch_no),
        as_dict=True,
    )
    
    qty_bundle = flt(bundle_rows[0].qty) if bundle_rows and bundle_rows[0].qty else 0.0

    legacy_rows = frappe.db.sql(
        """
        SELECT
            SUM(sle.actual_qty) AS qty
        FROM `tabStock Ledger Entry` sle
        WHERE sle.item_code = %s
          AND sle.warehouse = %s
          AND sle.batch_no = %s
          AND sle.is_cancelled = 0
          AND IFNULL(sle.serial_and_batch_bundle, '') = ''
        """,
        (item_code, warehouse, batch_no),
        as_dict=True,
    )

    qty_legacy = flt(legacy_rows[0].qty) if legacy_rows and legacy_rows[0].qty else 0.0

    return qty_bundle + qty_legacy

def get_stock_lote_detallado(item_code: str, batch_no: str):
    """
    Devuelve una lista de almacenes donde el lote tiene stock positivo,
    consolidando fuentes v16 + legacy.
    Retorna: list[dict(warehouse, qty)]
    """
    stock_map = {}

    bundle_rows = frappe.db.sql(
        """
        SELECT
            sbe.warehouse,
            SUM(CASE WHEN IFNULL(sbe.is_outward, 0) = 1 THEN -ABS(sbe.qty) ELSE sbe.qty END) AS qty
        FROM `tabSerial and Batch Entry` sbe
        INNER JOIN `tabSerial and Batch Bundle` bundle ON bundle.name = sbe.parent
        WHERE sbe.item_code = %s
          AND sbe.batch_no = %s
          AND sbe.is_cancelled = 0
        GROUP BY sbe.warehouse
        """,
        (item_code, batch_no),
        as_dict=True,
    )

    legacy_rows = frappe.db.sql(
        """
        SELECT
            sle.warehouse,
            SUM(sle.actual_qty) AS qty
        FROM `tabStock Ledger Entry` sle
        WHERE sle.item_code = %s
          AND sle.batch_no = %s
          AND sle.is_cancelled = 0
          AND IFNULL(sle.serial_and_batch_bundle, '') = ''
        GROUP BY sle.warehouse
        """,
        (item_code, batch_no),
        as_dict=True,
    )

    for row in bundle_rows:
        warehouse = row.warehouse
        stock_map[warehouse] = flt(stock_map.get(warehouse, 0)) + flt(row.qty)

    for row in legacy_rows:
        warehouse = row.warehouse
        stock_map[warehouse] = flt(stock_map.get(warehouse, 0)) + flt(row.qty)

    rows = []
    for warehouse, qty in stock_map.items():
        qty = round(flt(qty), 2)
        if qty > 0:
            rows.append({"warehouse": warehouse, "qty": qty})

    rows.sort(key=lambda r: r["warehouse"])
    return rows
