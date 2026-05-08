# Fase 3 - Playbook de cierre con muestras reales

Este playbook define una corrida minima para decidir si Fase 3 puede pasar a `Done`.

## 1) Preparar muestras locales

Ubicar 1+ archivos por perfil objetivo:

- ME2 OT (ej. `samples/me2_ot/*.pcc`)
- LE2 (ej. `samples/le2/*.pcc`)

Si los binarios no se versionan, mantenerlos solo en entorno local.

## 2) Generar reportes batch por perfil

```bash
pcc_dialog_extract --phase3-batch-dir samples/me2_ot --phase3-batch-glob "*.pcc" --phase3-batch-report reports/phase3-batch-me2ot.json --pretty
pcc_dialog_extract --phase3-batch-dir samples/le2 --phase3-batch-glob "*.pcc" --phase3-batch-report reports/phase3-batch-le2.json --pretty
```

## 3) Gate estricto por archivo

Para cualquier archivo con dudas:

```bash
pcc_dialog_extract "<ruta>.pcc" --validate-bioconversation-stubs --strict-validation
```

- Exit code `0`: sin bloqueantes de validacion.
- Exit code `3`: hay `invalid` o `needs_schema_review`.

## 4) Criterio minimo de cierre Fase 3

- `summary.invalid == 0` en muestras objetivo.
- `summary.needs_schema_review == 0` o residual pequeno con plan de mitigacion documentado.
- Sin warnings criticos sin explicar.
- Verificacion registrada en Notion (`Comandos`, `Resultados`, `Riesgos remanentes`).

## 5) Si falla el gate

- Revisar `validation_items` y `row_payloads` del reporte.
- Ajustar schema por perfil (`dialogue/schema.py`) o parser de listas.
- Repetir corrida hasta estabilizar.
