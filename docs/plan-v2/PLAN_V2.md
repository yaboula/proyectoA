# Plan V2 - Ejecucion Tecnica para Developers

Fecha: 2026-03-11
Base de referencia: `index.html` + `docs/CHECKPOINT.md`
Estado inicial: MVP operativo en Bloques 3 y 4, gaps abiertos en Bloques 2 y 5.

## 1. Objetivo del Plan V2

Consolidar el MVP actual en una plataforma operativa estable, auditable y escalable para planta y comercial, cerrando primero deuda funcional critica y luego habilitando los flujos de negocio pendientes.

Objetivos concretos:

1. Cerrar brechas del nucleo operativo (EP5 + robustez + testabilidad).
2. Completar el circuito comercial-logistico del Bloque 5.
3. Reducir riesgo operativo con automatizacion de QA y criterios de release.
4. Alinear documentacion y entregables con estado real del codigo en cada iteracion.

## 2. Principios de Ejecucion

1. API-first estricto: reglas de negocio en backend Frappe.
2. UX de trinchera: touch-first, fat-finger, textos FR para operario.
3. Commits por modulo con Conventional Commits.
4. Cada sprint cierra con evidencia tecnica (build, smoke, checklist release).
5. No se considera terminado sin DoD tecnico + funcional.

## 3. Estructura del Plan V2 por Bloques

### Bloque 1 - Nucleo Operativo y Confiabilidad

Foco: cerrar el core productivo ya desplegado.

Incluye:

- EP5 `info_lote` (backend + wrapper + UI de consumo).
- Hardening de sesion, errores y contratos API (produccion + calidad).
- Smoke suite automatizada para EP1-EP4-EP6-EP7 (+ EP5).
- Criterios de release y runbook de validacion por entorno.

Resultado esperado:

- Circuito planta + laboratorio completo, verificable y con regresion controlada.

### Bloque 2 - Operacion de Inventario de Planta (Gap Bloque 2)

Foco: convertir capacidades documentadas en modulos operativos.

Incluye:

- Pantalla de recepcion de camion (PWA) con API dedicada.
- Flujo de cuarentena de MP operacional en UI.
- Etiquetado operativo con salida estructurada para Zebra.
- Inventario ciego por escaneo (conteo y conciliacion).

Resultado esperado:

- Flujo de aprovisionamiento sin papel de recepcion a stock utilizable.

### Bloque 3 - Comercial y B2B (Gap Bloque 5)

Foco: cierre del ciclo pedido -> expedicion -> entrega.

Incluye:

- Captura movil de pedidos (Web Form/API o canal bot).
- Workflow de credito con aprobacion manager.
- FEFO de expedicion automatizado.
- Kiosco de picking con validacion QR.
- Bon de Livraison + POD fase inicial.

Resultado esperado:

- Circuito comercial-logistico trazable end-to-end.

### Bloque 4 - Gobierno de Plataforma y Escalado

Foco: capacidad de evolucion segura y multi-equipo.

Incluye:

- Pipeline CI minimo (build + lint + smoke).
- Convencion de versionado y release notes tecnicas.
- Matriz de entornos y controles previos a deploy.
- Tablero de KPIs tecnicos (fallos por endpoint, tiempo de respuesta, tasa de reintento).

Resultado esperado:

- Entrega continua con menor riesgo de regresion.

## 4. Roadmap Propuesto

1. Bloque 1 (prioridad alta, ejecucion inmediata)
2. Bloque 2 (prioridad alta, continuidad operativa)
3. Bloque 3 (prioridad alta-negocio, tras cierre operativo base)
4. Bloque 4 (transversal, en paralelo ligero y cierre)

## 5. Definicion de Listo (Definition of Ready)

Un item entra a sprint solo si:

- Tiene objetivo funcional claro.
- Tiene impacto en modulo identificado.
- Tiene criterios de aceptacion verificables.
- Tiene contrato API definido o actualizado.
- Tiene estrategia de prueba (manual + automatizada cuando aplique).

## 6. Definicion de Terminado (Definition of Done)

Un item se considera terminado solo si:

1. Codigo merged sin errores de build.
2. Tests/smoke del alcance en verde.
3. Documentacion actualizada (`API.md`, `FRONTEND.md`, `RUNBOOK.md`, `CHANGELOG.md`).
4. Evidencia de validacion funcional (payloads y respuestas esperadas).
5. No deja TODO criticos en flujo principal.

## 7. Riesgos Actuales y Mitigacion

### Riesgo A - Deriva entre documentacion y codigo

Mitigacion:

- Checklist de doc obligatorio por PR.
- Bloquear cierre de sprint si docs estan desalineadas.

### Riesgo B - Regresiones por cambios mobile

Mitigacion:

- Smoke funcional en mobile viewport por ruta critica.
- Casos de iOS drawer/scroll y HTTP local en suite de regresion.

### Riesgo C - Deuda en circuitos no implementados (B2/B5)

Mitigacion:

- Backlog priorizado por impacto en operacion real.
- Entregas incrementales por subflujo funcional.

## 8. KPIs de Seguimiento V2

- Tasa de exito EP1-EP4-EP6-EP7-EP5.
- Tiempo medio de ciclo login -> cierre de lote.
- Incidencias por sesion/no-auth por turno.
- Defectos criticos por sprint.
- Cobertura de smoke sobre endpoints productivos.

## 9. Primer Bloque a Ejecutar en este Plan

Bloque elegido: **Bloque 1 - Nucleo Operativo y Confiabilidad**.

Razon:

1. Maximiza estabilidad inmediata sobre lo ya en produccion interna.
2. Reduce riesgo antes de abrir frentes comerciales/logisticos complejos.
3. Cierra hueco funcional EP5 y mejora capacidad de release.

## 10. Enlaces a Sprints del Bloque 1

- `docs/plan-v2/sprints/bloque-1-nucleo-operativo/SPRINT-01_EP5_Y_CONTRATOS.md`
- `docs/plan-v2/sprints/bloque-1-nucleo-operativo/SPRINT-02_HARDENING_Y_SMOKE.md`
- `docs/plan-v2/sprints/bloque-1-nucleo-operativo/SPRINT-03_RELEASE_READINESS.md`

## 11. Enlaces a Sprints del Bloque 2

- `docs/plan-v2/sprints/bloque-2-inventario/SPRINT-04_RECEPCION.md`
- `docs/plan-v2/sprints/bloque-2-inventario/SPRINT-05_CUARENTENA_Y_ETIQUETADO.md`
- `docs/plan-v2/sprints/bloque-2-inventario/SPRINT-06_INVENTARIO_CIEGO.md`
