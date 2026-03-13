"""
GCMA / Maroc B2B — Analitica gerencial Sprint 12.

Contrato API objetivo:
- GET  /api/method/maroc_b2b.api.gerencial.get_panel_gerencial_360
- GET  /api/method/maroc_b2b.api.gerencial.get_cobertura_mapa
- GET  /api/method/maroc_b2b.api.gerencial.get_reporte_fotos_competencia
- POST /api/method/maroc_b2b.api.gerencial.run_alerta_abandono_clientes
"""

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime, timedelta
from typing import Any

import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime, today

_CACHE_TTL_SECONDS = 300


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_date(value: str | None) -> date:
    return getdate(value) if value else getdate(today())


def _safe_customer_value(customer: str, fieldname: str, default: Any = None) -> Any:
    try:
        value = frappe.db.get_value("Customer", customer, fieldname)
        return default if value is None else value
    except Exception:
        return default


def _has_checkin_visita_table() -> bool:
    try:
        return bool(frappe.db.table_exists("tabCheckIn_Visita"))
    except Exception:
        return False


def _is_authorized_manager() -> bool:
    if frappe.session.user == "Administrator":
        return True

    allowed_roles = {"System Manager", "Sales Manager", "Accounts Manager"}
    return bool(set(frappe.get_roles()) & allowed_roles)


def _require_manager():
    if not _is_authorized_manager():
        frappe.throw(_("Acceso denegado al panel gerencial"), frappe.PermissionError)


def _cache_key(prefix: str, ref_date: date) -> str:
    return f"b2b:{prefix}:{ref_date.isoformat()}"


def _get_top_customers_by_ytd_billing(ref_date: date, percentile: float = 0.2) -> list[str]:
    year_start = date(ref_date.year, 1, 1)
    rows = frappe.db.sql(
        """
        select si.customer as customer, sum(si.base_grand_total) as total_ytd
        from `tabSales Invoice` si
        where si.docstatus = 1
          and si.posting_date between %(year_start)s and %(ref_date)s
        group by si.customer
        order by total_ytd desc
        """,
        {"year_start": year_start, "ref_date": ref_date},
        as_dict=True,
    )

    if not rows:
        return []

    limit = max(1, int(len(rows) * percentile))
    return [row.customer for row in rows[:limit] if row.customer]


def _get_churn_days_for_customer(customer: str) -> int:
    tipo = None

    default_days = int(_to_float(frappe.conf.get("b2b_churn_days_default", 40), 40))
    by_tipo = frappe.conf.get("b2b_churn_days_by_tipo", {})

    if isinstance(by_tipo, str):
        try:
            by_tipo = json.loads(by_tipo)
        except Exception:
            by_tipo = {}

    if isinstance(by_tipo, dict) and tipo in by_tipo:
        return int(_to_float(by_tipo.get(tipo), default_days))

    return default_days


def _scorecard_rows(ref_date: date) -> list[dict[str, Any]]:
    year_start = date(ref_date.year, 1, 1)
    rows = frappe.db.sql(
        """
        select
            c.name as customer,
            c.customer_name as customer_name,
            ifnull(sum(si.base_grand_total), 0) as facturacion_ytd,
            max(si.posting_date) as ultima_compra,
            count(distinct date_format(si.posting_date, '%%Y-%%m')) as frecuencia_mensual
        from `tabCustomer` c
        left join `tabSales Invoice` si
            on si.customer = c.name
           and si.docstatus = 1
           and si.posting_date between %(year_start)s and %(ref_date)s
        group by c.name, c.customer_name
        order by facturacion_ytd desc, c.name asc
        """,
        {"year_start": year_start, "ref_date": ref_date},
        as_dict=True,
    )

    scorecard = []
    for row in rows:
        ultima_compra = row.ultima_compra
        dias_sin_compra = None
        if ultima_compra:
            dias_sin_compra = (ref_date - getdate(ultima_compra)).days

        customer_fields = frappe.db.get_value(
            "Customer",
            row.customer,
            ["name", "customer_name"],
            as_dict=True,
        ) or {}

        tipo_drogueria = None
        deuda_vencida = 0
        deuda_total = 0
        dias_peor_mora = 0

        scorecard.append(
            {
                "customer": customer_fields.get("name") or row.customer,
                "customer_name": customer_fields.get("customer_name") or row.customer_name,
                "tipo_drogueria": tipo_drogueria,
                "facturacion_ytd": flt(row.facturacion_ytd, 2),
                "deuda_vencida": flt(deuda_vencida, 2),
                "deuda_total": flt(deuda_total, 2),
                "dias_peor_mora": dias_peor_mora,
                "frecuencia_mensual": int(_to_float(row.frecuencia_mensual, 0)),
                "ultima_compra": str(ultima_compra) if ultima_compra else None,
                "dias_sin_compra": dias_sin_compra,
            }
        )

    return scorecard


