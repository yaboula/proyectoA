import frappe
from frappe import _
from frappe.model.document import Document


class RutaComercialDia(Document):
    def validate(self):
        if not self.visitas_programadas:
            # Una ruta diaria sin clientes programados no es operable.
            frappe.throw(_("Ruta_Comercial_Dia requiere al menos una visita programada"))

        ordenes = [row.orden_visita for row in self.visitas_programadas if row.orden_visita is not None]
        if len(ordenes) != len(set(ordenes)):
            frappe.throw(_("Orden_Visita duplicado en Visitas_Programadas"))
