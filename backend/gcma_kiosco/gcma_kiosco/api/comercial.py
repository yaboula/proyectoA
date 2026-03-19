"""
GCMA / Maroc B2B — Endpoints comerciales (Sprint 07-11).

Contrato API objetivo:
- GET  /api/method/maroc_b2b.api.comercial.get_catalogo_stock
- GET  /api/method/maroc_b2b.api.comercial.get_ruta_dia
- POST /api/method/maroc_b2b.api.comercial.post_checkin
- GET  /api/method/maroc_b2b.api.comercial.get_estado_cuenta
- POST /api/method/maroc_b2b.api.comercial.post_cobro
- POST /api/method/maroc_b2b.api.comercial.sync_pedidos_offline
- GET  /api/method/maroc_b2b.api.comercial.get_portal_dashboard
- GET  /api/method/maroc_b2b.api.comercial.get_portal_estado_cuenta
- POST /api/method/maroc_b2b.api.comercial.crear_pedido_portal
- POST /api/method/maroc_b2b.api.comercial.create_support_ticket
- GET  /api/method/maroc_b2b.api.comercial.get_loyalty_points
- POST /api/method/maroc_b2b.api.comercial.redimir_puntos
"""

from __future__ import annotations

import base64
import json
import math
from typing import Any, Optional

import frappe
from frappe import _
from frappe.utils import add_days, flt, get_datetime, now_datetime, today


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_json_maybe(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, (dict, list)):
        return value

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            parsed = frappe.parse_json(raw)
            return parsed

    return value


def _get_credit_limit(id_cliente: str) -> float:
    # ERPNext maneja limite de credito en la tabla hija Customer Credit Limit.
    rows = frappe.get_all(
        "Customer Credit Limit",
        filters={"parent": id_cliente, "parenttype": "Customer"},
        fields=["credit_limit"],
    )
    if not rows:
        return 0.0
    return max(_to_float(row.credit_limit) for row in rows)


def _get_deuda_vencida_limit() -> float:
    # Parametrizacion dura: site_config.json -> b2b_deuda_vencida_limite
    configured = frappe.conf.get("b2b_deuda_vencida_limite", 0)
    return max(0.0, _to_float(configured))


def _get_default_company(customer: frappe.model.document.Document) -> str | None:
    if getattr(customer, "default_company", None):
        return customer.default_company

    company = frappe.db.get_single_value("Global Defaults", "default_company")
    if company:
        return company

    fallback = frappe.db.get_value("Company", {}, "name")
    return fallback


def _ensure_customer_exists(id_cliente: str):
    if not id_cliente:
        frappe.throw(_("Parametro obligatorio: id_cliente"))

    if not frappe.db.exists("Customer", id_cliente):
        frappe.throw(_("Cliente no existe: {0}").format(id_cliente))


def _table_exists(table_name: str) -> bool:
    try:
        return bool(frappe.db.table_exists(table_name))
    except Exception:
        return False


def _distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Distancia Haversine para validar geocerca en servidor.
    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def _current_portal_customer() -> str:
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Sesion no valida para Portal B2B"), frappe.PermissionError)

    customer = frappe.db.sql(
        """
                select dl.link_name
                from `tabContact` c
                inner join `tabDynamic Link` dl on dl.parent = c.name
                where c.email_id = %(user)s
                    and dl.parenttype = 'Contact'
                    and dl.link_doctype = 'Customer'

                union

                select dl.link_name
                from `tabContact Email` ce
                inner join `tabDynamic Link` dl on dl.parent = ce.parent
                where ce.email_id = %(user)s
                    and dl.parenttype = 'Contact'
          and dl.link_doctype = 'Customer'
        """,
                {"user": user},
                as_dict=True,
    )

    if customer and customer[0].get("link_name"):
        return customer[0].link_name

    # Fallback: many portal setups enforce tenant scope via User Permission.
    user_perm_customer = frappe.db.get_value(
        "User Permission",
        {"user": user, "allow": "Customer"},
        "for_value",
    )
    if user_perm_customer:
        return user_perm_customer

    frappe.throw(_("Usuario portal sin Customer vinculado"), frappe.PermissionError)