def _hit_rate_rows(ref_date: date) -> dict[str, Any]:
    if not _has_checkin_visita_table():
        return {
            "total_visitas": 0,
            "visitas_con_pedido": 0,
            "visitas_sin_pedido": 0,
            "hit_rate": 0.0,
            "por_comercial": [],
        }

    start_dt = datetime.combine(ref_date, datetime.min.time())
    end_dt = datetime.combine(ref_date, datetime.max.time())

    checkins = frappe.get_all(
        "CheckIn_Visita",
        filters={"timestamp_in": ["between", [start_dt, end_dt]]},
        fields=["name", "cliente", "comercial", "timestamp_in"],
        limit=10000,
    )

    with_order = 0
    without_order = 0

    by_comercial: dict[str, dict[str, int]] = {}

    for row in checkins:
        fecha = getdate(row.timestamp_in)
        has_order = bool(
            frappe.db.exists(
                "Sales Order",
                {
                    "customer": row.cliente,
                    "transaction_date": fecha,
                    "owner": row.comercial,
                    "docstatus": ["in", [0, 1]],
                },
            )
            or frappe.db.exists(
                "Sales Order",
                {
                    "customer": row.cliente,
                    "transaction_date": fecha,
                    "docstatus": ["in", [0, 1]],
                },
            )
        )

        key = row.comercial or "N/A"
        by_comercial.setdefault(key, {"with_order": 0, "without_order": 0})

        if has_order:
            with_order += 1
            by_comercial[key]["with_order"] += 1
        else:
            without_order += 1
            by_comercial[key]["without_order"] += 1

    total = with_order + without_order
    rate = (with_order / total) if total else 0.0

    return {
        "total_visitas": total,
        "visitas_con_pedido": with_order,
        "visitas_sin_pedido": without_order,
        "hit_rate": round(rate, 4),
        "por_comercial": [
            {
                "comercial": comercial,
                "visitas_con_pedido": data["with_order"],
                "visitas_sin_pedido": data["without_order"],
            }
            for comercial, data in by_comercial.items()
        ],
    }


def _cobertura_rows(ref_date: date) -> list[dict[str, Any]]:
    if not _has_checkin_visita_table():
        return []

    start_dt = datetime.combine(ref_date, datetime.min.time())
    end_dt = datetime.combine(ref_date, datetime.max.time())

    checkins = frappe.get_all(
        "CheckIn_Visita",
        filters={"timestamp_in": ["between", [start_dt, end_dt]]},
        fields=[
            "name",
            "cliente",
            "comercial",
            "timestamp_in",
            "gps_lat_capturada",
            "gps_lng_capturada",
            "es_visita_valida",
        ],
        order_by="timestamp_in asc",
        limit=10000,
    )

    rows: list[dict[str, Any]] = []
    for row in checkins:
        rows.append(
            {
                "checkin_id": row.name,
                "cliente": row.cliente,
                "comercial": row.comercial,
                "lat": _to_float(row.gps_lat_capturada),
                "lng": _to_float(row.gps_lng_capturada),
                "time": str(row.timestamp_in),
                "estado_visita": "valida" if int(row.es_visita_valida or 0) == 1 else "desviada",
                "es_desviacion": int(row.es_visita_valida or 0) == 0,
            }
        )

    return rows


