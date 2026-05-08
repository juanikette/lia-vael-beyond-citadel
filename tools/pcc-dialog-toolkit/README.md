# pcc-dialog-toolkit

MVP para extraer conversaciones `BioConversation` desde archivos `.pcc` (Mass Effect OT/LE).

## Estado actual

- Fase 3 en progreso: bootstrap de parseo de propiedades clave (`EntryList`, `ReplyList`, `SpeakerList`).

## Uso (actual)

```bash
pcc_dialog_extract path/al/archivo.pcc --list-bioconversations
pcc_dialog_extract path/al/archivo.pcc --inspect-bioconversation-properties
pcc_dialog_extract path/al/archivo.pcc --dump-bioconversation-stub --pretty
pcc_dialog_extract path/al/archivo.pcc --dump-bioconversation-row-payloads --pretty
pcc_dialog_extract path/al/archivo.pcc --validate-bioconversation-stubs --pretty
pcc_dialog_extract path/al/archivo.pcc --validate-bioconversation-stubs --strict-validation
pcc_dialog_extract path/al/archivo.pcc --phase3-report reports/phase3-sample.json --pretty
pcc_dialog_extract --phase3-batch-dir samples/me2_ot --phase3-batch-glob "*.pcc" --phase3-batch-report reports/phase3-batch-me2ot.json --pretty
```

`--validate-bioconversation-stubs` marca `needs_schema_review=true` cuando el perfil es desconocido o el parseo sugiere desajuste de esquema.

Flujo sugerido de cierre Fase 3 con muestras reales:

1. Generar reporte por muestra con `--phase3-report`.
2. Revisar `summary.needs_schema_review` y `validation_items`.
3. Repetir con `--validate-bioconversation-stubs --strict-validation` para usar exit code como gate.
4. Para varias muestras, usar `--phase3-batch-report` y revisar el `summary` agregado.
