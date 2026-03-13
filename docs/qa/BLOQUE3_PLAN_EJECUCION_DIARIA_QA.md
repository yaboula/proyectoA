# Bloque 3 - Plan de Ejecucion Diaria QA (Operativo)

## 1. Objetivo
Estandarizar la ejecucion diaria de pruebas de Bloque 3 (Sprints 07-12) con un checklist accionable por rol, reduciendo variabilidad y asegurando evidencia auditable.

## 2. Roles y responsabilidades
1. QA Lead
- Define alcance diario, prioriza riesgos y valida criterio Go/No-Go.
- Aprueba cierre de ciclo y consolida reporte final.
2. QA Automation Engineer
- Ejecuta suites automatizadas API/E2E.
- Mantiene estabilidad de fixtures y scripts.
3. QA Manual Engineer
- Ejecuta casos exploratorios y validaciones visuales/UX.
- Documenta defectos con evidencia reproducible.
4. Backend Owner (soporte)
- Asiste en análisis de errores API/scheduler.
- Valida fix técnico y trazabilidad en logs.
5. Frontend Owner (soporte)
- Asiste en errores de flujo UI/PWA/offline.
- Valida comportamiento por dispositivo/viewport.

## 3. Ventana diaria sugerida
- 09:00-09:20: Kickoff QA diario y revisión de riesgos.
- 09:20-11:30: Ejecución smoke + API críticos.
- 11:30-13:00: E2E críticos por sprint.
- 14:00-16:00: Retest de defectos y validación no funcional rápida.
- 16:00-17:00: Consolidación evidencia + reporte del día.

## 4. Checklist pre-ejecucion (obligatorio)
1. Entorno QA arriba y estable (backend/frontend/db).
2. Build frontend en verde.
3. Migraciones/fixtures aplicadas.
4. Datos seed de Bloque 3 cargados.
5. Variables de entorno de Playwright configuradas.
6. Estado de rama limpio y versión identificada.
7. Carpeta de evidencia del día creada.

## 5. Plan diario por dia

## Dia 1 - Preparacion y baseline
1. QA Lead
- Confirmar alcance de ciclo y lista de casos críticos.
- Publicar matriz de casos objetivo del día.
2. Automation
- Correr smoke API base de sprints 07-12.
- Verificar estabilidad de scripts y tiempos de ejecución.
3. Manual
- Verificar flujos base por rol (vendedor, chofer, portal, gerente).
- Validar textos críticos y estados UI.
4. Salida esperada
- Baseline de ejecución y lista de bloqueantes iniciales.

## Dia 2 - Sprint 07 y 08
1. Automation
- Ejecutar casos S07 API/E2E (geocerca y rutas).
- Ejecutar casos S08 API/E2E (deuda y offline sync).
2. Manual
- Validar comportamiento offline/online en PWA.
- Verificar no duplicidad de pedidos tras reconexión.
3. QA Lead
- Revisar defectos críticos y definir severidad final.
4. Salida esperada
- Estado consolidado S07-S08 con evidencia.

## Dia 3 - Sprint 09 y 10
1. Automation
- Ejecutar FEFO estricto (rechazo/aceptación).
- Ejecutar POD (firma/foto/actualización de documento).
2. Manual
- Validar UX de bloqueo FEFO y feedback visual.
- Validar captura de firma/cámara en modo móvil.
3. QA Lead
- Validar criterio de aceptación para logística.
4. Salida esperada
- Estado consolidado S09-S10 con evidencia.

## Dia 4 - Sprint 11 y 12 + seguridad
1. Automation
- Ejecutar tenant isolation portal (403 forzado).
- Ejecutar dashboard 360 y alerta abandono.
2. Manual
- Validar portal cliente end-to-end (estado cuenta + SOS).
- Validar panel gerente (mapa, scorecard, export CSV).
3. Seguridad (QA + Backend)
- Revisión de permisos por endpoint crítico.
4. Salida esperada
- Estado consolidado S11-S12 + seguridad.

## Dia 5 - Regresion final y cierre
1. Automation
- Correr regresión de casos críticos Bloque 3.
- Re-ejecutar fallos previos corregidos.
2. Manual
- Sanity visual completa por flujo principal.
3. QA Lead
- Emitir Go/No-Go final y riesgo residual.
4. Salida esperada
- Informe de cierre de ciclo listo para release board.

## 6. Checklist de ejecucion tecnica
1. Smoke API critico
- Estado de cuenta, FEFO, POD, portal SOS, panel 360.
2. E2E critico
- Flujo vendedor (ruta/check-in/pedido).
- Flujo operario FEFO.
- Flujo chofer POD.
- Flujo cliente portal.
- Flujo gerente panel.
3. Scheduler
- Ejecución manual y por cron de alerta abandono.
- Validación de log de envío/notificación.
4. Performance rapida
- Medición p95 endpoint panel en cache caliente.

## 7. Gestión de defectos
1. Campos mínimos obligatorios
- ID caso, sprint, severidad, ambiente, pasos, esperado, obtenido, evidencia.
2. Criterios de severidad
- Critica: bloquea operación o incumple seguridad/contrato.
- Alta: afecta función principal con workaround limitado.
- Media: impacto parcial no bloqueante.
3. SLA de respuesta sugerido
- Critica: triage inmediato, fix en el día.
- Alta: triage en 4h, fix <=24h.
- Media: planificada en siguiente ciclo.

## 8. Evidencia requerida por día
1. Reporte de ejecución (pass/fail/skipped por caso).
2. Screenshots y videos de flujos críticos.
3. Logs de scheduler y notificaciones.
4. Export de resultados de Playwright.
5. Resumen ejecutivo diario (riesgo, avance, bloqueos).

## 9. Criterio Go/No-Go diario
Go:
- 100% casos críticos del día ejecutados.
- 0 defectos críticos abiertos sin mitigación.
- Evidencia completa archivada.

No-Go:
- Cualquier fallo crítico de seguridad/contrato sin contención.
- Inestabilidad de entorno que invalide resultados.
- Ausencia de evidencia mínima auditable.

## 10. Plantilla de resumen diario
- Fecha:
- Build/commit evaluado:
- Casos ejecutados: total / pass / fail / skipped
- Defectos nuevos: critica / alta / media
- Defectos cerrados:
- Riesgo residual:
- Decision del día: Go parcial / No-Go
- Acciones para mañana:
