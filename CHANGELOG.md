# Changelog

Todos los cambios notables del proyecto se documentan aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

## [0.8.9] — 2026-03-14

### Added

**QA — Dia 4 S11/S12 + seguridad ejecutado**

- Nuevo reporte `docs/qa/BLOQUE3_DIA4_EJECUCION_2026-03-14.md`.
- Evidencia consolidada de:
  - Tenant isolation portal (`403` forzado + `200` valido).
  - Dashboard gerencial 360 (`200`).
  - Ejecucion manual scheduler de abandono (`200`).
  - Export CSV scorecard (`200`).
  - Controles de autorizacion anonima en endpoints criticos (`403`).

### Changed

**QA — Progreso de cierre Bloque 3**

- Dia 4 finaliza sin defectos criticos/altos abiertos, quedando preparado el Dia 5 de regresion final y reporte Go/No-Go.

## [0.8.8] — 2026-03-14

### Added

**QA — Dia 3 S09/S10 ejecutado y automatizado**

- Nuevo reporte `docs/qa/BLOQUE3_DIA3_EJECUCION_2026-03-14.md` con evidencia FEFO/POD.
- Nuevo spec `kiosco-pwa/tests/e2e/logistica-fefo-pod.spec.js` cubriendo:
  - FEFO rechazo/aceptacion.
  - POD invalido/valido.
- Scripts operativos de soporte para entorno QA:
  - `scripts/manual/day3_probe_runtime.py`
  - `scripts/manual/day3_runtime_prepare.py`
  - `scripts/manual/day3_generate_image_payloads.py`

### Changed

**Datos QA — Preparacion reproducible para S09/S10**

- Se estandariza preparacion de dataset FEFO/POD en runtime para garantizar ejecucion repetible de casos criticos.

## [0.8.7] — 2026-03-14

### Added

**Backend — Sprint 07 contrato comercial restaurado**

- Nuevos endpoints en `backend/gcma_kiosco/gcma_kiosco/api/comercial.py`:
  - `get_ruta_dia`
  - `post_checkin`
- Exposicion de ambos endpoints en namespace contractual `backend/gcma_kiosco/maroc_b2b/api/comercial.py`.
- Manejo defensivo para entornos QA sin tablas activas (`Ruta_Comercial_Dia` / `CheckIn_Visita`) manteniendo respuesta controlada del contrato.

### Changed

**Frontend — Resiliencia namespace B2B Sprint 07**

- `kiosco-pwa/src/api/kiosco.js` ahora aplica fallback automatico de namespace `maroc_b2b -> gcma_kiosco` para:
  - `getRutaDia`
  - `postCheckin`

### Added

**QA/Docs — Ejecucion Dia 2 Bloque 3**

- Nuevo reporte `docs/qa/BLOQUE3_DIA2_EJECUCION_2026-03-14.md`.
- `docs/API.md` actualizado con referencia de los endpoints Sprint 07 comerciales.

## [0.8.6] — 2026-03-13

### Added

**Backend — Sprint 12 Panel Gerencial 360**

- Nuevo modulo `backend/gcma_kiosco/gcma_kiosco/api/gerencial.py` con endpoints:
  - `get_panel_gerencial_360`
  - `get_cobertura_mapa`
  - `get_reporte_fotos_competencia`
  - `export_scorecard_csv`
  - `run_alerta_abandono_clientes`
- Nuevo namespace contractual `backend/gcma_kiosco/maroc_b2b/api/gerencial.py`.
- Cache de 5 minutos para consultas del dashboard.
- Scheduler diario activado en `hooks.py` para alerta de abandono parametrizable.

### Added

**Frontend — Dashboard directivo con mapa GPS**

- Nuevo cliente API `kiosco-pwa/src/api/gerencial.js`.
- Nueva vista `kiosco-pwa/src/views/PanelGerencial360.vue` con:
  - Scorecard de clientes.
  - Mapa Leaflet de check-ins y desviaciones (rojo/verde).
  - Hit-rate visitas con/sin pedido.
  - Boton de ejecucion de alerta de abandono.
  - Export CSV del scorecard.
  - Reporte de fotos de competencia.
- Nueva ruta `/panel-gerencial-360` en `kiosco-pwa/src/router/index.js`.
- Dependencia `leaflet` instalada en `kiosco-pwa/package.json`.

### Added

**QA — Evidencia Sprint 12**

- Nuevo spec `kiosco-pwa/tests/e2e/panel-gerencial-360.spec.js` para carga del dashboard, trigger de alerta y screenshot de evidencia.