def _resolve_portal_customer(id_cliente: str | None = None) -> str:
    requested_customer = (id_cliente or "").strip()

    # Operarios de kiosco (Employee con sesión activa) o managers pueden acceder
    # a cualquier cliente directamente con id_cliente explícito.
    user = frappe.session.user
    _MANAGER_ROLES = {"System Manager", "Sales Manager", "Accounts Manager"}
    is_manager = (user == "Administrator") or bool(set(frappe.get_roles()) & _MANAGER_ROLES)
    is_kiosco_employee = bool(
        frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
    )

    if (is_manager or is_kiosco_employee) and requested_customer:
        return requested_customer

    # Flujo normal portal B2B: verificar que el usuario está vinculado al cliente
    linked_customer = _current_portal_customer()
    if requested_customer and requested_customer != linked_customer:
        frappe.throw(_("Forbidden: cliente fuera de tenant"), frappe.PermissionError)

    return requested_customer or linked_customer


def _is_customer_blocked_30_days(id_cliente: str) -> tuple[bool, str]:
    customer = frappe.get_doc("Customer", id_cliente)
    deuda_vencida = _to_float(getattr(customer, "deuda_vencida", 0))
    dias_peor_mora = int(_to_float(getattr(customer, "dias_peor_mora", 0), 0))

    blocked = dias_peor_mora > 30 and deuda_vencida > 0
    message = (
        _("Compte bloque: retard superieur a 30 jours. Contactez votre gestionnaire de portefeuille.")
        if blocked
        else ""
    )
    return blocked, message


def _decode_b64_payload(payload: str | None, label: str) -> bytes | None:
    if payload is None:
        return None

    raw = str(payload).strip()
    if not raw:
        return None

    if "," in raw and ";base64" in raw:
        raw = raw.split(",", 1)[1]

    try:
        return base64.b64decode(raw, validate=True)
    except Exception:
        frappe.throw(_("Base64 invalido en {0}").format(label), frappe.ValidationError)


def _save_private_attachment(content: bytes, filename: str, doctype: str, docname: str) -> str:
    file_doc = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": filename,
            "is_private": 1,
            "content": content,
            "attached_to_doctype": doctype,
            "attached_to_name": docname,
        }
    )
    file_doc.insert(ignore_permissions=True)
    return file_doc.file_url


def _get_quality_recipients() -> list[str]:
    users = frappe.get_all(
        "Has Role",
        filters={"role": ["in", ["Quality Manager", "Quality Inspector"]], "parenttype": "User"},
        fields=["parent"],
    )
    recipients = [row.parent for row in users if row.parent and row.parent != "Administrator"]
    return sorted(set(recipients))


def _notify_quality_team(issue_name: str, customer: str, affected_batch: str):
    recipients = _get_quality_recipients()
    if not recipients:
        return

    subject = f"SOS Client B2B: {issue_name}"
    message = (
        f"Nouveau ticket SOS cree par {customer}.<br>"
        f"Issue: <b>{issue_name}</b><br>"
        f"Lot affecte: <b>{affected_batch or 'N/A'}</b>"
    )

    try:
        frappe.sendmail(recipients=recipients, subject=subject, message=message)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "create_support_ticket: sendmail quality")

    for user in recipients:
        try:
            frappe.get_doc(
                {
                    "doctype": "Notification Log",
                    "for_user": user,
                    "type": "Alert",
                    "subject": subject,
                    "email_content": message,
                    "document_type": "Issue",
                    "document_name": issue_name,
                }
            ).insert(ignore_permissions=True)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "create_support_ticket: notification log")


def _get_portal_suggestions(id_cliente: str, limit: int = 5) -> list[dict[str, Any]]:
    purchased = frappe.db.sql(
        """
        select distinct soi.item_code
        from `tabSales Order Item` soi
        inner join `tabSales Order` so on so.name = soi.parent
        where so.customer = %(customer)s
          and so.docstatus = 1
          and soi.item_code is not null
        order by soi.modified desc
        limit 50
        """,
        {"customer": id_cliente},
        as_dict=True,
    )

    purchased_codes = [row.item_code for row in purchased if row.item_code]
    if not purchased_codes:
        return []

    escaped_codes = ", ".join(frappe.db.escape(code) for code in purchased_codes)

    rows = frappe.db.sql(
        f"""
        select soi.item_code, soi.item_name, count(*) as score
        from `tabSales Order Item` soi
        inner join `tabSales Order` so on so.name = soi.parent
        where so.docstatus = 1
          and soi.item_code not in ({escaped_codes})
          and exists (
            select 1
            from `tabSales Order Item` soi2
            where soi2.parent = soi.parent
              and soi2.item_code in ({escaped_codes})
          )
        group by soi.item_code, soi.item_name
        order by score desc, soi.item_code asc
        limit {int(limit)}
        """,
        as_dict=True,
    )

    return [
        {
            "item_code": row.item_code,
            "item_name": row.item_name,
            "score": int(row.score or 0),
        }
        for row in rows
    ]


