# Bloque 3 - Plantilla de Evidencia y Reporte Final Go/No-Go

## 1. Objetivo
Estandarizar la evidencia QA del Bloque 3 (Sprints 07-12) y formalizar la decision final Go/No-Go para release.

## 2. Estructura recomendada de evidencias
Ruta sugerida por fecha de ejecucion:

- `qa/evidence/block3/YYYY-MM-DD/`

Subcarpetas:

- `api/` (requests/responses JSON, contratos)
- `e2e/` (screenshots, videos, traces)
- `scheduler/` (logs de jobs, notificaciones)
- `performance/` (métricas p95, tiempos de carga)
- `security/` (pruebas tenant isolation/autorizacion)
- `reportes/` (resumen ejecutivo diario/final)

## 3. Plantilla de evidencia por caso

### 3.1 Metadatos
- ID caso:
- Sprint:
- Tipo:
- Prioridad:
- Ambiente:
- Build/commit evaluado:
- Fecha/hora ejecucion:
- Ejecutado por:

### 3.2 Resultado
- Estado: Pass / Fail / Blocked / Skipped
- Resultado esperado:
- Resultado obtenido:
- Observaciones:

### 3.3 Evidencia adjunta
- Request payload:
- Response payload:
- Status code:
- Screenshot(s):
- Video/trace:
- Query DB / log técnico:

### 3.4 Defecto (si aplica)
- ID ticket:
- Severidad:
- Reproducibilidad:
- Impacto negocio:
- Owner asignado:
- ETA fix:

## 4. Checklist de evidencia mínima obligatoria
1. Todos los casos críticos con evidencia completa.
2. Casos fallidos con defecto registrado y reproducible.
3. Logs scheduler adjuntos para alertas de abandono.
4. Evidencia de seguridad para forzado de tenant (403).
5. Evidencia performance para panel gerencial (p95).
6. Trazabilidad caso -> evidencia -> resultado -> ticket.

## 5. Resumen ejecutivo diario (plantilla)
- Fecha:
- Build/commit:
- Casos ejecutados (total/pass/fail/blocked/skipped):
- Defectos nuevos (criticos/altos/medios):
- Defectos cerrados:
- Riesgo residual:
- Decision del dia: Go parcial / No-Go
- Acciones para el siguiente ciclo:

## 6. Reporte final Go/No-Go (plantilla)

### 6.1 Identificacion
- Bloque: 3 (Sprints 07-12)
- Fecha de decision:
- Version candidata:
- QA Lead:
- Stakeholders presentes:

### 6.2 Cobertura de ejecucion
- Casos totales planificados:
- Casos ejecutados:
- Cobertura (%):
- Casos criticos ejecutados (%):
- Casos criticos en Pass (%):

### 6.3 Estado de defectos
- Criticos abiertos:
- Altos abiertos:
- Medios abiertos:
- Waivers aprobados:

### 6.4 Validaciones clave Bloque 3
- Geocerca y check-in: Pass / Fail
- Mora y bloqueo comercial: Pass / Fail
- FEFO server-side: Pass / Fail
- POD firma/foto y cierre DN: Pass / Fail
- Tenant isolation portal: Pass / Fail
- SOS + alertas calidad: Pass / Fail
- Dashboard 360 + mapa + CSV: Pass / Fail
- Scheduler abandono parametrizable: Pass / Fail

### 6.5 SLO/SLA
- p95 panel gerencial <= 2s: Cumple / No cumple
- p95 endpoints críticos <= 800ms: Cumple / No cumple
- Tasa sincronizacion offline >= 99%: Cumple / No cumple

### 6.6 Riesgo residual
- Riesgo 1:
- Riesgo 2:
- Mitigaciones acordadas:

### 6.7 Decision final
- Decision: GO / NO-GO
- Justificacion:
- Condiciones previas al release (si aplica):

### 6.8 Aprobaciones
- QA Lead:
- Backend Lead:
- Frontend Lead:
- Product/CTO:

## 7. Criterios de decision recomendados

GO:
1. 0 defectos críticos abiertos.
2. 0 defectos altos sin mitigacion aprobada.
3. 100% pruebas críticas ejecutadas con evidencia.
4. SLO/SLA mínimos cumplidos o waiver formal.

NO-GO:
1. Existe al menos 1 crítico abierto sin mitigación.
2. Falla de seguridad en tenant isolation.
3. Evidencia insuficiente para auditoría de casos críticos.
4. Inestabilidad recurrente que invalida resultados.