## [0.8.5] — 2026-03-13

### Added

**Backend — Sprint 11 Portal B2B Cliente**

- Nuevos endpoints en `maroc_b2b.api.comercial` para portal cliente:
  - `get_portal_dashboard`
  - `get_portal_estado_cuenta`
  - `crear_pedido_portal`
  - `create_support_ticket`
- Aislamiento por tenant para usuarios portal (`403 Forbidden` al forzar `id_cliente` ajeno).
- Bloqueo de creacion de pedidos por mora mayor a 30 dias.
- Ticket SOS crea `Issue`, adjunta foto base64 y dispara alerta a Calidad (email + `Notification Log`).

### Added

**Frontend — Portal B2B self-service**

- Nuevo cliente API `kiosco-pwa/src/api/customerPortal.js`.
- Nueva vista `kiosco-pwa/src/views/PortalB2BCliente.vue` con:
  - Estado de cuenta en tiempo real.
  - Panel de sugerencias de catalogo.
  - Pedido rapido con bloqueo visual por mora.
  - Formulario SOS con foto movil (`capture="environment"`).
- Nueva ruta `/portal-b2b` en `kiosco-pwa/src/router/index.js`.

### Added

**QA — Evidencia Playwright Sprint 11**

- Nuevo spec `kiosco-pwa/tests/e2e/portal-b2b.spec.js`:
  - Login de cliente portal.
  - Intento de fraude por `id_cliente` ajeno con espera de `403`.
  - Creacion exitosa de ticket SOS.

## [0.8.4] — 2026-03-13

### Fixed

**Frontend — Mensajeria coherente en traslado de cuarentena (Sprint 5)**

- `kiosco-pwa/src/views/TransladoCuarentena.vue`: tras `EP_REC_3` exitoso, la recarga del lote ya no reemplaza el exito con el aviso "Le lot n'est pas en quarantaine MP.".
- Se conserva la confirmacion operativa y el contexto de auditoria del traslado para evitar falsos negativos percibidos por operario.

### Changed

**QA — Cierre determinista Bloque 2 (Sprint 5/6)**

- `kiosco-pwa/tests/e2e/quarantine.spec.js`: expectativa alineada al mensaje real de exito post-traslado.
- `kiosco-pwa/package.json`: `test:e2e:block2` y `test:e2e:block2:headed` ejecutan con `--workers=1` para evitar interferencias de fixtures compartidos.
- Ejecuciones finales en verde: `scripts/smoke/test-bloque-2.ps1` y `npm run test:e2e:block2`.

## [0.8.3] — 2026-03-12

### Added

**QA — Playwright visible para kiosco**

- Configuracion inicial de Playwright en `kiosco-pwa/` con `playwright.config.js`, scripts npm y primer spec E2E de recepcion parcial.
- Nuevo helper `scripts/e2e/prepare-reception-sandbox.ps1` para preparar una Purchase Order abierta antes de ejecutar el navegador automatizado.
- Nueva suite `@block2` con specs de recepcion, cuarentena, reimpresion e inventario ciego.
- Nuevo orquestador `scripts/smoke/test-bloque-2.ps1` para validar los tres sprints del Bloque 2 en una sola pasada.

### Fixed

**Frontend — Cierre del modal de recepcion tras submit exitoso**

- `kiosco-pwa/src/views/ReceptionMateriaux.vue`: el modal ya se cierra correctamente despues de `EP_REC_2` sin quedar bloqueado en estado `submitting`.

**Backend — Elevacion segura en recepcion e inventario**

- `backend/gcma_kiosco/gcma_kiosco/api/recepcion.py`: la elevacion interna vuelve a permitir operaciones nativas de ERPNext que requieren permisos de sistema, sin corromper la sesion HTTP del operario.

## [0.8.2] — 2026-03-11

### Added

**Backend — Sprint 6 Inventario ciego**

- Nuevo endpoint `subir_conteo_fisico` (EP_REC_5) en `backend/gcma_kiosco/gcma_kiosco/api/recepcion.py` para crear borradores `Stock Reconciliation`.
- Nuevos helpers `bootstrap_inventario_ciego_sandbox` e `inspect_latest_blind_inventory_reconciliation` para smoke y diagnostico.

### Added

**Frontend — Conteo offline persistente**

- Nuevo store `kiosco-pwa/src/stores/blindInventory.js` con persistencia por warehouse.
- Nueva vista `kiosco-pwa/src/views/InventarioCiego.vue` y nueva ruta `/inventario-ciego`.
- Nuevo parser `kiosco-pwa/src/utils/qr.js` y soporte de cola diferida `EP_REC_5_SUBIR_CONTEO` en `syncQueue.js`.

