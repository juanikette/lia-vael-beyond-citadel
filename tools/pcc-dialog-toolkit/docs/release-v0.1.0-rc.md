# pcc-dialog-toolkit v0.1.0-rc (scope OT)

Fecha: 2026-05-08

Estado del release: candidato aprobado para ME2 OT.

## Resumen

- Se consolida un pipeline MVP estable para extraccion de `BioConversation` con salida JSON versionada (`schema_version=0.1`).
- Se valida flujo de resolucion TLK base + overrides DLC en muestras reales OT.
- Se documenta QA Fase 6 con cierre parcial: OT validado, LE2 pendiente por entorno.

## Alcance incluido

- Lectura package PCC y deteccion de exports `BioConversation`.
- Parse de estructuras de conversacion a AST normalizado.
- Resolucion de `StrRef` mediante TLK base y TLKs de DLC con prioridad por `MountPriority`.
- Serializer JSON final con contrato validado:
  - `conversations` correctas
  - `errors` por conversacion fallida (sin abortar el archivo)
  - `summary` agregado (`ok/failed/warnings`)

## Evidencia de validacion

- QA OT ampliado:
  - `files=25`
  - `files_with_conversations=11`
  - `conversations_total=11`
  - `conversations_ok=11`
  - `conversations_failed=0`
  - `warnings_total=0`
  - `nonzero_returncodes=0`
- Contraste manual LEX OT:
  - `cases=3`
  - `OK=3`
  - `Mismatch=0`
  - `N/A=0`

## Limitaciones conocidas

- Cobertura LE2 no ejecutada en este ciclo por ausencia de instalacion local de Legendary Edition.
- Cierre total OT/LE queda pendiente de re-ejecucion del runbook en entorno LE2.

## Artefactos

- Reporte OT ampliado:
  - `tools/pcc-dialog-toolkit/output/phase6-ot-expanded/phase6-ot-expanded-report.json`
- Lineas de control para contraste LEX:
  - `tools/pcc-dialog-toolkit/output/phase6-ot-expanded/phase6-ot-lex-control-lines.json`
- Runbook operativo de QA:
  - `tools/pcc-dialog-toolkit/docs/phase6-qa-runbook.md`

## Decision

- Se congela baseline como `v0.1.0-rc` con alcance OT.
- Siguiente hito: completar validacion LE2 y promover a cierre completo de Fase 6.
