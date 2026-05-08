# Fase 6 - QA con muestras OT/LE y validacion contra LEX

Objetivo: validar el MVP (`schema_version=0.1`) con evidencia reproducible en ME2 OT y LE2, contrastando resultados puntuales con baseline de LegendaryExplorer (LEX).

## Plan operativo

1. Preparar corpus fijo de muestras por perfil (`OT` y `LE2`).
2. Ejecutar extraccion JSON versionada por muestra con TLK base + DLC.
3. Consolidar metricas de salud (`ok/failed/warnings`) por corrida.
4. Verificar lineas puntuales (`StrRef`, `line_text`, links, speaker tags) contra LEX.
5. Registrar incidencias no bloqueantes y decidir congelamiento `v0.1.0`.

## Prerrequisitos

- `python` con entorno del toolkit activo.
- `lzallright` instalado para PCC OT comprimidos.
- Rutas locales validas a:
  - ME2 OT (`BioGame/CookedPC`, `BIOGame_INT.tlk`, `BioGame/DLC`)
  - LE2 (`Game/ME2/BioGame/CookedPCConsole`, `BIOGame_INT.tlk`, `DLC`)

## Muestras sugeridas

Usar al menos 3 PCC por perfil. Si hay disponibilidad, preferir 5 para mayor cobertura.

- OT recomendadas:
  - `BioD_CitHub_LOC_INT.pcc`
  - `BioD_CitHub_300Dialogue_LOC_INT.pcc`
  - `BioD_CitHub_230Baily_LOC_INT.pcc`
  - `BioD_CitAsL_LOC_INT.pcc`
  - `BioD_CitGrL_300MeetTheMole_LOC_INT.pcc`
- LE2 recomendadas:
  - espejo de nombres si existen en `CookedPCConsole`
  - si no existen, seleccionar 3-5 `BioD_*LOC_INT.pcc` con `BioConversation`

## Comando base por muestra

```bash
pcc_dialog_extract <ruta_pcc> --game <me2|le2> --tlk "<ruta_BIOGame_INT.tlk>" --dlc-dir "<ruta_DLC>" --output "<salida_json>" --pretty
```

## Evidencia minima por muestra

- `summary.conversations_total`, `summary.conversations_failed`, `summary.warnings_total`.
- 3-5 lineas de control con:
  - `conversation_id`
  - `entry_id` o `reply_id`
  - `line_strref`
  - `line_text`
- Estado de parseo resiliente:
  - `errors[]` vacio o listado de fallas con `export_index`.

## Checklist de validacion contra LEX

Para cada linea de control:

1. Abrir la conversacion equivalente en LEX.
2. Confirmar que `StrRef` coincide.
3. Confirmar que el texto resuelto (`line_text`) coincide con LEX/TLK efectivo.
4. Confirmar coherencia de links (`reply_links`, `target_entry_id`) y speaker tags.
5. Registrar `OK` o `Mismatch` con detalle.

## Criterio de paso Fase 6

- OT: corpus objetivo ejecuta sin crashes y sin fallos criticos.
- LE2: corpus objetivo ejecuta sin crashes y sin fallos criticos.
- Validacion puntual contra LEX completa en ambos perfiles.
- Incidencias restantes clasificadas como no bloqueantes para `v0.1.0`.

## Contingencia si no hay instalacion LE2 local

Si no existe una instalacion local de LE2, aplicar cierre parcial controlado:

- Ejecutar QA OT ampliado (>=25 muestras `BioD_*LOC_INT.pcc`) para subir confianza del pipeline.
- Mantener comparacion puntual contra LEX para las lineas de control OT.
- Marcar validacion LE2 como `pendiente por entorno` en Notion.
- No cerrar la cobertura OT/LE como completa; registrar `v0.1.0-rc` (OT validado, LE2 diferido).

## Salidas recomendadas

- JSON por muestra en `tools/pcc-dialog-toolkit/output/phase6-<perfil>/`.
- Reporte consolidado por perfil (`phase6-ot-report.json`, `phase6-le2-report.json`).
- Nota de cierre en Notion (`Fase 6 - QA del MVP`).
