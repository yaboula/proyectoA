import frappe
so = frappe.get_doc('Sales Order', 'SAL-ORD-2026-00003')
so.submit()
frappe.db.commit()
print('SUBMITTED:', so.name, 'docstatus=', so.docstatus)
