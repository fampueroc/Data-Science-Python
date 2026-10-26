# Referencias manuales (muestra de evaluación)

Muestra fija, elegida **antes** de calcular cualquier métrica:

| Modalidad | Casos | Quién transcribe |
|---|---|---|
| Documentos | `doc_002`, `doc_003`, `doc_007` (impresos) · `doc_009`, `doc_010`, `doc_011`, `doc_015` (fotos) · `doc_018`, `doc_019`, `doc_020` (manuscritos) | Estudiante, mirando la imagen en `datos/raw/documentos/` |
| Audio (entrevistas) | `clip_006`, `clip_007`, `clip_010`, `clip_016`, `clip_017` | Estudiante, escuchando el audio en `datos/raw/audio/` |
| Audio (lectura) | `clip_020`, `clip_022`, `clip_024`, `clip_026`, `clip_028` | Transcripción humana oficial de OpenSLR 73 (no está en esta carpeta: se lee de `datos/raw/audio/openslr73.csv`) |

## Reglas de transcripción

1. Escribir **todo el texto legible / todo lo hablado**, en orden de lectura (izquierda a derecha, arriba a abajo).
2. **No mirar la salida del OCR ni del ASR** antes de terminar (para no sesgar la referencia).
3. Documentos: copiar tal como está escrito (mayúsculas, tildes y ortografía antigua incluidas). Un salto de línea puede ser un espacio. Si una palabra es ilegible, escribir `[ilegible]`.
4. Audio: escribir las palabras como se pronuncian, sin marcas de hablante. Muletillas que sí se oyen (`eh`, `este`) se escriben. Nombres propios de personas: escribirlos igual (luego se seudonimizan con el mismo diccionario en la referencia y en la hipótesis).
5. Guardar cada archivo en UTF-8 (VS Code lo hace por defecto).

La normalización para CER/WER (minúsculas, sin puntuación, sin `[HABLANTE_n]`) se aplica después, igual a referencia y a hipótesis.
