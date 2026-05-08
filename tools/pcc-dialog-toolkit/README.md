# pcc-dialog-toolkit

MVP para extraer conversaciones `BioConversation` desde archivos `.pcc` (Mass Effect OT/LE).

## Estado actual

- Fase 3 cerrada: parse semantico de `BioConversation` validado en corpus ME2 OT LOC.
- Fase 4 en progreso: resolucion `StrRef` desde TLK base con soporte de overrides DLC.
- Soporte ME2 OT comprimido (LZO) requiere `lzallright`.

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
pcc_dialog_extract path/al/archivo.pcc --dump-bioconversation-stub --tlk ".../BIOGame_INT.tlk" --dlc-dir ".../BioGame/DLC" --pretty
```

Cuando se usa `--dump-bioconversation-stub` junto con `--tlk`, el CLI resuelve `line_text` para `EntryNode` y `ReplyNode`.
Si se agrega `--dlc-dir`, los TLKs de DLC se cargan por prioridad (`MountPriority`) y pueden sobreescribir strings del TLK base.
Por defecto, el resolver ignora TLKs de prueba (`*_Test_INT.tlk`) para priorizar contenido runtime real.

`--validate-bioconversation-stubs` marca `needs_schema_review=true` cuando el perfil es desconocido o el parseo sugiere desajuste de esquema.

Flujo sugerido de cierre Fase 3 con muestras reales:

1. Generar reporte por muestra con `--phase3-report`.
2. Revisar `summary.needs_schema_review` y `validation_items`.
3. Repetir con `--validate-bioconversation-stubs --strict-validation` para usar exit code como gate.
4. Para varias muestras, usar `--phase3-batch-report` y revisar el `summary` agregado.

Guia operativa detallada: `docs/phase3-closure-playbook.md`.
