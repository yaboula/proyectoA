# QA Manual Bloque 2 (Operador)

## 1. Objetivo

Ejecutar manualmente los flujos de Bloque 2 y registrar evidencia valida para cierre funcional:

1. Recepcion parcial.
2. Traslado de cuarentena.
3. Reimpresion de etiqueta (bridge activo y bridge caido).
4. Inventario ciego con creacion de borrador ERP.

## 2. Precondiciones

1. ERPNext/Frappe disponible en http://localhost:8080.
2. Kiosco disponible en http://localhost:5173.
3. Badge operativo de prueba: OP-2026-BADGE-00042.
4. Datos sandbox preparados justo antes de probar:

```powershell
Set-Location D:\proyectoA
.\scripts\e2e\prepare-block2-sandbox.ps1
```

5. Si vas a probar impresion exitosa real, levantar bridge Zebra en localhost:9000.
6. Si vas a probar error controlado de impresion, detener bridge Zebra.

## 3. Datos de prueba

1. Lote reimpresion y cuarentena: LOTE-QA-RECEP-0001.
2. Inventario ciego:
   - MP-RES-ALK-G70|LOTE-CIEGO-2026-0001 (2 veces)
   - MP-RES-ALK-G70|LOTE-CIEGO-2026-0002 (1 vez)

## 4. Flujo A - Recepcion parcial (evidencia obligatoria)

### Paso a paso en app

1. Login en kiosco con badge.
2. Ir a Reception materiaux (/recepcion).
3. Seleccionar la primera PO abierta.
4. Pulsar Receptionner en una linea pendiente.
5. En modal, ingresar qty 1 y validar.

### Resultado esperado en app

1. Se cierra modal sin error rojo.
2. Aparece Purchase Receipt creado.
3. El reliquat del item baja (antes > despues).

### Verificacion ERP

1. Abrir Purchase Receipt mostrado por la app.
2. Validar docstatus = 1.
3. Validar item y warehouse esperados.

## 5. Flujo B - Traslado cuarentena (evidencia obligatoria)

### Paso a paso en app

1. Ir a Gestion quarantaine (/traslado-cuarentena).
2. Saisir lot: LOTE-QA-RECEP-0001.
3. Verificar stock en quarantaine > 0.
4. Pulsar Transferer vers MP approuvee.

### Resultado esperado en app

1. Mensaje de exito con Stock Entry MAT-STE-....
2. Boton de transferencia deshabilitado para ese lote tras mover.
3. Sin error rojo no controlado en flujo feliz.

### Verificacion ERP

1. Abrir Stock Entry mostrado por la app.
2. Validar docstatus = 1.
3. Validar source = Cuarentena MP - PDM.
4. Validar target = Materia Prima Aprobada - PDM.
5. Validar batch_no = LOTE-QA-RECEP-0001.

## 6. Flujo C - Reimpression etiquette (Sprint 5)

### Caso C1 - Bridge activo

#### Paso a paso en app

1. Ir a Re-impression etiquette (/reimpresion).
2. Saisir lot: LOTE-QA-RECEP-0001.
3. Pulsar Imprimer etiquette.

#### Resultado esperado en app

1. Carga item_code, item_name, batch_no, expiry_date.
2. Muestra mensaje de impresion exitosa.

#### Verificacion ERP

1. No se crea documento nuevo por reimpresion.
2. Batch/Item en ERP coinciden con lo mostrado en app.

### Caso C2 - Bridge detenido

#### Paso a paso en app

1. Detener bridge Zebra local (localhost:9000).
2. Repetir pulsacion Imprimer etiquette en el mismo lote.

#### Resultado esperado en app

1. Muestra error controlado de impresion (ejemplo PRINT_HTTP_503 o timeout).
2. La pantalla no se rompe ni pierde los datos del lote cargado.

#### Verificacion ERP

1. No se crea ningun documento ERP por esta accion fallida de impresion.

## 7. Flujo D - Inventaire rapide (Sprint 6)

### Paso a paso en app

1. Ir a Inventaire rapide (/inventario-ciego).
2. Escanear o ingresar manualmente:
   - MP-RES-ALK-G70|LOTE-CIEGO-2026-0001 (dos veces)
   - MP-RES-ALK-G70|LOTE-CIEGO-2026-0002 (una vez)
3. Verificar contadores.
4. Pulsar Envoyer le comptage.

### Resultado esperado en app

1. Scans = 3.
2. Lots = 2.
3. Se ven dos filas con qty 2 y qty 1.
4. Mensaje Brouillon cree: MAT-RECO-....
5. Se limpia el conteo local del warehouse activo.
6. Si cambias de warehouse, veras solo el conteo local de ese warehouse (puede aparecer vacio aunque en otro warehouse haya conteo).
7. Despues de enviar, es normal volver a ver "Aucun comptage local" en ese warehouse.

### Verificacion ERP

1. Se crea Stock Reconciliation nuevo.
2. Docstatus = 0 (Draft).
3. Warehouse correcto.
4. Persisten solo lineas con diferencia real vs stock sistema.

## 8. Evidencias a guardar (obligatorio)

Guardar capturas con nombre sugerido:

1. 01-login-kiosco.png
2. 02-reception-before-reliquat.png
3. 03-reception-after-reliquat.png
4. 04-cuarentena-transfer-success.png
5. 05-reprint-data-loaded.png
6. 06-reprint-print-success.png
7. 07-reprint-print-controlled-error.png
8. 08-inventory-before-submit.png
9. 09-inventory-submit-success.png
10. 10-erp-pr.png
11. 11-erp-ste.png
12. 12-erp-reco-draft.png
13. 13-erp-batch-item-match.png

## 9. Registro de IDs (rellenar durante prueba)

1. Purchase Receipt: ____________________
2. Stock Entry: ____________________
3. Stock Reconciliation (Draft): ____________________
4. Batch validado: LOTE-QA-RECEP-0001

## 10. Criterio de aceptacion final Bloque 2

Marcar PASS/FAIL:

1. Recepcion parcial funciona y recarga backlog correctamente: [ ] PASS [ ] FAIL
2. Traslado de cuarentena crea movimiento de stock correcto: [ ] PASS [ ] FAIL
3. Reimpresion reconstruye etiqueta del lote correcto: [ ] PASS [ ] FAIL
4. Inventario ciego crea borrador de reconciliacion en ERP: [ ] PASS [ ] FAIL
5. No hay errores rojos no controlados en flujo feliz: [ ] PASS [ ] FAIL
6. Todos los documentos ERP esperados existen y con estado correcto: [ ] PASS [ ] FAIL

## 11. Resultado final

1. QA ejecutado por: ____________________
2. Fecha/hora inicio: ____________________
3. Fecha/hora fin: ____________________
4. Estado final: [ ] APROBADO [ ] RECHAZADO
5. Observaciones: ____________________
