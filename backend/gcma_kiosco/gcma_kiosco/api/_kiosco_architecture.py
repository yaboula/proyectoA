"""
GCMA Kiosco — API REST Architecture
====================================

Diseño de los endpoints @frappe.whitelist() para la PWA del Kiosco de operarios.
Bloque 3 del FSD: autenticación QR, tareas, validación Poka-Yoke, consumo.

RUTAS BASE:  /api/method/gcma_kiosco.api.kiosco.<method_name>

CONVENCIONES:
  - Todos los endpoints devuelven JSON envuelto en {"message": ...}
    (estándar Frappe para @frappe.whitelist).
  - Errores devuelven HTTP 4xx/5xx con {"exc_type": "...", "message": "..."}
  - Los mensajes al operario siempre en FRANCÉS (Guardrail G1).
  - Nunca se expone item_code al frontend; solo item_name (Guardrail G3).
  - Todos los endpoints requieren autenticación (session cookie o token).

═══════════════════════════════════════════════════════════════════════════
ENDPOINT 1 — Autenticación del Operario por QR
═══════════════════════════════════════════════════════════════════════════

RUTA:   POST /api/method/gcma_kiosco.api.kiosco.login_operario

CONTEXTO:
  El operario escanea su badge QR personal al inicio del turno.
  El QR contiene un token único vinculado a su usuario Frappe.
  El Kiosco NO tiene teclado; el QR es el único medio de login.

REQUEST (JSON):
  {
    "qr_token": "OP-2026-BADGE-00042"         // Contenido escaneado del badge
  }

RESPONSE 200 — Login OK:
  {
    "message": {
      "success": true,
      "operario": {
        "full_name": "Ahmed Benali",
        "employee_id": "HR-EMP-00042",
        "role": "Operario Planta",
        "turno": "Matin",                     // Matin / Après-midi / Nuit
        "company": "Peintures du Maroc SARL",
        "default_warehouse": "Planta Mezclas WIP - PDM"
      },
      "session_token": "...",                  // API key o session para requests siguientes
      "message_fr": "Bienvenue, Ahmed."
    }
  }

RESPONSE 401 — QR inválido:
  {
    "message": {
      "success": false,
      "error_code": "INVALID_BADGE",
      "message_fr": "Badge non reconnu. Veuillez contacter le superviseur."
    }
  }

RESPONSE 403 — Operario desactivado:
  {
    "message": {
      "success": false,
      "error_code": "EMPLOYEE_INACTIVE",
      "message_fr": "Compte désactivé. Contactez les Ressources Humaines."
    }
  }

LÓGICA INTERNA (no expuesta):
  1. Buscar Employee donde custom_field qr_badge_token == qr_token
  2. Verificar que Employee.status == "Active"
  3. Verificar que tiene User vinculado con rol "Operario Planta"
  4. Crear/renovar API Key o generar session
  5. Log de acceso (hora, badge, IP del kiosco)


═══════════════════════════════════════════════════════════════════════════
ENDPOINT 2 — Obtener Tareas del Operario (Work Orders pendientes)
═══════════════════════════════════════════════════════════════════════════

RUTA:   GET /api/method/gcma_kiosco.api.kiosco.get_tareas

CONTEXTO:
  Después del login, el Kiosco muestra las Work Orders asignadas al
  turno/estación del operario. Pantalla tipo "lista de tareas" con
  botones grandes para seleccionar.

REQUEST (Query params):
  ?company=Peintures du Maroc SARL
  &warehouse=Planta Mezclas WIP - PDM        // Opcional: filtrar por WIP del operario

RESPONSE 200:
  {
    "message": {
      "tareas": [
        {
          "work_order": "WO-PDM-2026-00033",
          "producto": "Peinture Blanche Mate 20L",     // item_name, NO item_code (G3)
          "cantidad": 50,
          "uom": "Nos",
          "bom": "BOM-PT-PIN-BLC-MAT-20L-001",
          "estado": "Not Started",                      // Not Started | In Process | Completed
          "prioridad": "Haute",
          "fecha_inicio_plan": "2026-03-10",
          "materiales_pendientes": true,                // ¿Falta Material Transfer?
          "materiales": [
            {
              "item_name": "Résine Alkyde G-70",        // Nombre visible (G3)
              "qty_requerida": 306.0,
              "uom": "Kg",
              "qty_disponible": 1075.0,                 // Stock en MP Aprobada
              "suficiente": true
            },
            {
              "item_name": "Dioxyde de Titane R-902",
              "qty_requerida": 404.0,
              "uom": "Kg",
              "qty_disponible": 500.0,
              "suficiente": true
            }
            // ... resto de ingredientes
          ]
        }
        // ... más Work Orders
      ],
      "total": 3
    }
  }

RESPONSE 200 — Sin tareas:
  {
    "message": {
      "tareas": [],
      "total": 0,
      "message_fr": "Aucun ordre de fabrication en attente."
    }
  }

LÓGICA INTERNA:
  1. Filtrar Work Orders: company, status IN ("Not Started", "In Process"), docstatus=1
  2. Para cada WO, explotar la BOM y verificar stock disponible en MP Aprobada
  3. Traducir item_code → item_name (G3)
  4. Ordenar por prioridad y fecha planificada


═══════════════════════════════════════════════════════════════════════════
ENDPOINT 3 — Validar Escaneo de Material (Poka-Yoke)
═══════════════════════════════════════════════════════════════════════════

RUTA:   POST /api/method/gcma_kiosco.api.kiosco.validar_material

CONTEXTO:
  El operario seleccionó una Work Order. Ahora escanea el QR del bidón
  de materia prima que va a verter en la mezcladora. El Kiosco envía
  el contenido del QR y el backend valida:
    ✓ ¿Es el material correcto para esta BOM?
    ✓ ¿El lote no está caducado?
    ✓ ¿El lote tiene QC aprobada?
    ✓ ¿Hay stock suficiente de este lote?

REQUEST (JSON):
  {
    "work_order": "WO-PDM-2026-00033",
    "qr_data": "MP-RES-ALK-G70|LOTE-RES-2026-0001"   // item_code|batch_no embebido en QR
  }

RESPONSE 200 — Material VÁLIDO (luz verde en Kiosco):
  {
    "message": {
      "valido": true,
      "item_name": "Résine Alkyde G-70",               // Nombre visible (G3)
      "batch_no": "LOTE-RES-2026-0001",
      "fecha_caducidad": "2027-03-09",
      "dias_restantes": 365,
      "qty_en_lote": 215.0,
      "qty_requerida_bom": 306.0,
      "uom": "Kg",
      "estado_qc": "Aprobado",
      "message_fr": "✓ Matériau vérifié. Vous pouvez verser."
    }
  }

RESPONSE 200 — Material INCORRECTO (luz roja + alarma):
  {
    "message": {
      "valido": false,
      "error_code": "WRONG_MATERIAL",
      "item_escaneado": "White Spirit Standard",         // Lo que escaneó
      "item_esperado": ["Résine Alkyde G-70"],           // Lo que necesita la BOM
      "message_fr": "✗ STOP — Ce matériau ne correspond pas à la recette. Vérifiez l'étiquette.",
      "alerta_nivel": "CRITICO"
    }
  }

RESPONSE 200 — Lote CADUCADO:
  {
    "message": {
      "valido": false,
      "error_code": "BATCH_EXPIRED",
      "item_name": "Résine Alkyde G-70",
      "batch_no": "LOTE-RES-2025-0044",
      "fecha_caducidad": "2026-02-15",
      "message_fr": "✗ STOP — Lot périmé depuis le 15/02/2026. Ne pas utiliser.",
      "alerta_nivel": "CRITICO"
    }
  }

RESPONSE 200 — QC no aprobada:
  {
    "message": {
      "valido": false,
      "error_code": "QC_NOT_APPROVED",
      "batch_no": "LOTE-RES-2026-0005",
      "message_fr": "✗ Ce lot n'a pas encore passé le contrôle qualité. En attente d'approbation.",
      "alerta_nivel": "BLOQUEO"
    }
  }

RESPONSE 400 — QR no parseable:
  {
    "message": {
      "valido": false,
      "error_code": "INVALID_QR",
      "message_fr": "Code QR illisible. Réessayez ou saisissez manuellement le numéro de lot."
    }
  }

LÓGICA INTERNA:
  1. Parsear qr_data → extraer item_code y batch_no
  2. Validar que item_code existe en la BOM del Work Order
  3. Verificar Batch: expiry_date > today
  4. Verificar que el Batch tiene QC aprobada (Quality Inspection con status Accepted)
  5. Verificar stock del Batch en el warehouse de origen (MP Aprobada)
  6. Si todo OK → responder valido=true
  7. Si algo falla → responder con error_code específico y mensaje en francés


═══════════════════════════════════════════════════════════════════════════
ENDPOINT 4 — Reportar Consumo Real (Post-producción)
═══════════════════════════════════════════════════════════════════════════

RUTA:   POST /api/method/gcma_kiosco.api.kiosco.reportar_consumo

CONTEXTO:
  Al terminar la mezcla, el operario confirma las cantidades reales
  consumidas. El backflush teórico ya está calculado por la BOM;
  este endpoint permite AJUSTAR si hubo diferencia (el botón
  [+AÑADIR EXTRA] del Kiosco).

  Este endpoint NO crea el Stock Entry de Manufacture directo.
  Registra las diferencias y el supervisor (Jefe de Planta) valida
  antes de que se genere el SE definitivo.

REQUEST (JSON):
  {
    "work_order": "WO-PDM-2026-00033",
    "consumos": [
      {
        "item_code": "MP-RES-ALK-G70",                // Oculto al operario, viene del QR escaneado
        "batch_no": "LOTE-RES-2026-0001",
        "qty_real": 310.0,                             // Teórico BOM: 306 Kg, real: 310 Kg
        "uom": "Kg",
        "motivo_diferencia": "Viscosité haute, ajout compensatoire"  // Opcional, texto libre
      },
      {
        "item_code": "MP-PIG-TIO2-R902",
        "batch_no": "LOTE-PIG-2026-0044",
        "qty_real": 404.0,                             // Sin diferencia
        "uom": "Kg"
      },
      {
        "item_code": "MP-SOL-WSPI-STD",
        "batch_no": "LOTE-SOL-2026-0012",
        "qty_real": 157.0,                             // +2 Kg extra
        "uom": "Kg",
        "motivo_diferencia": "Compensation dilution"
      },
      {
        "item_code": "MP-H2O-DESMIN",
        "batch_no": "LOTE-H2O-2026-0001",
        "qty_real": 450.0,
        "uom": "Kg"
      }
    ],
    "qty_producida": 50,                               // Cubetas reales producidas
    "observaciones": "Mélange homogène, temps 45min"   // Nota general del operario
  }

RESPONSE 200 — Consumo registrado OK:
  {
    "message": {
      "success": true,
      "work_order": "WO-PDM-2026-00033",
      "resumen": {
        "qty_producida": 50,
        "desviaciones": [
          {
            "item_name": "Résine Alkyde G-70",
            "qty_teorica": 306.0,
            "qty_real": 310.0,
            "diferencia_kg": 4.0,
            "diferencia_pct": 1.3,
            "motivo": "Viscosité haute, ajout compensatoire"
          },
          {
            "item_name": "White Spirit Standard",
            "qty_teorica": 154.5,
            "qty_real": 157.0,
            "diferencia_kg": 2.5,
            "diferencia_pct": 1.6,
            "motivo": "Compensation dilution"
          }
        ],
        "merma_total_pct": 1.2,
        "estado": "Pendiente validación superviseur"
      },
      "message_fr": "Consommation enregistrée. En attente de validation du chef de production."
    }
  }

RESPONSE 200 — Desviación excesiva (>10%):
  {
    "message": {
      "success": true,
      "alerta": true,
      "alerta_nivel": "WARNING",
      "message_fr": "⚠ Écart supérieur à 10% détecté sur Résine Alkyde G-70. Le superviseur sera notifié.",
      "resumen": { "..." }
    }
  }

RESPONSE 400 — Work Order no válida:
  {
    "message": {
      "success": false,
      "error_code": "WO_NOT_IN_PROCESS",
      "message_fr": "Cet ordre de fabrication n'est pas en cours. Vérifiez avec le superviseur."
    }
  }

LÓGICA INTERNA:
  1. Validar que la Work Order existe y está en estado "In Process"
  2. Para cada consumo: verificar item+batch existen y tienen stock
  3. Calcular desviación vs BOM teórica (incluyendo scrap %)
  4. Si desviación > 10% en algún material → marcar alerta
  5. Guardar en un Custom DocType "Registro Consumo Kiosco" (draft)
  6. Notificar al Jefe de Planta si hay alertas
  7. El Jefe de Planta aprueba → se genera el Stock Entry Manufacture real


═══════════════════════════════════════════════════════════════════════════
ENDPOINT 5 (AUXILIAR) — Buscar Lote por Escaneo Rápido
═══════════════════════════════════════════════════════════════════════════

RUTA:   GET /api/method/gcma_kiosco.api.kiosco.info_lote

CONTEXTO:
  El operario escanea un QR de cualquier bidón/saco para consultar
  información del lote sin estar en contexto de una Work Order.
  Pantalla informativa del Kiosco.

REQUEST (Query params):
  ?qr_data=MP-RES-ALK-G70|LOTE-RES-2026-0001

RESPONSE 200:
  {
    "message": {
      "item_name": "Résine Alkyde G-70",               // Nunca item_code (G3)
      "batch_no": "LOTE-RES-2026-0001",
      "fecha_recepcion": "2026-03-01",
      "fecha_caducidad": "2027-03-01",
      "dias_restantes": 357,
      "estado_qc": "Aprobado",
      "almacen_actual": "Materia Prima Aprobada - PDM",
      "qty_disponible": 765.0,
      "uom": "Kg",
      "proveedor": "ChimEurope SARL",
      "purchase_receipt": "PR-PDM-2026-00045",
      "ficha_seguridad_url": "https://...",            // Si existe el custom field
      "clase_peligrosidad": "Inflamable"
    }
  }


═══════════════════════════════════════════════════════════════════════════
RESUMEN DE RUTAS
═══════════════════════════════════════════════════════════════════════════

 #  | Método | Ruta                                              | Propósito
----+--------+---------------------------------------------------+---------------------------------
 1  | POST   | .../gcma_kiosco.api.kiosco.login_operario         | Auth por QR badge
 2  | GET    | .../gcma_kiosco.api.kiosco.get_tareas             | Work Orders pendientes
 3  | POST   | .../gcma_kiosco.api.kiosco.validar_material       | Poka-Yoke: escaneo de MP
 4  | POST   | .../gcma_kiosco.api.kiosco.reportar_consumo       | Consumo real post-mezcla
 5  | GET    | .../gcma_kiosco.api.kiosco.info_lote              | Consulta informativa de lote

NOTA: Todos bajo /api/method/ (estándar Frappe @frappe.whitelist).
"""