### Added

**QA — Smoke Sprint 6**

- Nuevo script `scripts/smoke/test-ep-inventario-ciego.ps1` con bootstrap de 5 lotes, alta EP_REC_5 e inspeccion del draft persistido.

### Changed

**Docs — Cobertura Sprint 6**

- `docs/API.md`, `docs/FRONTEND.md`, `docs/RUNBOOK.md` y `docs/plan-v2/sprints/bloque-2-inventario/SPRINT-06_INVENTARIO_CIEGO.md` actualizados con el flujo de inventario ciego.

## [0.8.1] — 2026-03-11

### Added

**Backend — Sprint 5 Cuarentena y re-etiquetado**

- Nuevos endpoints `trasladar_lote_aprobado` (EP_REC_3) y `get_lote_para_impresion` (EP_REC_4) en `backend/gcma_kiosco/gcma_kiosco/api/recepcion.py`.
- Nuevo helper `bootstrap_cuarentena_transfer_sandbox` para preparar stock de cuarentena reutilizable en smoke tests.
- Perfil `quality` ampliado para permitir acceso al modulo `reception` cuando se use el flujo de inventario.

### Added

**Frontend — Sprint 5 Inventario operativo**

- Nuevas vistas `TransladoCuarentena.vue` y `ReimpresionEtiqueta.vue` con scanner HID/manual, verificacion EP5 y acciones touch-first.
- Nuevas rutas `/traslado-cuarentena` y `/reimpresion` protegidas por `module: reception`.
- `printer.js` generalizado para reuso de etiquetas kiosco con `printSingleKioscoLabel`.

### Added

**QA — Smoke cuarentena Sprint 5**

- Nuevo script `scripts/smoke/test-ep-cuarentena.ps1` con bootstrap, happy path EP_REC_3, rechazo por stock insuficiente y contrato EP_REC_4.

### Changed

**Docs — Cobertura Sprint 5**

- `docs/API.md`, `docs/FRONTEND.md`, `docs/RUNBOOK.md` y el sprint plan de Bloque 2 actualizados con contratos, rutas y smoke operativo.

## [0.8.0] — 2026-03-11

### Added

**Backend — Sprint 4 Recepcion de materias primas**

- Nuevo modulo `backend/gcma_kiosco/gcma_kiosco/api/recepcion.py` con EP_REC_1 `get_compras_pendientes` y EP_REC_2 `registrar_recepcion`.
- Bootstrap sandbox reutilizable para smoke de recepcion con `Purchase Order` abierta de prueba.
- `registrar_recepcion` crea `Purchase Receipt` nativo en `Cuarentena MP - PDM` y auto-genera `Quality Inspection` de entrada cuando el item lo exige.

### Added

**Frontend — Modulo Reception**

- Nueva vista `ReceptionMateriaux.vue` accesible en `/recepcion`.
- Nuevo componente `ReceptionCaptureModal.vue` para captura touch-first de qty, lote proveedor y vencimiento.
- Nuevo servicio `src/utils/printer.js` para impresion local ZPL en `http://localhost:9000/print`.
- `ModuleHub.vue` incorpora el modulo `reception`.

### Added

**QA — Smoke recepcion**

- Nuevo script `scripts/smoke/test-ep-recepcion.ps1` con bootstrap sandbox + validacion HTTP de EP_REC_1 y EP_REC_2.
- `scripts/smoke/smoke-kiosco.ps1` usa badge de calidad dedicado para EP6/EP7.

### Changed

**Docs — Cobertura Sprint 4**

- `docs/API.md`, `docs/FRONTEND.md` y `docs/RUNBOOK.md` actualizados con contratos y operativa del modulo de recepcion.

## [0.7.7] — 2026-03-11

### Added

**QA — Tests focalizados para EP5**

- Nuevo script `scripts/smoke/test-ep5-info-lote.ps1` con dos casos ejecutables:
  - EP5 positivo (lote + item validos).
  - EP5 contrato de error con `item_code` incompatible (HTTP 422 esperado).

### Changed

**Runbook — Validacion post-deploy de EP5**

- `docs/RUNBOOK.md`: añadida seccion de test focalizado EP5 para verificacion rapida tras recarga de backend.

## [0.7.6] — 2026-03-11

### Added

**Release readiness — Cierre tecnico Bloque 1**

