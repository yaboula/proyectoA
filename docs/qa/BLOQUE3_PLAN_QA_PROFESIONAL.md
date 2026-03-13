# Plan QA Profesional - Bloque 3 (Sprints 07-12)

## 1. Objetivo de calidad
1. Garantizar que Bloque 3 es funcionalmente correcto, seguro, trazable y operable en producción.
2. Validar reglas críticas de negocio: geocerca, mora, FEFO, POD, aislamiento de tenant y alertas gerenciales.
3. Entregar evidencia auditable para cierre técnico y release readiness.

## 2. Alcance
1. Incluido:
- Sprint 07: rutas comerciales y check-in GPS.
- Sprint 08: estado de cuenta, bloqueo por deuda, pedidos offline.
- Sprint 09: picking FEFO con bloqueo server-side.
- Sprint 10: POD con firma y foto.
- Sprint 11: portal B2B cliente y soporte SOS.
- Sprint 12: panel gerencial 360 y job de abandono.
2. Excluido:
- Cambios de negocio fuera de contratos ya aprobados.
- Refactors no funcionales sin impacto de calidad.

## 3. Estrategia de pruebas (pirámide)
1. API Contract Testing (alta prioridad):
- Validación de payloads, errores, códigos HTTP, idempotencia y permisos.
2. E2E críticos (media-alta prioridad):
- Flujos reales por rol en navegador, incluyendo offline y fraude.
3. Pruebas no funcionales (selectivas):
- Performance de panel gerencial, seguridad de aislamiento tenant, robustez del scheduler.
4. Smoke y regresión:
- Smoke diario de endpoints críticos.
- Regresión completa antes de release.

## 4. Matriz de riesgo y prioridad
1. Riesgo crítico:
- FEFO incorrecto permite despacho inválido.
- Tenant isolation roto en portal.
- POD sin evidencia o documento mal cerrado.
2. Riesgo alto:
- Pedidos offline no sincronizan o duplican.
- Bloqueo por mora no aplica.
- Dashboard lento o inconsistente.
3. Riesgo medio:
- Reportes de fotos competencia incompletos.
- Alertas de abandono sin trazabilidad.

## 5. Plan de suites por sprint
1. Sprint 07:
- Check-in válido dentro geocerca.
- Check-in fuera geocerca marcado como desviado.
- Integridad de datos de ruta y visitas.
2. Sprint 08:
- Estado de cuenta correcto por cliente.
- Bloqueo por deuda vencida según regla.
- Pedido offline: guardar local, sincronizar al reconectar, evitar duplicados.
3. Sprint 09:
- Escaneo lote no FEFO bloquea con mensaje claro.
- Lote FEFO correcto permite avanzar.
- No bypass posible desde frontend.
4. Sprint 10:
- Registro POD exige firma y foto válidas.
- Adjuntos persistidos y Delivery Note actualizado.
- Reintentos controlados ante error de red.
5. Sprint 11:
- Usuario cliente solo ve su tenant.
- Intento de forzar id_cliente ajeno devuelve 403.
- Ticket SOS crea Issue y dispara alertas.
6. Sprint 12:
- Dashboard carga bajo 2 segundos con cache caliente.
- Cobertura mapa pinta coordenadas reales.
- Job abandono parametrizable por tipo de cliente.
- Export CSV consistente con scorecard.

## 6. No funcionales (SLO/SLA)
1. Performance:
- Panel gerencial: p95 menor o igual a 2 segundos.
- Endpoints críticos: p95 menor o igual a 800 ms en entorno QA.
2. Seguridad:
- 100% pruebas de aislamiento tenant en endpoints portal.
- Validación de autorización por rol en endpoints gerenciales.
3. Confiabilidad:
- Scheduler diario con log de ejecución y conteo de alertas.
- Tasa de éxito de sincronización offline mayor o igual a 99%.

## 7. Datos y ambientes
1. Ambientes:
- QA estable (base principal), Staging pre-release.
2. Seed data controlado:
- Clientes con perfiles de deuda diversos.
- Lotes FEFO viejo/nuevo.
- Delivery Notes pendientes para POD.
- Usuarios por rol: vendedor, chofer, cliente portal, gerente.
3. Reglas:
- Dataset versionado y reproducible para evidencias.

## 8. Evidencia y trazabilidad
1. Entregables por ciclo:
- Reporte de ejecución por suite.
- Screenshots y videos de E2E críticos.
- Evidencia de logs del scheduler.
- Matriz requisito -> caso -> resultado -> evidencia.
2. Criterio de aceptación del bloque:
- 0 defectos críticos abiertos.
- 0 defectos altos sin mitigación aprobada.
- Cobertura total de DoD por sprint.

## 9. Flujo operativo QA
1. Entrada a ciclo:
- Build verde.
- Migraciones/fixtures aplicadas.
- Datos de prueba cargados.
2. Ejecución:
- Smoke API.
- E2E críticos.
- Seguridad/permiso.
- Performance rápida.
3. Salida:
- Informe Go/No-Go.
- Lista de riesgos residuales.
- Recomendación de release.

## 10. Roadmap sugerido (5 días)
1. Día 1: diseño de casos + dataset + smoke API.
2. Día 2: automatización y ejecución S07-S08.
3. Día 3: automatización y ejecución S09-S10.
4. Día 4: automatización y ejecución S11-S12 + seguridad.
5. Día 5: performance, rerun regresión, informe final de cierre.