@frappe.whitelist()
def get_catalogo_stock(
    search: str | None = None,
    warehouse: str | None = None,
    limit: int = 40,
):
    """
    Sprint 07 — Catálogo de ítems con stock proyectado para el comercial en campo.
    Devuelve items activos con precio de venta y stock real disponible.
    """
    limit_value = max(1, min(int(_to_float(limit, 40)), 100))
    search_term = (search or "").strip()

    filters: dict[str, Any] = {"disabled": 0, "is_sales_item": 1}
    if search_term:
        filters["item_name"] = ["like", f"%{search_term}%"]

    items = frappe.get_all(
        "Item",
        filters=filters,
        fields=["name as item_code", "item_name", "item_group", "stock_uom", "description"],
        order_by="item_name asc",
        limit=limit_value,
    )

    if not items:
        return {"items": [], "total": 0}

    # Precio de venta (lista de precios estándar)
    price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"
    item_codes = [it.item_code for it in items]
    prices_rows = frappe.get_all(
        "Item Price",
        filters={"item_code": ["in", item_codes], "price_list": price_list, "selling": 1},
        fields=["item_code", "price_list_rate"],
    )
    prices = {row.item_code: flt(row.price_list_rate, 2) for row in prices_rows}

    # Stock total por item (todos los warehouses o el indicado)
    stock_filters = "where b.item_code in %(codes)s"
    stock_params: dict[str, Any] = {"codes": tuple(item_codes) if len(item_codes) > 1 else (item_codes[0], item_codes[0])}
    if warehouse:
        stock_filters += " and b.warehouse = %(wh)s"
        stock_params["wh"] = warehouse

    stock_rows = frappe.db.sql(
        f"""
        select b.item_code, sum(b.actual_qty) as qty
        from `tabBin` b
        {stock_filters}
        group by b.item_code
        """,
        stock_params,
        as_dict=True,
    )
    stock_map = {row.item_code: flt(row.qty, 2) for row in stock_rows}

    enriched = [
        {
            "item_code": it.item_code,
            "item_name": it.item_name,
            "item_group": it.item_group,
            "uom": it.stock_uom,
            "precio_venta": prices.get(it.item_code, 0.0),
            "stock_disponible": stock_map.get(it.item_code, 0.0),
            "en_stock": stock_map.get(it.item_code, 0.0) > 0,
        }
        for it in items
    ]

    return {"items": enriched, "total": len(enriched), "price_list": price_list}


@frappe.whitelist()
def get_ruta_dia():
    """Sprint 07 — Ruta diaria del comercial autenticado."""
    if not _table_exists("tabRuta_Comercial_Dia"):
        return {"fecha": str(today()), "comercial": frappe.session.user, "rutas": []}

    user = frappe.session.user
    sales_person = frappe.db.get_value("Sales Person", {"user": user}, "name")
    if not sales_person:
        return {"fecha": str(today()), "comercial": user, "rutas": []}

    rutas = frappe.get_all(
        "Ruta_Comercial_Dia",
        filters={"comercial": sales_person, "fecha_ruta": today(), "docstatus": ["in", [0, 1]]},
        fields=["name", "fecha_ruta", "estado"],
        order_by="modified desc",
        limit=1,
    )

    if not rutas:
        return {"fecha": str(today()), "comercial": user, "rutas": []}

    ruta = rutas[0]
    visitas = frappe.get_all(
        "Visitas_Programadas",
        filters={"parent": ruta.name, "parenttype": "Ruta_Comercial_Dia"},
        fields=["cliente", "orden_visita"],
        order_by="orden_visita asc",
    )

    return {
        "fecha": str(ruta.fecha_ruta),
        "comercial": user,
        "ruta_id": ruta.name,
        "estado": ruta.estado,
        "rutas": [
            {
                "id_cliente": row.cliente,
                "orden_visita": int(_to_float(row.orden_visita, 0)),
            }
            for row in visitas
            if row.cliente
        ],
    }


