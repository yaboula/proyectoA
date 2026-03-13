# Evidencia Bloque 2 - 2026-03-13

## Resumen

Ejecucion realizada para cerrar Fase 2 (Sprint 5) y Fase 3 (Sprint 6) con evidencia guardada de:

1. Recepcion parcial.
2. Traslado de cuarentena.
3. Reimpresion de etiqueta (bridge activo y error controlado).
4. Inventario ciego y creacion de borrador de reconciliacion.

## Artefactos guardados

Ruta de capturas y JSON:

- [kiosco-pwa/evidence/block2](kiosco-pwa/evidence/block2)
- [kiosco-pwa/evidence/block2/evidence.json](kiosco-pwa/evidence/block2/evidence.json)

Capturas generadas:

1. [kiosco-pwa/evidence/block2/01-login-kiosco.png](kiosco-pwa/evidence/block2/01-login-kiosco.png)
2. [kiosco-pwa/evidence/block2/02-reception-before-reliquat.png](kiosco-pwa/evidence/block2/02-reception-before-reliquat.png)
3. [kiosco-pwa/evidence/block2/03-reception-after-reliquat.png](kiosco-pwa/evidence/block2/03-reception-after-reliquat.png)
4. [kiosco-pwa/evidence/block2/04-cuarentena-before-transfer.png](kiosco-pwa/evidence/block2/04-cuarentena-before-transfer.png)
5. [kiosco-pwa/evidence/block2/05-cuarentena-transfer-success.png](kiosco-pwa/evidence/block2/05-cuarentena-transfer-success.png)
6. [kiosco-pwa/evidence/block2/06-reprint-data-loaded.png](kiosco-pwa/evidence/block2/06-reprint-data-loaded.png)
7. [kiosco-pwa/evidence/block2/07-reprint-print-success.png](kiosco-pwa/evidence/block2/07-reprint-print-success.png)
8. [kiosco-pwa/evidence/block2/08-reprint-print-controlled-error.png](kiosco-pwa/evidence/block2/08-reprint-print-controlled-error.png)
9. [kiosco-pwa/evidence/block2/09-inventory-before-submit.png](kiosco-pwa/evidence/block2/09-inventory-before-submit.png)
10. [kiosco-pwa/evidence/block2/10-inventory-submit-success.png](kiosco-pwa/evidence/block2/10-inventory-submit-success.png)

## IDs de documentos obtenidos

Tomados de [kiosco-pwa/evidence/block2/evidence.json](kiosco-pwa/evidence/block2/evidence.json):

1. Purchase Order: PUR-ORD-2026-00004.
2. Purchase Receipt: MAT-PRE-2026-00029.
3. Stock Entry (traslado cuarentena): MAT-STE-2026-00059.
4. Stock Reconciliation (inventario ciego): MAT-RECO-2026-00012.

## Verificacion ERP (consulta directa)

Validacion ejecutada en ERPNext/Frappe via consulta directa al sitio frontend.

1. Purchase Receipt MAT-PRE-2026-00029:
   - docstatus = 1.
   - item: ENV-BID-20L-BLC.
   - warehouse: Cuarentena MP - PDM.
2. Stock Entry MAT-STE-2026-00059:
   - docstatus = 1.
   - tipo: Material Transfer.
   - lote: LOTE-QA-RECEP-0001.
   - source: Cuarentena MP - PDM.
   - target: Materia Prima Aprobada - PDM.
3. Stock Reconciliation MAT-RECO-2026-00012:
   - docstatus = 0 (Draft).
   - purpose = Stock Reconciliation.
   - warehouse en lineas: Materia Prima Aprobada - PDM.
   - lineas persistidas con diferencia real:
     - LOTE-CIEGO-2026-0002: qty 1, current_qty 12, quantity_difference -11.
     - LOTE-CIEGO-2026-0001: qty 2, current_qty 11, quantity_difference -9.
4. Reimpresion LOTE-QA-RECEP-0001:
   - Batch/Item consistente con app:
     - item_code: MP-RES-ALK-G70.
     - item_name: Résine Alkyde G-70.
     - expiry_date: 2027-12-31.
   - No crea documento ERP nuevo durante impresion:
     - la accion de imprimir usa bridge local (localhost:9000), no endpoint de escritura ERP.
     - ultimo Stock Entry se mantiene en MAT-STE-2026-00059 (movimiento de cuarentena, no de reimpresion).

## Resultado contra criterios de aceptacion

1. Recepcion parcial funciona y recarga backlog correctamente: Cumplido.
2. Traslado de cuarentena crea movimiento de stock correcto: Cumplido.
3. Reimpresion reconstruye etiqueta del lote correcto: Cumplido.
4. Inventario ciego crea borrador de reconciliacion en ERP: Cumplido.
5. No hay errores rojos no controlados en flujo feliz: Cumplido.
6. Documentos ERP esperados existen y con estado correcto: Cumplido.

## Comandos usados

1. npm run test:e2e:prepare-block2
2. npm run test:e2e:block2:evidence
3. Consulta ERP via docker exec + bench python para validar docstatus/almacenes/diferencias.