- Nueva plantilla de checklist y evidencia en `docs/releases/BLOQUE1_RELEASE_CHECKLIST.md`.
- Nueva plantilla de acta de cierre en `docs/releases/BLOQUE1_ACTA_CIERRE.md`.

### Changed

**Runbook — Flujo de pre-release estandarizado**

- `docs/RUNBOOK.md`: nueva seccion "Release Readiness Bloque 1" con secuencia obligatoria build + smoke + registro de evidencia.

## [0.7.5] — 2026-03-11

### Added

**QA — Smoke suite operativa de endpoints críticos**

- Nuevo script `scripts/smoke/smoke-kiosco.ps1` para validación rápida de EP1, EP1b, EP2, EP3, EP5 y EP6.
- Soporte opt-in para operaciones de escritura: `-IncludeWriteOps` (EP4) y `-IncludeQualityWriteOps` (EP7).
- Salida estandarizada por paso (`PASS`/`FAIL`) con exit code `0/1` para uso en validación de release.

### Changed

**Runbook — Ejecución Sprint 2**

- `docs/RUNBOOK.md`: añadida sección "Smoke Suite Sprint 2" con comandos base (read-only) y comandos de write-ops controlados.

### Fixed

**Backend — Consistencia HTTP en restauración de sesión**

- `get_operario_session` ahora devuelve `401` cuando no existe sesión válida (`NO_ACTIVE_SESSION`), alineado con el contrato documentado.

## [0.7.4] — 2026-03-11

### Added

**Backend — EP5 `info_lote` implementado**

- Nuevo endpoint `GET /api/method/gcma_kiosco.api.kiosco.info_lote` con consulta rapida de lote.
- Respuesta incluye `lote` (item/caducidad/dias restantes), `stock_por_almacen` y `total_qty`.
- Validaciones funcionales implementadas: `MISSING_PARAMS`, `BATCH_NOT_FOUND`, `BATCH_ITEM_MISMATCH`.

### Changed

**Frontend — Integración EP5 en laboratorio**

- `kiosco.js`: nuevo wrapper `getInfoLote(batchNo, itemCode?)`.
- `LaboratoireQC.vue`: al abrir un lote, el drawer consulta EP5 y muestra expiracion, dias restantes y stock por almacen.

### Docs

- `docs/API.md`: sección EP5 completada (request/response/errores/curl).
- `docs/FRONTEND.md`: actualizado uso de EP5 en wrappers y consola de laboratorio.

## [0.7.3] — 2026-03-11

### Changed

**Docs — Sincronización checkpoint documental con estado real**

- `docs/FRONTEND.md`: reescrito para reflejar la arquitectura vigente (light theme industrial, rutas por perfil, flujo EP1–EP4 y EP6/EP7, componentes compartidos, scanner HID y estado de implementación real).
- `backend/gcma_kiosco/README.md`: actualizado de "API en desarrollo" a estado real de endpoints implementados (EP1–EP4, EP6, EP7) y comandos actuales de instalación/seed en Docker.

### Fixed

**Frontend — Versión visible en login**

- `kiosco-pwa/src/views/LoginQR.vue`: badge de versión actualizado de `v0.5.0` a `v0.7.2` para alinear la UI con el release activo.

## [0.7.2] — 2026-03-10

### Fixed

**Frontend — LaboratoireQC drawer bugs en móvil HTTP**

- `crypto.randomUUID()` requiere contexto seguro (HTTPS). El kiosco accedido desde móvil vía HTTP (`http://192.168.x.x:5173`) hace que `crypto.randomUUID` sea `undefined`. `buildDefaultRows()` y `addParameterRow()` lanzaban `TypeError` silencioso → `parameterRows` quedaba `[]` → el `v-for` no renderizaba filas y el botón «Ajouter» no tenía efecto. Fix: contador simple `nextRowId()` reemplaza todas las llamadas a `randomUUID`.
- Al abrir el Drawer en iOS, PrimeVue enfoca automáticamente el primer input interactivo (`InputNumber` de «Quantite inspectee»). iOS hace scroll automático para mostrarlo, dejando el bloque «Produit» y el `SelectButton` «Verdict» fuera del viewport. Fix: `@show` handler + `nextTick(() => contentScrollRef.scrollTop = 0)` resetea el scroll al inicio del contenido cada vez que se abre el Drawer.
- Botones Num./Texte y Trash en las filas de parámetro cambiados de `flex-col` a `flex-row` en mobile para reducir la altura por fila.

## [0.7.1] — 2026-03-10

### Fixed