@frappe.whitelist()
def post_checkin(
    id_cliente: str,
    gps_lat_capturada: str,
    gps_lng_capturada: str,
    timestamp: str | None = None,
):
    """Sprint 07 — Registrar check-in y validar geocerca."""
    _ensure_customer_exists(id_cliente)

    lat = _to_float(gps_lat_capturada, None)
    lng = _to_float(gps_lng_capturada, None)
    if lat is None or lng is None:
        frappe.throw(_("Parametros GPS invalidos"), frappe.ValidationError)

    customer = frappe.get_doc("Customer", id_cliente)
    lat_ref = _to_float(getattr(customer, "gps_lat", None), None)
    lng_ref = _to_float(getattr(customer, "gps_lng", None), None)
    geofence_m = _to_float(frappe.conf.get("b2b_geofence_radius_m", 150), 150)

    distancia_m = None
    es_visita_valida = 1
    if lat_ref is not None and lng_ref is not None:
        distancia_m = round(_distance_meters(lat_ref, lng_ref, lat, lng), 2)
        es_visita_valida = 1 if distancia_m <= geofence_m else 0

    checkin_id = None
    if _table_exists("tabCheckIn_Visita"):
        checkin_doc = frappe.get_doc(
            {
                "doctype": "CheckIn_Visita",
                "naming_series": "CHKIN-.YYYY.-.####",
                "cliente": id_cliente,
                "comercial": frappe.session.user,
                "timestamp_in": get_datetime(timestamp) if timestamp else now_datetime(),
                "gps_lat_capturada": str(lat),
                "gps_lng_capturada": str(lng),
                "es_visita_valida": int(es_visita_valida),
            }
        )
        checkin_doc.insert(ignore_permissions=True)
        checkin_id = checkin_doc.name
        frappe.db.commit()

    return {
        "status": "success",
        "checkin_id": checkin_id,
        "id_cliente": id_cliente,
        "es_visita_valida": bool(es_visita_valida),
        "distancia_metros": distancia_m,
        "radio_geocerca_m": geofence_m,
    }


@frappe.whitelist()
def post_cobro(
    id_cliente: str,
    monto: str,
    modo_pago: str,
    referencia: str | None = None,
    fecha: str | None = None,
):
    """Sprint 08 — Registra un cobro (cheque/efectivo) como Payment Entry draft."""
    _ensure_customer_exists(id_cliente)

    amount = _to_float(monto, None)
    if amount is None or amount <= 0:
        frappe.throw(_("El monto debe ser un numero positivo"), frappe.ValidationError)

    modo = (modo_pago or "").strip()
    if not modo:
        frappe.throw(_("Parametro obligatorio: modo_pago"), frappe.ValidationError)

    modos_validos = {"Cheque", "Efectivo", "Virement", "Espece"}
    if modo not in modos_validos:
        frappe.throw(
            _("modo_pago invalido. Valores aceptados: {0}").format(", ".join(sorted(modos_validos))),
            frappe.ValidationError,
        )

    customer = frappe.get_doc("Customer", id_cliente)
    company = _get_default_company(customer)
    if not company:
        frappe.throw(_("No hay company por defecto para el cobro"), frappe.ValidationError)

    # Cuenta de caja/banco según modo de pago
    paid_to_account = frappe.db.get_value(
        "Account",
        {"account_type": "Cash" if modo in ("Efectivo", "Espece") else "Bank", "company": company, "is_group": 0},
        "name",
    )
    if not paid_to_account:
        frappe.throw(
            _("No se encontro cuenta de {0} para la empresa {1}").format(modo, company),
            frappe.ValidationError,
        )

    receivable_account = frappe.db.get_value(
        "Account",
        {"account_type": "Receivable", "company": company, "is_group": 0},
        "name",
    )
    if not receivable_account:
        frappe.throw(_("No se encontro cuenta por cobrar para la empresa {0}").format(company), frappe.ValidationError)

    ref_no = (referencia or "").strip() or f"COBRO-PWA-{frappe.generate_hash(length=6).upper()}"

    payment_entry = frappe.get_doc(
        {
            "doctype": "Payment Entry",
            "payment_type": "Receive",
            "party_type": "Customer",
            "party": id_cliente,
            "company": company,
            "posting_date": fecha or frappe.utils.today(),
            "paid_amount": amount,
            "received_amount": amount,
            "paid_to": paid_to_account,
            "paid_from": receivable_account,
            "mode_of_payment": modo,
            "reference_no": ref_no,
            "reference_date": fecha or frappe.utils.today(),
            "remarks": f"Cobro registrado desde PWA Comercial B2B — {modo}",
        }
    )

    payment_entry.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "payment_entry": payment_entry.name,
        "monto": flt(amount, 2),
        "modo_pago": modo,
        "referencia": ref_no,
    }


