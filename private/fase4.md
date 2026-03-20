S07 — Rutas + Catálogo
[ ] http://localhost:5173 → Login badge: COM-2026-BADGE-00099
[ ] Vista "Rutas Comerciales" carga sin error
[ ] Botón "Catalogue" → navega a /catalogo-stock
[ ] Items PT-TEST-B3-ITEM-A y B aparecen con precio MAD y stock
[ ] Buscador filtra en tiempo real
[ ] Añadir item → barra sticky con total aparece
[ ] Botón "Commander" → abre CartePedidoModal
S08 — Pedido + Carrito
[x] CartePedidoModal muestra estado de cuenta del cliente  ← S08-A PASS
[x] Botones + / - ajustan cantidad                         ← S08-B PASS
[x] Botón "Passer la commande" → feedback de éxito o offline ← S08-C PASS
[x] Apagar WiFi → intentar pedido → mensaje "hors ligne" aparece ← S08-D PASS
[~] Cliente bloqueado → botón deshabilitado (Poka-Yoke)    ← S08-E SKIP (sin cliente bloqueado en seed)
S09 — Picking FEFO
[ ] Login con badge producción/logística → /picking-fefo
[ ] Introducir SAL-ORD-2026-XXXXX → pick list carga
[ ] Primer batch sugerido: B3-FEFO-NEAR-001 (30d, prioritario FEFO)
[ ] Escanear NEAR → validado ✓ verde
[ ] Intentar escanear FAR primero → overlay rojo + shake
[ ] Override → pide PIN → acepta → continúa
S10 — Chofer POD
[ ] Login badge: CHOFER-2026-BADGE-00088 → /chofer-pod
[ ] Delivery Note de "Droguerie Atlas Test" aparece
[ ] Firma en canvas con dedo
[ ] Confirmar → estado cambia a "Livré"
S11 — Portal + Loyalty
[ ] http://localhost:5173/portal-b2b
[ ] Widget loyalty: 250 puntos visibles
[ ] Introducir 50 pts → Échanger → saldo baja a 200 pts
[ ] Sección facturas/pagos visible
S12 — Panel Gerencial

[ ] /panel-gerencial-360
[ ] Scorecard con métricas del día
[ ] Mapa Leaflet con pins GPS
[ ] Botón "Exporter CSV" → descarga fichero

Credenciales resumen
Acceso	URL	Usuario	Contraseña
ERPNext Admin	http://localhost:8080	Administrator	admin
Kiosco comercial	http://localhost:5173	badge COM-2026-BADGE-00099	—
Kiosco chofer	http://localhost:5173	badge CHOFER-2026-BADGE-00088	—
Kiosco producción	http://localhost:5173	badge OP-2026-BADGE-00042	—