**Frontend — LaboratoireQC Drawer sin scroll en mobile**
- `style.css`: añadidos estilos globales `.p-drawer { display: flex; flex-direction: column }` y `.p-drawer-content { flex: 1 1 0%; min-height: 0; overflow-y: auto; -webkit-overflow-scrolling: touch }`. El Drawer de PrimeVue Aura preset ocultaba el contenido que superaba la altura de pantalla.
- `LaboratoireQC.vue`: refactorizado para usar el slot `#container` del Drawer (control total de layout). Estructura: header fijo `shrink-0` + content `flex-1 overflow-y-auto min-h-0` (con `ref="contentScrollRef"`) + footer fijo `shrink-0`. El `min-h-0` en el div de contenido es necesario para que `overflow-y: auto` sea respetado por el navegador en un flexbox child.
- Botones «Annuler» / «Valider» movidos al footer fijo del Drawer (siempre visibles independientemente del scroll del contenido).

## [0.7.0] — 2026-03-10

### Changed

**Frontend — Responsividad Mobile/Tablet (toda la app)**
- `KioskLayout.vue`: corregido bug crítico de Tailwind JIT — `max-w-${props.maxWidth}` reemplazado por lookup map estático (`{ '5xl': 'max-w-5xl', ... }`). Las clases dinámicas construidas con interpolación no se detectan en JIT.
- `KioskLayout.vue`: padding responsive `px-3 py-3 sm:px-5 sm:py-5`, gap `gap-4 sm:gap-5`
- `LoginQR.vue`: grid principal `xl:` → `lg:`, heading `text-2xl sm:text-3xl md:text-4xl`, step cards `sm:grid-cols-2 md:grid-cols-3`, botón manual `w-full md:w-auto md:min-w-[15rem]`
- `ModuleHub.vue`: heading responsive, grid `xl:` → `lg:`, module cards `md:grid-cols-2`, CTA `h-14` → `h-16`
- `TareasList.vue`: heading responsive, stats `sm:grid-cols-2 md:grid-cols-3`, card grid `xl:` → `lg:`, botón principal `w-full lg:w-auto lg:min-w-[16rem]` (sin overflow en 320px), retry `h-14` → `h-16`
- `PokaYokeScanner.vue`: heading responsive, grid principal `xl:` → `lg:`, filas de material `xl:` → `sm:`, stats header con `md:min-w-[8rem]` (sin overflow), extras close button `h-10` → `h-12`, extras input `px-3 py-3 text-lg` → `px-4 py-4 text-xl` (cumple spec fat-finger), botón manual `h-14` → `h-16`, botón retry goBack `h-14` → `h-16`
- `LaboratoireQC.vue`: heading responsive, grid principal `xl:` → `lg:`, metrics `lg:grid-cols-3` → `md:grid-cols-3`, "Lancer l'inspection" `h-13` → `h-16`, lot stats `grid-cols-2` → `grid-cols-1 sm:grid-cols-2`, botón add param `h-11` → `h-12`, toggle num/texte `h-11` → `h-12`, delete param `h-10 w-10` → `h-12 w-12`, drawer inputs `!h-11` → `!h-14`, drawer buttons cancel/submit `h-14` → `h-16`
- `style.css`: font-size root `16px` en mobile, `18px` desde `sm:` (640px) con `@media (min-width: 640px)`. Todos los rem calculan sobre 16px en móvil.

### Fixed
- Eliminada "dead zone" en breakpoint `sm:` (640–1023px) donde ningún layout respondía
- Todos los botones destructivos y secundarios cumplen mínimo h-12 / 48px para uso con guantes

## [0.6.0] — 2026-03-10

### Changed

**Frontend — Migración completa a Light Theme Industrial**
- `style.css`: removidos todos los overrides oscuros (`bg-slate-*`, `text-slate-*`, PrimeVue dark). Nuevas CSS custom properties: `--gcma-bg: #f4f4f5`, `--gcma-panel: #ffffff`, `--gcma-panel-soft: #fafafa`.
  Nuevas clases utilitarias: `.kiosk-panel`, `.kiosk-panel-soft`, `.gcma-data-row`, `.gcma-stat`, `.kiosk-chip`, `.gcma-toolbar`, `.gcma-section-label`, `.kiosk-icon-shell`.