@frappe.whitelist()
def get_estado_cuenta(id_cliente: str):
    """Contrato 1.3 — Estado de cuenta para bloqueo previo a venta."""
    _ensure_customer_exists(id_cliente)

    customer = frappe.get_doc("Customer", id_cliente)

    deuda_total = _to_float(getattr(customer, "deuda_total", 0))
    deuda_vencida = _to_float(getattr(customer, "deuda_vencida", 0))
    dias_peor_mora = int(_to_float(getattr(customer, "dias_peor_mora", 0), 0))

    limite_credito = _get_credit_limit(id_cliente)
    limite_deuda_vencida = _get_deuda_vencida_limit()

    bloqueado_para_venta = deuda_vencida > limite_deuda_vencida
    mensaje_bloqueo = (
        _("Deuda vencida excede el limite permitido.")
        if bloqueado_para_venta
        else ""
    )

    return {
        "limite_credito": flt(limite_credito, 2),
        "deuda_total": flt(deuda_total, 2),
        "deuda_vencida": flt(deuda_vencida, 2),
        "dias_peor_mora": dias_peor_mora,
        "bloqueado_para_venta": bool(bloqueado_para_venta),
        "mensaje_bloqueo": mensaje_bloqueo,
    }


@frappe.whitelist()
def sync_pedidos_offline(pedidos=None):
    """Contrato 1.4 — Sincronizacion bulk de pedidos offline a Sales Order."""
    payload = _parse_json_maybe(pedidos)

    if payload is None:
        payload = _parse_json_maybe(frappe.form_dict.get("pedidos"))

    if payload is None:
        payload = []

    if not isinstance(payload, list):
        frappe.throw(_("El payload 'pedidos' debe ser una lista"))

    synced = 0
    failed = 0
    ids_creados: list[str] = []

    for idx, pedido in enumerate(payload):
        savepoint = f"sync_pedido_{idx}"
        frappe.db.savepoint(savepoint)

        try:
            if not isinstance(pedido, dict):
                raise frappe.ValidationError(_("Pedido invalido"))

            id_cliente = str(pedido.get("id_cliente") or "").strip()
            items = pedido.get("items")
            _ensure_customer_exists(id_cliente)

            if not isinstance(items, list) or not items:
                raise frappe.ValidationError(_("Pedido sin items"))

            customer = frappe.get_doc("Customer", id_cliente)
            company = _get_default_company(customer)
            if not company:
                raise frappe.ValidationError(_("No hay company por defecto para el pedido"))

            delivery_date = add_days(today(), 1)

            so_items = []
            for line in items:
                if not isinstance(line, dict):
                    raise frappe.ValidationError(_("Linea de item invalida"))

                item_code = str(line.get("item_code") or "").strip()
                qty = _to_float(line.get("qty"), 0)

                if not item_code or qty <= 0:
                    raise frappe.ValidationError(_("Item o qty invalidos en pedido"))

                so_items.append(
                    {
                        "item_code": item_code,
                        "qty": qty,
                        "delivery_date": delivery_date,
                    }
                )

            so_data = {
                "doctype": "Sales Order",
                "customer": id_cliente,
                "company": company,
                "transaction_date": today(),
                "delivery_date": delivery_date,
                "order_type": "Sales",
                "items": so_items,
            }

            if getattr(customer, "default_price_list", None):
                so_data["selling_price_list"] = customer.default_price_list

            sales_order = frappe.get_doc(so_data)
            sales_order.insert(ignore_permissions=True)

            ids_creados.append(sales_order.name)
            synced += 1

        except Exception:
            frappe.db.rollback(save_point=savepoint)
            failed += 1
            frappe.log_error(frappe.get_traceback(), "sync_pedidos_offline: pedido descartado")

    return {
        "synced": synced,
        "failed": failed,
        "ids_creados": ids_creados,
    }