def _competitor_photo_rows(limit: int = 100) -> list[dict[str, Any]]:
    rows = frappe.db.sql(
        """
        select
            f.file_url,
            f.creation,
            f.attached_to_doctype,
            f.attached_to_name,
            i.description as issue_description,
            i.raised_by as raised_by,
            i.subject as issue_subject
        from `tabFile` f
        left join `tabIssue` i
          on i.name = f.attached_to_name
         and f.attached_to_doctype = 'Issue'
        where f.attached_to_doctype in ('Issue', 'CheckIn_Visita')
          and (
            lower(ifnull(i.description, '')) like '%%competencia%%'
            or lower(ifnull(i.description, '')) like '%%precio%%'
            or lower(ifnull(i.subject, '')) like '%%competencia%%'
            or lower(ifnull(i.subject, '')) like '%%precio%%'
          )
        order by f.creation desc
        limit %(limit)s
        """,
        {"limit": int(max(1, min(limit, 500)))},
        as_dict=True,
    )

    return [
        {
            "file_url": row.file_url,
            "created_at": str(row.creation),
            "origen_doctype": row.attached_to_doctype,
            "origen_docname": row.attached_to_name,
            "descripcion": row.issue_description,
            "subido_por": row.raised_by,
            "asunto": row.issue_subject,
        }
        for row in rows
        if row.file_url
    ]


@frappe.whitelist()
def get_cobertura_mapa(fecha: str | None = None):
    """Sprint 12 — Cobertura GPS por comercial para la fecha solicitada."""
    _require_manager()
    ref_date = _to_date(fecha)

    cache = frappe.cache()
    key = _cache_key("cobertura_mapa", ref_date)
    cached = cache.get_value(key)
    if cached:
        return cached

    payload = {
        "fecha": ref_date.isoformat(),
        "rows": _cobertura_rows(ref_date),
    }
    cache.set_value(key, payload, expires_in_sec=_CACHE_TTL_SECONDS)
    return payload


@frappe.whitelist()
def get_panel_gerencial_360(fecha: str | None = None):
    """Sprint 12 — Scorecard + hit-rate + cobertura resumida para dashboard 360."""
    _require_manager()
    ref_date = _to_date(fecha)

    cache = frappe.cache()
    key = _cache_key("panel_360", ref_date)
    cached = cache.get_value(key)
    if cached:
        return cached

    scorecard = _scorecard_rows(ref_date)
    hit_rate = _hit_rate_rows(ref_date)
    cobertura = _cobertura_rows(ref_date)

    payload = {
        "fecha": ref_date.isoformat(),
        "generated_at": now_datetime().isoformat(),
        "scorecard": scorecard,
        "hit_rate": hit_rate,
        "cobertura_resumen": {
            "total_checkins": len(cobertura),
            "desviaciones": sum(1 for row in cobertura if row["es_desviacion"]),
        },
    }

    cache.set_value(key, payload, expires_in_sec=_CACHE_TTL_SECONDS)
    return payload


@frappe.whitelist()
def get_reporte_fotos_competencia(limit: int = 100):
    """Sprint 12 — Reporte simple de fotos de precios de competencia."""
    _require_manager()
    rows = _competitor_photo_rows(limit=limit)
    return {
        "total": len(rows),
        "rows": rows,
    }


