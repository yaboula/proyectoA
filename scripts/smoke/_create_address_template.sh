#!/bin/bash
source /home/frappe/frappe-bench/env/bin/activate
cd /home/frappe/frappe-bench

python - <<'PYEOF'
import frappe
frappe.init(site='frontend', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')

# Check if Address Template exists
existing = frappe.db.get_value('Address Template', {'is_default': 1}, 'name')
if existing:
    print(f"Address Template already exists: {existing}")
else:
    tpl = frappe.new_doc('Address Template')
    tpl.country = 'Morocco'
    tpl.is_default = 1
    tpl.template = """{{ address_line1 }}
{% if address_line2 %}{{ address_line2 }}<br>{% endif %}
{{ city }}{% if state %}, {{ state }}{% endif %}
{{ country }}"""
    tpl.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"Created Address Template for Morocco: {tpl.name}")

# Also check if there's any template at all
all_tpls = frappe.get_all('Address Template', fields=['name', 'country', 'is_default'])
print(f"All Address Templates: {all_tpls}")
frappe.destroy()
PYEOF