- `App.vue`: `bg-slate-900` → `bg-zinc-100`, shell limpia sin gradientes.
- `KioskLayout.vue`: reescrito con clases light (bg-zinc-100, gap responsive).
- `LoginQR.vue`: tema completo light — bg-white panels, text-zinc-900, blue-600 CTA, badges zinc.
- `ModuleHub.vue`: cards bg-white border-zinc-200, CTA blue-600, badges de módulo light.
- `TareasList.vue`: cards de WO bg-white, badges stock green/red light, cantidades text-zinc-900.
- `PokaYokeScanner.vue`: checklist con bg-zinc-50 + border-zinc-200, scanner status light, overlays error/success/loading via FullScreenOverlay (mantiene fondos de color intenso para estados críticos).
- `LaboratoireQC.vue`: métricas y cards de lote en blanco/zinc, drawer bg-white, decision switch light.
- `ScanStation.vue`: indicador de estado con iconos y colores light (blue idle, green success, red error).
- `ManualInputModal.vue`: dialog bg-white border-zinc-200, input bg-zinc-50.

**Instrucciones**
- `context.instructions.md`: sección DESIGN SYSTEM actualizada de dark a light theme.



### Changed

**Frontend — Component extraction & design refactoring**
- New `src/composables/useScanner.js`: shared USB HID barcode scanner logic (was duplicated in LoginQR + PokaYokeScanner)
- New `src/components/KioskLayout.vue`: standardised outer shell wrapper applied to all 5 views
- New `src/components/ScanStation.vue`: scanner state visualiser (idle/scanning/loading/success/error)
- New `src/components/ManualInputModal.vue`: teleported manual QR input dialog (was duplicated in 2 views)
- New `src/components/FullScreenOverlay.vue`: teleported fullscreen overlay for error/success/loading/info states
- New `src/components/EmptyState.vue`: reusable "no data" display component
- `LoginQR.vue` rewritten with useScanner + KioskLayout + ScanStation + ManualInputModal (~285→~190 lines)
- `PokaYokeScanner.vue` rewritten with useScanner + KioskLayout + ScanStation + ManualInputModal + FullScreenOverlay (~605→~350 lines)
- `TareasList.vue` rewritten with KioskLayout + EmptyState
- `ModuleHub.vue` rewritten with KioskLayout, removed PrimeVue Card/Button/Tag dependency
- `LaboratoireQC.vue` rewritten with KioskLayout + EmptyState, kept PrimeVue Drawer + form inputs
- Updated `docs/FRONTEND.md` with new component architecture, composables, and shared component API reference

## [0.4.0] — 2026-03-10

### Added

**Backend — Perfiles reales de kiosco**
- Nuevo custom field `Employee.custom_kiosk_profile` con perfiles `production` y `quality`
- Nuevo badge semilla de laboratorio `QC-2026-BADGE-00077` para Karim El Idrissi
- EP1 y EP1b devuelven `profile_code`, `profile_label`, `allowed_modules` y `default_route`
- Los endpoints de producción y laboratorio rechazan badges del perfil incorrecto con `PROFILE_NOT_ALLOWED`

**Frontend — Separación por perfil**
- El store Pinia ahora expone `profileCode`, `profileLabel`, `allowedModules` y `hasModule()`
- Router protegido por `meta.module` para bloquear acceso directo a módulos no autorizados
- Login redirige directamente al módulo único permitido cuando el badge solo tiene un perfil
- `ModuleHub.vue` filtra tarjetas por perfil y muestra el perfil kiosco activo

**Backend — Bloque 4 Control de Calidad**
- Nuevo módulo `gcma_kiosco.api.calidad` con endpoints nativos de laboratorio
- `get_lotes_cuarentena` lista lotes de PT con saldo positivo en `Cuarentena PT - PDM`
- `aprobar_calidad` crea `Quality Inspection` manual y, si aprueba, libera stock con `Stock Entry` `Material Transfer`
- El `Quality Inspection` queda enlazado al `Stock Entry Detail.quality_inspection`

**Backend — EP4 `reportar_consumo`**
- Endpoint POST para registrar consumo real de materiales al finalizar la mezcla
- Calcula desviaciones vs BOM teórica (cantidad, porcentaje)
- Alerta WARNING si algún material supera 10% de desviación
- Registra consumo como Comment en la Work Order con trazabilidad de documentos generados
- Recibe lotes usados y extras por `item_name` (guardrail G3 — nunca `item_code` visible en el Kiosco)
- Crea `Stock Entry` nativos `Material Transfer for Manufacture` y `Manufacture`
- Usa `SerialBatchCreation` nativo de ERPNext para materiales con lote y cierra la WO en `Completed`

