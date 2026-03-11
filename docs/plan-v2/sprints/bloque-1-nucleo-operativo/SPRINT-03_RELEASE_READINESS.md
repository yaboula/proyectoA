# Sprint 03 - Release Readiness Operativo

Bloque: 1 - Nucleo Operativo y Confiabilidad
Duracion sugerida: 1 semana
Objetivo del sprint: cerrar un paquete de release estable para el nucleo operativo con controles previos y evidencia tecnica.

Estado: En ejecucion

## 1. Alcance

### In Scope

1. Checklist de release por entorno.
2. Evidencias de build + smoke + validacion funcional minima.
3. Limpieza de deuda menor detectada en sprint 01-02.
4. Criterio de salida del Bloque 1.

### Out of Scope

1. Nuevas features fuera del nucleo operativo.
2. Inicio de implementacion Bloque 2/5.

## 2. Historias Tecnicas

### H1 - Checklist release estandar

Como equipo dev,
quiero una lista unica de validacion antes de despliegue
para reducir errores humanos.

Criterios de aceptacion:

1. Checklist unificada en RUNBOOK.
2. Pasos concretos backend/frontend/datos.
3. Evidencia de cada paso en release notes.

### H2 - Cierre de bloque con KPI minimo

Como lider tecnico,
quiero confirmar salida del Bloque 1 con metricas basicas
para abrir Bloque 2 con riesgo controlado.

Criterios de aceptacion:

1. Endpoints core estables en smoke recurrente.
2. Incidencias criticas abiertas = 0.
3. Documentacion sincronizada.

## 3. Tareas Tecnicas

## Control de release

1. Definir plantilla de release notes tecnica:
   - cambios funcionales
   - cambios no funcionales
   - riesgos conocidos
   - rollback plan
2. Formalizar comandos obligatorios pre-release:
   - `npm run build`
   - smoke suite
   - verificacion de sesiones/roles

## Calidad documental

1. Revisar coherencia entre:
   - `docs/API.md`
   - `docs/FRONTEND.md`
   - `docs/RUNBOOK.md`
   - `CHANGELOG.md`
2. Eliminar ambiguedades de estado pendiente vs hecho.

## Cierre de deuda menor

1. Resolver inconsistencias menores de versionado visible.
2. Confirmar textos y mensajes funcionales FR en rutas criticas.

## 4. Definicion de Terminado del Sprint

1. Release checklist ejecutada de punta a punta.
2. Evidencias archivadas en docs.
3. Bloque 1 marcado como cerrado para pasar a Bloque 2.

## 5. Criterio de Salida del Bloque 1

Se puede iniciar Bloque 2 si y solo si:

1. EP1-EP7 + EP5 smoke verde.
2. No hay bug critico abierto en produccion/laboratorio.
3. Build frontend estable.
4. Documentacion core sin desalineacion.

## 6. Riesgos del Sprint

- Cierre apresurado sin evidencia completa.
- Deuda documental por cambios de ultimo minuto.

Mitigacion:

- Congelar scope 48h antes de release.
- Aplicar regla: sin evidencia, no se marca como completado.

## 7. Entregables

1. Paquete de release readiness del Bloque 1.
2. Acta de cierre de bloque (resumen tecnico).
3. Backlog refinado para inicio de Bloque 2.

## 8. Avance implementado (2026-03-11)

1. Plantilla de checklist y evidencia creada en `docs/releases/BLOQUE1_RELEASE_CHECKLIST.md`.
2. Plantilla de acta de cierre creada en `docs/releases/BLOQUE1_ACTA_CIERRE.md`.
3. `docs/RUNBOOK.md` actualizado con flujo operativo de pre-release y cierre de bloque.
