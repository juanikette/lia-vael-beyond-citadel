# pcc-dialog-toolkit

MVP para extraer conversaciones `BioConversation` desde archivos `.pcc` (Mass Effect OT/LE).

## Estructura del codigo

- Codigo fuente directo en `src/` (sin subpaquete `src/pcc_dialog_toolkit/`).
- Modulos principales:
  - `src/cli.py`
  - `src/pcc/`
  - `src/dialogue/`
  - `src/tlk/`
  - `src/serialize/`
  - `src/model/`

## Que hace la herramienta

- Lee paquetes `.pcc` de Mass Effect y detecta exports `BioConversation`.
- Extrae stubs de dialogo (`entries`, `replies`, `speakers`) en JSON.
- Puede resolver `StrRef` contra TLK base y overrides de DLC.
- Genera salida JSON versionada con resumen de warnings/errores.
- Permite validacion estricta para usar la CLI como gate automatizable.

## Alcance y limites

- Soporta perfiles OT/LE orientados a conversaciones `BioConversation`.
- Para PCC OT comprimidos (LZO) requiere dependencia `lzallright`.
- Si una conversacion falla, el flujo resiliente continua y reporta error por item.
- Si el perfil o schema no coincide, marca `needs_schema_review`.

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
pcc_dialog_extract path/al/archivo.pcc --game me2 --tlk ".../BIOGame_INT.tlk" --dlc-dir ".../BioGame/DLC" --output output.json --pretty
```

Para desarrollo local sin instalar script, desde `tools/pcc-dialog-toolkit/`:

```bash
PYTHONPATH=src python -m cli --help
PYTHONPATH=src python -m cli --version
```

Cuando se usa `--dump-bioconversation-stub` junto con `--tlk`, el CLI resuelve `line_text` para `EntryNode` y `ReplyNode`.
Si se agrega `--dlc-dir`, los TLKs de DLC se cargan por prioridad (`MountPriority`) y pueden sobreescribir strings del TLK base.
Por defecto, el resolver ignora TLKs de prueba (`*_Test_INT.tlk`) para priorizar contenido runtime real.

Cuando se usa `--output`, el CLI escribe JSON final versionado (`schema_version`) e incluye:

- `conversations` parseadas correctamente.
- `errors` por conversacion fallida (sin abortar todo el archivo).
- `summary` con conteos agregados y total de warnings.

El CLI valida un contrato minimo de salida antes de escribir archivo (campos top-level requeridos y consistencia de conteos en `summary`).
Si hay warnings o errores por conversacion, tambien los imprime en consola para trazabilidad inmediata.

`--validate-bioconversation-stubs` marca `needs_schema_review=true` cuando el perfil es desconocido o el parseo sugiere desajuste de esquema.

## Salida JSON (resumen)

La salida `--output` incluye:

- `schema_version`
- `tool_version`
- `input`
- `summary`
- `conversations`
- `errors`
