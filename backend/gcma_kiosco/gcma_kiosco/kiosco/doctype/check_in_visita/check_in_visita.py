from math import cos, radians, sqrt

import frappe
from frappe import _
from frappe.model.document import Document


MAX_DISTANCIA_METROS = 500.0
METROS_POR_GRADO_LAT = 110540.0
METROS_POR_GRADO_LNG = 111320.0


class CheckInVisita(Document):
    def validate(self):
        self._validar_timestamps()
        self._calcular_visita_valida()

    def _validar_timestamps(self):
        if self.timestamp_in and self.timestamp_out and self.timestamp_out < self.timestamp_in:
            frappe.throw(_("timestamp_out no puede ser menor que timestamp_in"))

    def _calcular_visita_valida(self):
        lat_capturada = _as_float(self.gps_lat_capturada, "gps_lat_capturada")
        lng_capturada = _as_float(self.gps_lng_capturada, "gps_lng_capturada")

        lat_cliente, lng_cliente = self._obtener_gps_cliente(self.cliente)
        distancia = _distancia_euclidiana_metros(
            lat_cliente,
            lng_cliente,
            lat_capturada,
            lng_capturada,
        )

        self.es_visita_valida = 1 if distancia <= MAX_DISTANCIA_METROS else 0

    @staticmethod
    def _obtener_gps_cliente(cliente):
        gps_cliente = frappe.db.get_value("Customer", cliente, ["gps_lat", "gps_lng"], as_dict=True)
        if not gps_cliente:
            frappe.throw(_("Cliente no encontrado para calcular geocerca"))

        lat = _as_float(gps_cliente.gps_lat, "Customer.gps_lat")
        lng = _as_float(gps_cliente.gps_lng, "Customer.gps_lng")
        return lat, lng


def _as_float(valor, nombre_campo):
    try:
        return float(valor)
    except (TypeError, ValueError):
        frappe.throw(_("Valor invalido en {0}").format(nombre_campo))


def _distancia_euclidiana_metros(lat_1, lng_1, lat_2, lng_2):
    # Aproximacion euclidiana en metros usando correccion por latitud media.
    lat_media_rad = radians((lat_1 + lat_2) / 2.0)
    dx = (lng_2 - lng_1) * METROS_POR_GRADO_LNG * cos(lat_media_rad)
    dy = (lat_2 - lat_1) * METROS_POR_GRADO_LAT
    return sqrt((dx * dx) + (dy * dy))