**Frontend — Modal de Consumo (EP4) en PokaYokeScanner.vue**
- Diálogo "Standard ou Extra ?" con 2 botones fat-finger (emerald / amber)
- Formulario de extras: lista scrollable de ingredientes con inputs numéricos `qty_extra`
- Overlay de éxito: pantalla completa emerald "LOT TERMINÉ — Placer en zone de Quarantaine" con redirect 3s
- Overlay de error: pantalla completa rose con botón "Réessayer"
- Máquina de estados: idle → asking → extras → submitting → success / error
- Iconos lucide: Scale, PackageCheck

**Frontend — API Wrapper EP4**
- `reportarConsumo(workOrder, lotesUsados, consumosExtra)` en `kiosco.js` con `JSON.stringify` para serializar mapas como form-urlencoded

**Frontend — Hub + Laboratoire (Bloque 4)**
- PrimeVue activado globalmente con preset Aura dark y `ToastService`
- Nuevo `ModuleHub.vue` como entrada post-login para elegir Production / Laboratoire
- Nueva pantalla `LaboratoireQC.vue` con KPIs, búsqueda, cards de lotes y drawer de inspección
- El laboratorio consume EP6 `get_lotes_cuarentena` y EP7 `aprobar_calidad`
- El flujo de login ahora redirige al hub, no directamente a producción

### Changed
- `docs/API.md`: Documentación completa de EP4 (request, response, errores, curl)
- `docs/FRONTEND.md`: Flujo EP4, tabla de API wrappers
- `docs/RUNBOOK.md`: la demo contable ya no es manual; se verifica cierre automático con EP4
- `docs/API.md`: se documentan EP6/EP7 de Control de Calidad y la base URL `gcma_kiosco.api.calidad`
- `docs/RUNBOOK.md`: se añade la nota operativa de ERPNext v16 para lotes en cuarentena usando `Serial and Batch Entry`
- `gcma_kiosco.setup.test_data.run`: ahora resetea la demo y recrea un entorno repetible con fixtures de caos
- `gcma_kiosco.setup.test_data.run`: también limpia `Quality Inspection` y `Stock Entry` de liberación QC antes de reinyectar la demo
- `reportar_consumo`: añade guardrail `EXTRA_QTY_ABSURD` para bloquear errores groseros de tipeo en extras
- Sesión del kiosco: restauración desde cookie `sid`, logout explícito y headers anti-cache para evitar fallos entre navegadores
- `App.vue`, `main.js` y `style.css`: nueva shell visual con PrimeVue dark, fondo atmosférico y overrides profesionales de componentes
- `TareasList.vue`: añade navegación directa al hub y al módulo de laboratorio

### Fixed
- `aprobar_calidad`: el flujo rechazado ahora referencia el `Stock Entry` que originó el lote en cuarentena, evitando errores nativos de `Quality Inspection` sin referencia
- `get_lotes_cuarentena` y la validación de saldo por lote usan `Serial and Batch Entry` como fuente principal en ERPNext v16

## [0.3.0] — 2025-07-25

### Added

**Design System — Industrial Premium MES**
- Tema oscuro industrial (bg-slate-900 fondo, bg-slate-800 cards/headers)
- Paleta: emerald-600 (acción primaria), rose-600 (errores), amber-400 (warnings)
- Librería de iconos lucide-vue-next reemplaza todos los emoji y SVG inline
- Animaciones CSS: shake (error overlay), fade-in (modales), pulse-ring (finalizar)
- Reglas UX fat-finger: botones h-16 min, rounded-md (no rounded-2xl/3xl), select-none

### Changed

**Frontend — LoginQR.vue**
- Reescrito completo: tema oscuro, iconos lucide (ScanBarcode 64px, ShieldCheck, Loader2, etc.)
- Modal de saisie manuelle estilo shadcn (bg-slate-800, border-slate-700, rounded-md)
- Barra superior con ShieldCheck + versión
- Input font-mono, botón emerald "Valider" con ChevronRight

**Frontend — TareasList.vue**
- Reescrito completo: cards bg-slate-800 con border-slate-700/60 rounded-md
- Header bg-slate-800/80 con RefreshCw y LogOut (lucide icons)
- Badges de stock (emerald/amber) y estado (amber/slate) con bordes sutiles
- Botón h-16 bg-emerald-600 "DÉMARRER LA PRODUCTION" con icono Play
- Metadatos con iconos Beaker y Clock

