# Checklist de Release — Bloque 1

Fecha: ____-__-__
Version candidata: ____
Responsable tecnico: ____
Entorno objetivo: ____

## 1. Validaciones previas obligatorias

- [ ] Codigo backend sincronizado en entorno objetivo.
- [ ] Reinicio coordinado de contenedores `backend-1` y `frontend-1`.
- [ ] Variables de entorno verificadas para el entorno.

## 2. Build y calidad tecnica

- [ ] `npm run build` ejecutado en `kiosco-pwa/` sin errores.
- [ ] Smoke suite base ejecutada:
  - [ ] EP1 `login_operario`.
  - [ ] EP1b `get_operario_session`.
  - [ ] EP2 `get_tareas`.
  - [ ] EP3 `validar_material`.
  - [ ] EP5 `info_lote`.
  - [ ] EP6 `get_lotes_cuarentena`.
- [ ] Exit code de smoke = `0`.

## 3. Validaciones opcionales por alcance

Marcar solo si el release toca estos flujos:

- [ ] EP4 (write-op) validado con `-IncludeWriteOps`.
- [ ] EP7 (write-op calidad) validado con `-IncludeQualityWriteOps`.

## 4. Criterios de salida Bloque 1

- [ ] EP1-EP7 + EP5 estables en pruebas del entorno.
- [ ] Incidencias criticas abiertas = 0.
- [ ] Documentacion sincronizada (`API.md`, `FRONTEND.md`, `RUNBOOK.md`, `CHANGELOG.md`).

## 5. Evidencia tecnica

### Build frontend

Comando:

```powershell
cd kiosco-pwa
npm run build
cd ..
```

Resultado:

```text
[pegar salida resumida]
```

### Smoke suite

Comando:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke/smoke-kiosco.ps1
```

Resultado:

```text
[pegar salida resumida PASS/FAIL]
```

### Observaciones y riesgos conocidos

```text
[registrar riesgos remanentes y mitigacion]
```

## 6. Decision de liberacion

- [ ] Aprobado para liberar.
- [ ] Rechazado (requiere correcciones).

Motivo:

```text
[justificacion tecnica]
```
