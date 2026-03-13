app_name = "gcma_kiosco"
app_title = "GCMA Kiosco"
app_publisher = "GCMA Tech Team"
app_description = "Custom App: Seed Data, API Kiosco y lógica de planta para la fábrica química GCMA."
app_email = "dev@gcma.ma"
app_license = "MIT"
required_apps = ["frappe", "erpnext"]

# ---------------------------------------------------------------------------
# After Install — Se ejecuta una sola vez al hacer bench install-app
# ---------------------------------------------------------------------------
# after_install = "gcma_kiosco.setup.install.after_install"

# ---------------------------------------------------------------------------
# CSRF Exemption — La PWA del Kiosco se sirve desde un origen diferente
# (Vite en dev, CDN/nginx en prod) y no recibe la cookie csrf_token que
# Frappe inyecta en páginas HTML. Los endpoints ya están protegidos por
# sesión (sid) y token QR, así que el CSRF no aporta seguridad aquí.
# ---------------------------------------------------------------------------
before_request = ["gcma_kiosco.api.kiosco.exempt_csrf"]

# ---------------------------------------------------------------------------
# Fixtures — DocTypes cuya data se exporta/importa con el app
# Se exportan con: bench export-fixtures --app gcma_kiosco
# Se importan automáticamente con bench install-app / bench migrate
# ---------------------------------------------------------------------------
fixtures = [
    {"dt": "Custom Field", "filters": [["fieldname", "like", "custom_qr_%"]]},
    {
        "dt": "Custom Field",
        "filters": [
            ["dt", "=", "Customer"],
            [
                "fieldname",
                "in",
                [
                    "deuda_total",
                    "deuda_vencida",
                    "dias_peor_mora",
                    "gps_lat",
                    "gps_lng",
                    "id_comercial_asignado",
                ],
            ],
        ],
    },
    {
        "dt": "Custom Field",
        "filters": [
            ["dt", "=", "Delivery Note"],
            [
                "fieldname",
                "in",
                [
                    "firma_receptor",
                    "foto_sello_pod",
                    "estado_entrega_pwa",
                    "gps_entrega_lat",
                    "gps_entrega_lng",
                ],
            ],
        ],
    },
]

# ---------------------------------------------------------------------------
# Whitelisted API methods — Endpoints REST del Kiosco (Fase 2)
# Cada método decorado con @frappe.whitelist() ya es público;
# esta sección es solo para documentación en hooks.
# ---------------------------------------------------------------------------
# override_whitelisted_methods = {}

# ---------------------------------------------------------------------------
# Scheduled Tasks — Tareas cron (futuro: alertas de caducidad, etc.)
# ---------------------------------------------------------------------------
scheduler_events = {
    "daily": [
        "gcma_kiosco.api.gerencial.scheduler_alerta_abandono_clientes",
    ],
}

# ---------------------------------------------------------------------------
# Doc Events — Hooks sobre DocTypes nativos (futuro: Server Scripts vía código)
# ---------------------------------------------------------------------------
# doc_events = {
#     "Quality Inspection": {
#         "on_update": "gcma_kiosco.events.quality_inspection.on_update"
#     }
# }