**Frontend — PokaYokeScanner.vue**
- Reescrito completo: tema oscuro, checklist con cards bg-slate-800
- Error overlay: bg-rose-600 + animate-shake + TriangleAlert 80px + tap-to-dismiss (sin botón)
- Modal saisie manuelle estilo shadcn con X close button
- Checklist: CircleCheckBig para validados, badges rounded-md emerald/rose
- Scan status bar con iconos lucide (ScanBarcode, Loader2, CircleCheckBig)
- Botón "FINALISER LE MÉLANGE" con animate-pulse-ring y icono Check

**Instrucciones**
- Sección DESIGN SYSTEM añadida a context.instructions.md (paleta, iconos, UX, animaciones, patrones)

## [0.2.0] — 2026-03-09

### Added

**Frontend — TareasList.vue (EP2)**
- Tarjetas industriales gigantes con nombre del producto, cantidad pendiente, badge de estado
- Indicador de stock de materiales (✓ Stock complet / ⚠ Stock insuffisant)
- Botón "DÉMARRER LA PRODUCTION ▶" por tarjeta
- Estados: loading, error con retry, empty state
- Botón refresh + logout en header

**Frontend — PokaYokeScanner.vue (EP3)**
- Checklist de ingredientes con tracking local de validación
- Escáner USB HID con guard de modal y guard de error
- UX semafórica: flash verde por material, overlay rojo STOP pantalla completa
- Overlay CRITICO con `animate-pulse` para errores de seguridad (material incorrecto, lote caducado)
- Barra de estado coloreada (ready/scanning/loading/success)
- Entrada manual (Saisie Manuelle) con auto-focus
- Botón pulsante "FINALISER LE MÉLANGE ✓" cuando todos los materiales están validados
- Contador de progreso en header (X/Y validés)

### Changed
- `kiosco.js`: `getTareas()` ahora acepta `company` y `warehouse` como parámetros

## [0.1.0] — 2025-07-25

### Added

**Backend — Custom App `gcma_kiosco`**
- `seed_data.py`: 15 pasos idempotentes (UoMs, Companies, Warehouses, Items, BOM, Suppliers, Customers, Price Lists, Custom Fields, Test Employee)
- `test_data.py`: Stock artificial (2000 Kg/MP con LOTE-TEST-*) + Work Order MFG-WO-2026-00001
- EP1 `login_operario` — Autenticación por QR badge con sesión Frappe
- EP2 `get_tareas` — Work Orders pendientes con BOM explodida y stock
- EP3 `validar_material` — Poka-Yoke: material, lote, caducidad, stock
- `qr_utils.py` — Parser QR con separador `|` (contrato Zebra)
- `exempt_csrf()` — Hook `before_request` para eximir CSRF en rutas del kiosco
- `hooks.py` — Fixtures Custom Fields (`custom_qr_*`), before_request hook

**Frontend — PWA Kiosco**
- Scaffolding Vue 3 + Vite 7 + Tailwind CSS 4 + Pinia + Router
- `client.js` — Axios con interceptor form-urlencoded + desenvuelve Frappe envelope
- `kiosco.js` — Wrappers EP1/EP2/EP3
- `operario.js` — Store Pinia (sesión operario)
- `LoginQR.vue` — Escáner USB HID + modal de entrada manual (Plan B)
- `TareasList.vue` — Lista de Work Orders con materiales
- `PokaYokeScanner.vue` — Validación de materiales por QR
- PWA manifest (standalone, portrait, theme industrial)
- Estilos industriales (18px font, no zoom, no select, 100dvh)

**Documentación**
- `index.html` — Diseño funcional (bloques de análisis, inventario, aprovisionamiento)
- `technical-design-data-foundation.html` — Data Foundation + PoC Sandbox
- `docs/API.md` — Referencia completa de endpoints REST
- `docs/FRONTEND.md` — Arquitectura PWA, componentes, patrones
- `docs/RUNBOOK.md` — Operaciones Docker, deploy, troubleshooting
- `README.md` — Visión general del proyecto

**Infraestructura**
- Docker Compose con 9 contenedores (Frappe v16.10.10 + ERPNext v16.8.2)
- Empresa PoC: PDM (Peintures du Maroc), 6 almacenes lógicos
- Datos de prueba: Employee Ahmed Benali, badge OP-2026-BADGE-00042
- Git inicializado con `.gitignore` (excluye `frappe_docker/`, `node_modules/`, `dist/`)

### Fixed
- nginx 502 por Docker IP drift → reiniciar siempre `frontend-1` junto con `backend-1`
- `DataError` por Content-Type → interceptor convierte a `URLSearchParams`
- `CSRFTokenError` → `exempt_csrf()` hook desactiva CSRF para rutas del kiosco
