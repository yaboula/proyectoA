# Release Notes v0.8.10

Fecha: 2026-03-14
Tipo: QA Closure Release (Bloque 3)

## Resumen
La version `v0.8.10` consolida el cierre QA del Bloque 3 (Sprints 07-12), incluyendo la regresion final critica, el reporte diario de Dia 5 y la decision formal Go/No-Go para release board.

## Artefactos incluidos
- `docs/qa/BLOQUE3_DIA5_EJECUCION_2026-03-14.md`
- `docs/qa/BLOQUE3_REPORTE_FINAL_GO_NO_GO_2026-03-14.md`
- `CHANGELOG.md` (entrada `0.8.10`)

## Validaciones de cierre
- Regresion E2E critica: `3 passed`.
- Smoke API S07-S12: Pass.
- Seguridad:
  - Tenant isolation forzado: `403`.
  - Acceso anonimo a endpoints criticos: `403`.
- Performance panel gerencial 360 (cache caliente, n=30):
  - `p95=20.62 ms`
  - `avg=8.88 ms`

## Decision
- Estado final QA: `GO`.
- Riesgo residual: bajo (configuracion de cuenta de correo saliente por defecto para notificaciones SOS).

## Referencias
- Commit de cierre QA Bloque 3: `480950b`
- Tag release: `v0.8.10`
