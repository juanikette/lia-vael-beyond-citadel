# Plan de implementacion - toolkit de dialogos Mass Effect (OT/LE)

## Nombre de herramienta

Nombre seleccionado: **pcc-dialog-toolkit**

## Fuente de conocimiento externa (obligatoria)

Repositorio de referencia para procesos y validacion tecnica:

- https://github.com/ME3Tweaks/LegendaryExplorer/

Regla de uso durante implementacion:

- Consultar LegendaryExplorer antes de cerrar cada fase que toque parseo de PCC/TLK.
- Priorizar nomenclatura, orden de lectura y comportamiento observables en herramientas maduras.
- No copiar codigo de forma ciega: usarlo como guia de formato, casos borde y verificacion.
- Registrar en notas de fase que archivos/clases de LegendaryExplorer se usaron como referencia.

## Objetivo MVP

Implementar un CLI llamado `pcc_dialog_extract` que:

1. Lea un archivo `.pcc` de ME OT/LE.
2. Detecte exports `BioConversation`.
3. Extraiga nodos, replies, speakers y `StrRef`.
4. Resuelva texto via TLK (`BIOGame_INT.tlk` + DLC TLKs).
5. Exporte resultado en `output.json`.

## Alcance y limites

### Incluye
- Parse parcial de formato package (names/imports/exports/properties relevantes).
- Parse de estructuras necesarias para conversaciones.
- Resolucion de `StrRef -> text`.
- Salida JSON estable y versionada.

### No incluye (MVP)
- Render, mallas, texturas, shaders.
- Edicion visual.
- FaceFX/Wwise avanzados.
- Reinyeccion binaria completa (se disena en fase posterior).

## Stack recomendado

- **MVP**: Python 3.11+
- `typer` o `argparse` para CLI
- `pydantic` (opcional) para validar AST/salida JSON
- Tests con `pytest`

Razon: velocidad de iteracion alta para validar formato de datos y flujo completo.

## Arquitectura propuesta

```text
input.pcc
  -> pcc_reader
  -> export_scanner (BioConversation)
  -> conversation_parser
  -> tlk_resolver
  -> serializer_json
  -> output.json
```

Modulos sugeridos:

- `src/cli.py`
- `src/pcc/reader.py`
- `src/pcc/tables.py`
- `src/pcc/properties.py`
- `src/dialogue/conversation_parser.py`
- `src/tlk/reader.py`
- `src/tlk/resolver.py`
- `src/model/ast.py`
- `src/serialize/json_writer.py`

## Modelo AST v0.1

### Conversation
- `id`: string (object name)
- `export_index`: int
- `package_path`: string
- `entries`: `EntryNode[]`
- `replies`: `ReplyNode[]`
- `speakers`: `Speaker[]`

### EntryNode
- `id`: int
- `speaker_id`: int|null
- `speaker_tag`: string|null
- `listener_tag`: string|null
- `line_strref`: int|null
- `line_text`: string|null
- `reply_links`: int[]

### ReplyNode
- `id`: int
- `line_strref`: int|null
- `line_text`: string|null
- `target_entry_id`: int|null
- `condition_refs`: string[]

### Speaker
- `id`: int
- `tag`: string|null
- `display_name`: string|null

## CLI objetivo (fase 1)

```bash
pcc_dialog_extract input.pcc \
  --game me2 \
  --tlk ".../BIOGame_INT.tlk" \
  --dlc-dir ".../BioGame/DLC" \
  -o output.json
```

Flags minimas:
- `--game`: `me1|me2|me3|le1|le2|le3`
- `--tlk`: ruta TLK base
- `--dlc-dir`: carpeta DLC (opcional)
- `-o, --output`: archivo JSON de salida
- `--pretty`: JSON legible

## Plan por fases

### Fase 0 - Preparacion del repo
- Crear estructura de carpetas.
- Definir formato de salida JSON v0.1.
- Agregar casos de prueba con 1-2 PCC reales conocidos.

### Fase 1 - Lectura package basica
- Implementar lector de header + tablas names/imports/exports.
- Exponer API para iterar exports por clase/nombre.
- Verificar lectura de varios PCC OT/LE.

### Fase 2 - Deteccion BioConversation
- Identificar exports con clase `BioConversation`.
- Dump de metadata minima (nombre, indice, clase, offset, size).

### Fase 3 - Parse de conversacion
- Parsear propiedades y listas clave (EntryList/ReplyList/SpeakerList).
- Resolver links entre nodos.
- Construir AST normalizado.

### Fase 4 - TLK resolver
- Implementar lector TLK base.
- Resolver `StrRef` de AST.
- Cargar TLKs DLC y aplicar prioridad/override.

### Fase 5 - Serializer y CLI estable
- Exportar JSON final con esquema versionado.
- Manejo de errores por conversacion (no abortar todo el archivo).
- Logs de warnings para campos no parseados.

### Fase 6 - QA del MVP
- Validar salida con muestras de ME2 OT y LE2.
- Comparar lineas puntuales contra resultado en juego/LEX.
- Congelar `v0.1.0` del extractor.

## Criterios de aceptacion MVP

- Dado un `.pcc` valido con `BioConversation`, genera `output.json` sin crash.
- Incluye nodos, replies, speakers, `StrRef` y texto resuelto (si existe).
- Si una conversacion falla, se reporta y continua con las demas.
- Soporta al menos ME2 OT en una muestra real de Citadel.

## Riesgos y mitigaciones

- Variaciones OT vs LE en serializacion:
  - Mitigar con capa `game profile` por version.
- Estructuras incompletas/no estandar:
  - Mitigar con parse defensivo + warnings.
- TLK DLC con overrides:
  - Mitigar aplicando orden de carga configurable.

## Siguiente paso inmediato

1. Inicializar esqueleto Python y CLI minima.
2. Implementar `pcc_reader` (header + names + exports).
3. Entregar comando que liste `BioConversation` por archivo como primer hito verificable.
