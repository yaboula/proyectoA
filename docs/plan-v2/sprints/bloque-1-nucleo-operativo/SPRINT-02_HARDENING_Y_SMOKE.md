# Sprint 02 - Hardening y Smoke Automatizado

Bloque: 1 - Nucleo Operativo y Confiabilidad
Duracion sugerida: 1 semana
Objetivo del sprint: mejorar robustez de errores/sesion y montar smoke suite reproducible para endpoints criticos.

## 1. Alcance

### In Scope

1. Hardening de manejo de errores en endpoints operativos.
2. Consolidacion de mensajes funcionales FR en respuestas de usuario.
3. Suite smoke para EP1, EP2, EP3, EP4, EP5, EP6, EP7.
4. Script de ejecucion rapida para validacion pre-release.

### Out of Scope

1. Nuevas features funcionales de Bloques 2 o 5.
2. Refactor estructural mayor de arquitectura frontend.

## 2. Historias Tecnicas

### H1 - Contratos de error consistentes

Como developer,
quiero estandarizar errores API
para simplificar debugging y evitar ambiguedad en frontend.

Criterios de aceptacion:

1. `error_code` coherente en endpoints criticos.
2. `message_fr` presente en errores funcionales.
3. Status HTTP alineado a tipo de fallo.

### H2 - Smoke suite funcional

Como developer,
quiero ejecutar una bateria corta de endpoints
para validar release minima sin recorrer toda la app manualmente.

Criterios de aceptacion:

1. Script smoke documentado y ejecutable localmente.
2. Cobertura de casos happy path + fallos controlados.
3. Resultado de smoke visible en salida resumida.

## 3. Tareas Tecnicas

## Backend

1. Revisar endpoints para consistencia de codigos/error payload.
2. Homogeneizar claves de respuesta y mensajes operarios.
3. Revisar `try/except` para evitar traces al usuario final.

## QA Tecnico

1. Definir casos smoke por endpoint:
   - EP1 login valido/invalido
   - EP2 sin company / con company valida
   - EP3 material correcto / mismatch / lote invalido
   - EP4 consumo estandar
   - EP5 lote valido/inexistente
   - EP6 listado cuarentena
   - EP7 rechazo/aprobacion
2. Implementar script de smoke (bash/ps1 o python) reutilizable.
3. Documentar prerequisitos de datos de prueba.

## Frontend

1. Verificar que errores de API se renderizan sin romper navegacion.
2. Validar guard de sesion en rutas protegidas.

## 4. Definicion de Terminado del Sprint

1. Smoke suite ejecuta todos los casos definidos.
2. Se detectan fallos con salida entendible para developers.
3. No hay regresiones funcionales en flujos principales.
4. RUNBOOK actualizado con comando y lectura de resultados.

## 5. Pruebas

### Gate minimo

1. `npm run build` en frontend.
2. Smoke script en verde en entorno preparado.
3. Verificacion manual rapida en LoginQR + Tareas + Laboratoire.

## 6. Riesgos del Sprint

- Fragilidad de datos demo entre ejecuciones.
- Dependencia de estado de contenedores.

Mitigacion:

- Estandarizar precondicion con `test_data.run`.
- Incluir chequeo de disponibilidad de backend antes de lanzar smoke.

## 7. Entregables

1. Ajustes de hardening en endpoints.
2. Script smoke + guia de uso.
3. Runbook actualizado.