@frappe.whitelist()
def export_scorecard_csv(fecha: str | None = None):
    """Exporta scorecard a CSV para analisis directivo."""
    _require_manager()
    ref_date = _to_date(fecha)
    rows = _scorecard_rows(ref_date)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "customer",
            "customer_name",
            "tipo_drogueria",
            "facturacion_ytd",
            "deuda_vencida",
            "deuda_total",
            "dias_peor_mora",
            "frecuencia_mensual",
            "ultima_compra",
            "dias_sin_compra",
        ]
    )

    for row in rows:
        writer.writerow(
            [
                row["customer"],
                row["customer_name"],
                row["tipo_drogueria"],
                row["facturacion_ytd"],
                row["deuda_vencida"],
                row["deuda_total"],
                row["dias_peor_mora"],
                row["frecuencia_mensual"],
                row["ultima_compra"] or "",
                row["dias_sin_compra"] if row["dias_sin_compra"] is not None else "",
            ]
        )

    content = output.getvalue()
    output.close()

    return {
        "filename": f"scorecard_b2b_{ref_date.isoformat()}.csv",
        "content_type": "text/csv",
        "content": content,
    }


def _collect_abandono_alerts(ref_date: date) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []

    for customer in _get_top_customers_by_ytd_billing(ref_date, percentile=0.2):
        latest_order = frappe.db.get_value(
            "Sales Order",
            {"customer": customer, "docstatus": ["in", [0, 1]]},
            "transaction_date",
            order_by="transaction_date desc",
        )

        if not latest_order:
            continue

        days_without_buy = (ref_date - getdate(latest_order)).days
        threshold = _get_churn_days_for_customer(customer)

        if days_without_buy > threshold:
            alerts.append(
                {
                    "customer": customer,
                    "ultima_compra": str(latest_order),
                    "dias_sin_compra": days_without_buy,
                    "umbral_dias": threshold,
                }
            )

    return alerts


def _send_abandono_notifications(alerts: list[dict[str, Any]]) -> list[str]:
    if not alerts:
        return []

    manager_users = frappe.get_all(
        "Has Role",
        filters={"role": "Sales Manager", "parenttype": "User"},
        fields=["parent"],
    )
    recipients = sorted(set(row.parent for row in manager_users if row.parent and row.parent != "Administrator"))

    if not recipients:
        fallback = frappe.db.get_single_value("System Settings", "email_addr")
        if fallback:
            recipients = [fallback]

    if not recipients:
        return []

    lines = [
        "Clientes Top 20% con riesgo de abandono detectados:",
        "",
    ]

    for row in alerts:
        lines.append(
            f"- {row['customer']}: {row['dias_sin_compra']} dias sin compra (umbral {row['umbral_dias']})"
        )

    message = "<br>".join(lines)
    subject = "Alerta de Abandono B2B"

    try:
        frappe.sendmail(recipients=recipients, subject=subject, message=message)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "run_alerta_abandono_clientes: sendmail")

    for user in recipients:
        try:
            frappe.get_doc(
                {
                    "doctype": "Notification Log",
                    "for_user": user,
                    "type": "Alert",
                    "subject": subject,
                    "email_content": message,
                }
            ).insert(ignore_permissions=True)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "run_alerta_abandono_clientes: notification")

    return recipients


@frappe.whitelist()
def run_alerta_abandono_clientes(fecha: str | None = None, enforce_permissions: int = 1):
    """Scheduler/manual — alerta de churn para clientes top 20%."""
    if int(enforce_permissions or 0) == 1:
        _require_manager()
    ref_date = _to_date(fecha)

    alerts = _collect_abandono_alerts(ref_date)
    recipients = _send_abandono_notifications(alerts)

    result = {
        "fecha": ref_date.isoformat(),
        "total_alertas": len(alerts),
        "recipients": recipients,
        "alerts": alerts,
    }

    frappe.logger("gcma_kiosco").info(
        "[Sprint12] run_alerta_abandono_clientes fecha=%s total=%s recipients=%s",
        result["fecha"],
        result["total_alertas"],
        ",".join(recipients) if recipients else "none",
    )

    return result


def scheduler_alerta_abandono_clientes():
    """Hook scheduler daily: ejecuta alertas de abandono sin UI."""
    try:
        run_alerta_abandono_clientes(
            fecha=(getdate(today()) - timedelta(days=1)).isoformat(),
            enforce_permissions=0,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "scheduler_alerta_abandono_clientes")
