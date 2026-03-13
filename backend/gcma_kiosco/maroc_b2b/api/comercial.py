"""Compatibilidad de namespace contractual: maroc_b2b.api.comercial.*"""

from gcma_kiosco.api.comercial import (
	create_support_ticket,
	crear_pedido_portal,
	get_estado_cuenta,
	get_ruta_dia,
	get_portal_dashboard,
	get_portal_estado_cuenta,
	post_checkin,
	sync_pedidos_offline,
)

__all__ = [
	"get_estado_cuenta",
	"get_ruta_dia",
	"post_checkin",
	"sync_pedidos_offline",
	"get_portal_dashboard",
	"get_portal_estado_cuenta",
	"crear_pedido_portal",
	"create_support_ticket",
]
