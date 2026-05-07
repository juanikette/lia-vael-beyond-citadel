# LegendaryExplorer Reference Map

Este archivo registra que componentes de LegendaryExplorer usamos como baseline tecnico.

Repositorio:
- https://github.com/ME3Tweaks/LegendaryExplorer/

## Fase 0

- Objetivo: definir practica de consulta y trazabilidad por fase.
- Estado: inicializado.

### Areas a consultar en fases siguientes

- Lectura de package PCC (header, names, imports, exports).
- Estructuras de conversacion (`BioConversation`, properties relevantes).
- Lectura TLK y logica de prioridad/override con DLC.

### Regla de registro

Al cerrar cada fase, agregar aqui:
- archivo/clase de LEX consultada,
- decision tomada en toolkit,
- diferencia relevante OT vs LE detectada (si aplica).

## Fase 1

- Archivo/clase LEX consultada: `LegendaryExplorerCore/Packages/MEPackage.cs`.
- Decision toolkit: mantener parseo defensivo minimo para header y tablas base, sin lazy-load ni soporte de compresion en esta fase.
- Diferencia OT vs LE detectada: formato de header comparte offsets base para names/imports/exports; las variaciones de plataforma/compresion se posponen para fases siguientes.

## Fase 2

- Archivo/clase LEX consultada: `LegendaryExplorerCore/Packages/MEPackage.cs` y `LegendaryExplorerCore/Packages/ImportEntry.cs`.
- Decision toolkit: detectar `BioConversation` resolviendo el `class_index` de export hacia import y mapeando `object_name`/`class_name` con la name table.
- Diferencia OT vs LE detectada: para la deteccion por clase, la logica de indices import/export aplicada en Fase 2 se mantiene estable en los perfiles validados (ME2 OT y LE2).
