# Bloque 3 - Matriz Profesional de Casos QA (Sprints 07-12)

## 1. Convenciones
- `ID`: identificador único del caso.
- `Tipo`: API, E2E, Seguridad, Performance, Scheduler, Datos.
- `Prioridad`: Critica, Alta, Media.
- `Automatizable`: Si/No.
- `Evidencia`: screenshot, video, log, respuesta JSON, query DB.

## 2. Matriz de Casos

| ID | Sprint | Tipo | Prioridad | Objetivo | Precondiciones | Pasos resumidos | Resultado esperado | Automatizable | Evidencia |
|---|---|---|---|---|---|---|---|---|---|
| B3-S07-API-001 | 07 | API | Alta | Validar check-in en geocerca | Cliente con `gps_lat/gps_lng` válidos, sesión vendedor | POST check-in con coordenadas dentro de radio | `es_visita_valida=true`, respuesta 200 | Si | JSON response + DB row `CheckIn_Visita` |
| B3-S07-API-002 | 07 | API | Alta | Detectar desviación de geocerca | Cliente con GPS definido | POST check-in con coordenadas fuera de radio | `es_visita_valida=false`, registro persiste | Si | JSON response + DB row |
| B3-S07-E2E-003 | 07 | E2E | Media | Flujo UI rutas + check-in | Ruta diaria con clientes cargados | Abrir rutas, iniciar check-in, confirmar en UI | Estado local y backend consistentes | Si | Video + screenshot + request log |
| B3-S07-DAT-004 | 07 | Datos | Media | Integridad de ruta y visitas | Fixtures de `Ruta_Comercial_Dia` y `Visitas_Programadas` | Consultar ruta y tabla hija | Orden de visitas consistente, IDs válidos | Si | Query DB |
| B3-S08-API-005 | 08 | API | Critica | Estado de cuenta correcto | Cliente con deuda y límites configurados | GET estado de cuenta | Campos de deuda y bloqueo correctos | Si | JSON response |
| B3-S08-API-006 | 08 | API | Critica | Bloqueo por mora vigente | Cliente con mora > regla | Intentar crear pedido | Pedido bloqueado con error de negocio | Si | JSON response + ausencia de SO |
| B3-S08-E2E-007 | 08 | E2E | Alta | Pedido offline y sincronización | Outbox habilitado, cliente válido | Modo offline, crear pedido, reconectar | Pedido se guarda local y luego sincroniza una sola vez | Si | Video + logs + DB Sales Order |
| B3-S08-API-008 | 08 | API | Alta | Idempotencia básica de sync | Payload repetido controlado | Ejecutar sync consecutivo | Sin duplicados indebidos | Si | Conteo Sales Order + payload logs |
| B3-S09-API-009 | 09 | API | Critica | FEFO bloquea lote incorrecto | Dos lotes con expiración distinta y stock | POST validar FEFO con lote nuevo | 400 ValidationError con mensaje FEFO | Si | JSON error + log |
| B3-S09-API-010 | 09 | API | Critica | FEFO permite lote correcto | Mismo setup FEFO | POST validar FEFO con lote viejo | `status=ok`, cálculo restante correcto | Si | JSON response |
| B3-S09-E2E-011 | 09 | E2E | Alta | No bypass FEFO desde frontend | UI picking operativa | Intentar cerrar picking tras rechazo FEFO | UI bloquea avance y muestra error | Si | Video + screenshot |
| B3-S10-API-012 | 10 | API | Critica | POD registra firma y foto válidas | Delivery Note en tránsito | POST registrar POD con base64 válidos | Adjuntos creados, estado entrega actualizado | Si | JSON response + File rows + DN fields |
| B3-S10-API-013 | 10 | API | Alta | Rechazo de POD inválido | DN válida | Enviar base64 inválido | Error controlado de validación | Si | JSON error + log |
| B3-S10-E2E-014 | 10 | E2E | Alta | Flujo chofer POD en móvil | Entregas pendientes y cámara simulada | Seleccionar entrega, firmar canvas, adjuntar foto, enviar | Mensaje éxito y DN sale de pendientes | Si | Video + screenshot + DB verify |
| B3-S11-SEC-015 | 11 | Seguridad | Critica | Aislamiento tenant en portal | Usuario portal Customer C y otro customer D | Forzar `id_cliente` de D en endpoint portal | HTTP 403 Forbidden | Si | Request/response capture |
| B3-S11-API-016 | 11 | API | Alta | Ticket SOS crea Issue | Usuario portal válido | POST create_support_ticket | `status=success`, Issue creado | Si | JSON response + DB Issue |
| B3-S11-API-017 | 11 | API | Alta | Alerta a Calidad por SOS | Roles calidad configurados | Crear ticket SOS | Email/notificación in-app registrada | Parcial | Notification Log + mail log |
| B3-S11-E2E-018 | 11 | E2E | Alta | Flujo portal cliente completo | Credenciales portal válidas | Login portal, ver dashboard, crear SOS | UI consistente, ticket visible | Si | Video + screenshot |
| B3-S12-API-019 | 12 | API | Critica | Dashboard 360 responde agregado correcto | Datos comerciales y check-ins cargados | GET panel_gerencial_360 | scorecard, hit-rate y cobertura resumen válidos | Si | JSON response |
| B3-S12-PERF-020 | 12 | Performance | Critica | Carga dashboard < 2s | Cache caliente y dataset QA | Medir p95 de endpoint dashboard | p95 <= 2s | Si | Métrica/benchmark report |
| B3-S12-API-021 | 12 | API | Alta | Cobertura mapa con coordenadas válidas | Check-ins del día | GET cobertura mapa | `lat/lng` válidos y estados correctos | Si | JSON + screenshot mapa |
| B3-S12-SCH-022 | 12 | Scheduler | Alta | Job abandono ejecuta y registra salida | Config churn en site_config | Ejecutar job manual/scheduler | total alertas y recipients en resultado/log | Si | job log + JSON result |
| B3-S12-API-023 | 12 | API | Media | Export CSV consistente | Dataset scorecard listo | GET export_scorecard_csv | archivo CSV con columnas esperadas | Si | Archivo descargado + checksum |
| B3-S12-REP-024 | 12 | Datos | Media | Reporte fotos competencia completo | Issues/files de competencia existentes | GET reporte fotos competencia | listado con metadatos y URLs válidas | Si | JSON + prueba de enlaces |
| B3-REG-025 | 07-12 | Regresión | Critica | No romper contratos existentes | Suite bloque 3 preparada | Ejecutar smoke + E2E críticos | Sin fallos críticos | Si | Reporte consolidado |

## 3. Criterio de salida por ciclo
1. 100% casos críticos ejecutados.
2. 100% casos críticos en Pass o con waiver formal aprobado.
3. Cobertura mínima del 90% en casos de prioridad alta.
4. Evidencia archivada y trazada por ID de caso.

## 4. Definición de evidencia mínima por caso
- API: request, response, status code y payload esperado.
- E2E: video o screenshot clave + logs de red.
- Scheduler: log de ejecución + resultado del job.
- Performance: métrica p95 documentada con método de medición.
- Seguridad: prueba de ataque/forzado y respuesta de rechazo.
