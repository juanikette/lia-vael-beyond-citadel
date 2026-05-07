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
```

`--validate-bioconversation-stubs` marca `needs_schema_review=true` cuando el perfil es desconocido o el parseo sugiere desajuste de esquema.