@frappe.whitelist()
def get_portal_dashboard(id_cliente: str | None = None):
    """Sprint 11 — Home del portal cliente, aislado por tenant."""
    customer_id = _resolve_portal_customer(id_cliente)
    estado = get_estado_cuenta(customer_id)
    blocked_30d, blocked_message = _is_customer_blocked_30_days(customer_id)

    return {
        "id_cliente": customer_id,
        "estado_cuenta": estado,
        "bloqueado_30_dias": blocked_30d,
        "mensaje_bloqueo_30_dias": blocked_message,
        "sugerencias": _get_portal_suggestions(customer_id, limit=5),
    }


@frappe.whitelist()
def get_portal_estado_cuenta(id_cliente: str | None = None, limit: int = 20):
    """Sprint 11 — Estado de cuenta historico (facturas + pagos)."""
    customer_id = _resolve_portal_customer(id_cliente)
    limit_value = max(1, min(int(_to_float(limit, 20)), 100))

    facturas = frappe.get_all(
        "Sales Invoice",
        filters={"customer": customer_id, "docstatus": ["in", [0, 1]]},
        fields=["name", "posting_date", "due_date", "grand_total", "outstanding_amount", "status"],
        order_by="posting_date desc, modified desc",
        limit=limit_value,
    )

    pagos = frappe.db.sql(
        """
        select pe.name, pe.posting_date, pe.paid_amount, pe.paid_to_account_currency as currency, pe.remarks
        from `tabPayment Entry` pe
        where pe.docstatus = 1
          and pe.party_type = 'Customer'
          and pe.party = %(customer)s
        order by pe.posting_date desc, pe.modified desc
        limit %(limit)s
        """,
        {"customer": customer_id, "limit": limit_value},
        as_dict=True,
    )

    return {
        "id_cliente": customer_id,
        "resumen": get_estado_cuenta(customer_id),
        "facturas": facturas,
        "pagos": pagos,
    }


@frappe.whitelist()
def crear_pedido_portal(id_cliente: str, items=None):
    """Sprint 11 — Alta de pedido desde portal, con tenant isolation y bloqueo por mora."""
    customer_id = _resolve_portal_customer(id_cliente)
    blocked_30d, blocked_message = _is_customer_blocked_30_days(customer_id)
    if blocked_30d:
        frappe.throw(blocked_message, frappe.ValidationError)

    payload_items = _parse_json_maybe(items)
    if payload_items is None:
        payload_items = _parse_json_maybe(frappe.form_dict.get("items"))

    if not isinstance(payload_items, list) or not payload_items:
        frappe.throw(_("El payload 'items' debe ser una lista no vacia"), frappe.ValidationError)

    customer = frappe.get_doc("Customer", customer_id)
    company = _get_default_company(customer)
    if not company:
        frappe.throw(_("No hay company por defecto para el pedido"), frappe.ValidationError)

    so_items = []
    for line in payload_items:
        if not isinstance(line, dict):
            frappe.throw(_("Linea de item invalida"), frappe.ValidationError)

        item_code = str(line.get("item_code") or "").strip()
        qty = _to_float(line.get("qty"), 0)
        if not item_code or qty <= 0:
            frappe.throw(_("Item o qty invalidos en pedido"), frappe.ValidationError)

        so_items.append(
            {
                "item_code": item_code,
                "qty": qty,
                "delivery_date": add_days(today(), 1),
            }
        )

    so_data = {
        "doctype": "Sales Order",
        "customer": customer_id,
        "company": company,
        "transaction_date": today(),
        "delivery_date": add_days(today(), 1),
        "order_type": "Sales",
        "items": so_items,
    }

    if getattr(customer, "default_price_list", None):
        so_data["selling_price_list"] = customer.default_price_list

    sales_order = frappe.get_doc(so_data)
    sales_order.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "sales_order": sales_order.name,
    }


@frappe.whitelist()
def create_support_ticket(
    description: str,
    b64Photo: str | None = None,
    affectedBatch: str | None = None,
    id_cliente: str | None = None,
):
    """Sprint 11 — Ticket SOS desde portal cliente (Issue + alerta a calidad)."""
    customer_id = _resolve_portal_customer(id_cliente)

    details = (description or "").strip()
    if not details:
        frappe.throw(_("Parametro obligatorio: description"), frappe.ValidationError)

    batch_no = (affectedBatch or "").strip()
    issue = frappe.get_doc(
        {
            "doctype": "Issue",
            "subject": f"SOS B2B - {customer_id}" + (f" - {batch_no}" if batch_no else ""),
            "description": details,
            "raised_by": frappe.session.user,
            "status": "Open",
        }
    )

    if issue.meta.has_field("customer"):
        issue.customer = customer_id
    if issue.meta.has_field("issue_type"):
        issue_type = "Support"
        if not frappe.db.exists("Issue Type", issue_type):
            issue_type = frappe.db.get_value("Issue Type", {}, "name")
        if issue_type:
            issue.issue_type = issue_type

    issue.insert(ignore_permissions=True)

    photo_bytes = _decode_b64_payload(b64Photo, "b64Photo")
    if photo_bytes:
        _save_private_attachment(
            photo_bytes,
            f"{issue.name}-sos-photo.jpg",
            "Issue",
            issue.name,
        )

    _notify_quality_team(issue.name, customer_id, batch_no)
    frappe.db.commit()

    return {
        "status": "success",
        "issue_id": issue.name,
        "customer": customer_id,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 11 — Loyalty Program
# Usa el DocType nativo de ERPNext "Loyalty Point Entry" y "Loyalty Program".
# Regla de acumulación: 1 punto por cada 100 MAD facturados, priorizando
# familias FEFO (productos próximos a vencer con descuento comercial).
# ─────────────────────────────────────────────────────────────────────────────

_LOYALTY_PROGRAM_NAME_CONF_KEY = "b2b_loyalty_program_name"
_POINTS_PER_100_MAD = 1  # 1 punto por cada 100 MAD de facturación


def _get_loyalty_program() -> str | None:
    """Devuelve el nombre del Loyalty Program configurado en site_config."""
    configured = frappe.conf.get(_LOYALTY_PROGRAM_NAME_CONF_KEY, "")
    if configured:
        return configured

    # Fallback: primer programa activo (sin filtro disabled que puede no existir)
    try:
        program = frappe.db.get_value("Loyalty Program", {"disabled": 0}, "name")
    except Exception:
        # El campo 'disabled' puede no existir en todas las versiones
        program = frappe.db.get_value("Loyalty Program", {}, "name")
    return program


def _get_loyalty_points_balance(id_cliente: str) -> dict[str, Any]:
    """Calcula el saldo de puntos acumulados y canjeados del cliente."""
    program = _get_loyalty_program()

    if not program:
        return {"puntos_acumulados": 0, "puntos_canjeados": 0, "saldo_puntos": 0, "programa": None}

    # ERPNext 16: earning en tabLoyalty Point Entry, redemption en tabla hija
    earned_rows = frappe.db.sql(
        """
        select coalesce(sum(lpe.loyalty_points), 0) as ganados
        from `tabLoyalty Point Entry` lpe
        where lpe.customer = %(customer)s
          and lpe.loyalty_program = %(program)s
          and lpe.expiry_date >= curdate()
        """,
        {"customer": id_cliente, "program": program},
        as_dict=True,
    )

    redeemed_rows = frappe.db.sql(
        """
        select coalesce(sum(r.redeemed_points), 0) as canjeados
        from `tabLoyalty Point Entry Redemption` r
        inner join `tabLoyalty Point Entry` lpe on lpe.name = r.parent
        where lpe.customer = %(customer)s
          and lpe.loyalty_program = %(program)s
        """,
        {"customer": id_cliente, "program": program},
        as_dict=True,
    )

    ganados = int(_to_float((earned_rows[0] if earned_rows else {}).get("ganados"), 0))
    canjeados = int(_to_float((redeemed_rows[0] if redeemed_rows else {}).get("canjeados"), 0))

    return {
        "puntos_acumulados": ganados,
        "puntos_canjeados": canjeados,
        "saldo_puntos": max(0, ganados - canjeados),
        "programa": program,
    }


def _calcular_puntos_por_familia(id_cliente: str, limit: int = 5) -> list[dict[str, Any]]:
    """Detalla puntos ganados por familia de productos (para fidelización FEFO)."""
    program = _get_loyalty_program()
    if not program:
        return []

    rows = frappe.db.sql(
        """
        select
            i.item_group as familia,
            sum(sii.amount) as facturacion,
            floor(sum(sii.amount) / 100) as puntos_estimados
        from `tabSales Invoice Item` sii
        inner join `tabSales Invoice` si on si.name = sii.parent
        inner join `tabItem` i on i.name = sii.item_code
        where si.customer = %(customer)s
          and si.docstatus = 1
          and year(si.posting_date) = year(curdate())
        group by i.item_group
        order by facturacion desc
        limit %(limit)s
        """,
        {"customer": id_cliente, "limit": int(limit)},
        as_dict=True,
    )

    return [
        {
            "familia": row.familia or "Sin familia",
            "facturacion_ytd": flt(row.facturacion, 2),
            "puntos_estimados": int(_to_float(row.puntos_estimados, 0)),
        }
        for row in rows
    ]


@frappe.whitelist()
def get_loyalty_points(id_cliente: str | None = None):
    """Sprint 11 — Saldo de puntos de fidelidad del cliente portal."""
    customer_id = _resolve_portal_customer(id_cliente)

    balance = _get_loyalty_points_balance(customer_id)
    por_familia = _calcular_puntos_por_familia(customer_id)

    return {
        "id_cliente": customer_id,
        "saldo": balance,
        "detalle_por_familia": por_familia,
        "equivalencia_mad": balance["saldo_puntos"] * 10,  # 10 MAD por punto
    }


@frappe.whitelist()
def redimir_puntos(id_cliente: str | None = None, puntos: str = "0"):
    """
    Sprint 11 — Canjea puntos de fidelidad aplicando un descuento al próximo pedido.
    Crea una entrada de Redemption en Loyalty Point Entry.
    """
    customer_id = _resolve_portal_customer(id_cliente)

    qty_puntos = int(max(0, _to_float(puntos, 0)))
    if qty_puntos <= 0:
        frappe.throw(_("Debe indicar una cantidad de puntos positiva"), frappe.ValidationError)

    program = _get_loyalty_program()
    if not program:
        frappe.throw(_("No hay programa de fidelidad activo"), frappe.ValidationError)

    balance = _get_loyalty_points_balance(customer_id)
    if qty_puntos > balance["saldo_puntos"]:
        frappe.throw(
            _("Saldo insuficiente: tiene {0} puntos, solicita {1}").format(
                balance["saldo_puntos"], qty_puntos
            ),
            frappe.ValidationError,
        )

    descuento_mad = flt(qty_puntos * 10, 2)  # 10 MAD por punto

    # Registrar la redención en Loyalty Point Entry
    # ERPNext 16: invoice_type y company son obligatorios; type fue eliminado
    expiry = frappe.utils.add_months(frappe.utils.today(), 12)
    company = frappe.db.get_single_value("Global Defaults", "default_company") or "Peintures du Maroc SARL"
    entry = frappe.get_doc(
        {
            "doctype": "Loyalty Point Entry",
            "loyalty_program": program,
            "loyalty_program_tier": None,
            "customer": customer_id,
            "loyalty_points": -qty_puntos,  # negativo = redención
            "invoice_type": "Sales Invoice",
            "invoice": None,
            "expiry_date": expiry,
            "posting_date": frappe.utils.today(),
            "company": company,
        }
    )
    entry.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "puntos_canjeados": qty_puntos,
        "descuento_aplicado_mad": descuento_mad,
        "saldo_restante": max(0, balance["saldo_puntos"] - qty_puntos),
        "loyalty_entry": entry.name,
    }
