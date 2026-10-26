# Tarea 2 · Voces y documentos peruanos: del archivo escaneado al texto buscable

**Estudiante:** @fampueroc · **Curso:** Data Science con Python 2026 · **Fecha de extracción y evaluación:** 25 de octubre de 2026
**Dashboard público:** https://voces-peruanas-fampueroc.streamlit.app/

## Pregunta

> ¿Pueden convertir documentos escaneados y entrevistas en audio en un archivo de texto estructurado y buscable?

**Respuesta corta: sí para impresos limpios y para entrevistas en español; todavía no para manuscritos.** Con modelos abiertos que
corren gratis en una laptop sin GPU se procesaron 25 documentos y 44.7 minutos de audio reales: el texto queda buscable
y un LLM local extrae campos en JSON, pero los manuscritos y los carteles pintados a mano siguen necesitando revisión humana.

## Resultados (muestra fija de 10 documentos y 10 clips, referencias manuales)

| Modalidad | Modelo | Error | Latencia |
|---|---|---|---|
| documentos | PaddleOCR 3.7 PP-OCRv6 (línea base) | CER 0.580 | 53.9 s/página |
| documentos | Tesseract 5.4 spa | CER 0.688 | 0.4 s/página |
| audio | faster-whisper small (línea base) | WER 0.218 | RTF 0.24 |
| audio | faster-whisper large-v3-turbo | WER 0.208 | RTF 0.50 |
| audio | Meta MMS-1b-all spa | WER 0.313 | RTF 0.39 |

**Acuerdo LLM vs. auditoría humana:** **15/20 (75 %)**: 10/10 en audio y 5/10 en documentos extracciones completamente correctas (Qwen2.5-1.5B-Instruct local).

## Corpus, fuentes y licencias

| Corpus | Contenido | Fuente | Licencia |
|---|---|---|---|
| Documentos | 25 imágenes: 8 impresos (resolución municipal, billetes de intis, *Mercurio Peruano* 1791, *El Comercio* 1839 y 1945, Constitución de 1823, carta mecanografiada a Ricardo Palma), 8 fotos (placas, letreros, pizarra de menú) y 9 manuscritos (Acta de la Independencia 1821, tarjeta y cartas a Ricardo Palma, recibo de 1895, partida de bautismo de 1897, cuatro páginas de Guamán Poma) | Wikimedia Commons | Dominio público, CC0, CC BY 3.0/4.0, CC BY-SA 3.0/4.0 |
| Audio | 19 entrevistas reales en español peruano (calle, marchas, conferencias de prensa, testimonios) y 2 en quechua de Huaylas | Wikimedia Commons (Wikimedia Perú, estudiantes UNMSM, *Voces y plantas*, *Semillas de Conocimiento*) | CC BY-SA 4.0, CC BY 4.0 |
| Audio | 10 frases leídas en español peruano con transcripción humana oficial | OpenSLR 73 (Google) | CC BY-SA 4.0 |

Fecha de extracción: 25 de octubre de 2026. La licencia, el autor y la URL de cada archivo están en `datos/fuentes.csv`
(leídos de la API de Commons, no escritos a mano). `corpus.py` vuelve a descargar todo el corpus a `datos/raw/`, que no se versiona.

## Pipeline

1. **`corpus.py`**: descarga con User-Agent descriptivo, 1,5 s entre solicitudes y reintentos ante *429 Too Many Requests*.
2. **`01_extraccion.ipynb`**: PaddleOCR 3.7 (PP-OCRv6) → faster-whisper `large-v3-turbo` con VAD + diarización por huellas de voz
   (WeSpeaker) → Meta MMS `qwh` para quechua → seudonimización (`voz.seudonimizar`) → hash SHA-256 de archivos → EDA con Plotly → CSV.
3. **`02_evaluacion.ipynb`**: referencias manuales → CER/WER de línea base → Tesseract, Whisper turbo y MMS en las mismas muestras →
   LLM local para JSON con verificación anti-invención → auditoría humana de 20 casos → tabla comparativa.
4. **`app.py`**: dashboard en Streamlit que solo lee CSV (no carga modelos).

Seudonimización: 41 menciones de nombres de personas privadas (6 en documentos y 35 en audio) reemplazadas por `[PERSONA_n]`, `[ENTREVISTADOR_n]` o `[AUTORIDAD_n]`.
El diccionario de reemplazos es privado (`datos/raw/seudonimos.json`, fuera de Git). Los personajes históricos se mantienen.

## Hallazgos

1. **La dificultad del documento importa más que el modelo.** PaddleOCR obtiene CER 0.45 en impresos, 0.78 en fotos y 0.97 en manuscritos; una placa grabada sale casi perfecta (0,05) y un cartel pintado a mano no se lee en absoluto. Frente a Tesseract (CER 0,69), PaddleOCR gana sobre todo en impresos (0,45 frente a 0,81). Y ese ruido se propaga: el LLM acertó 10/10 fichas de audio pero solo 5/10 de documentos, porque sobre texto OCR ruidoso inventa temas o confunde emisor y destinatario.
2. **El ASR funciona en la calle, pero el contexto acústico manda.** Con las mismas tres configuraciones, las frases leídas de OpenSLR tienen WER ≈ 0,06 y las entrevistas en la calle ≈ 0,26; el estadio llega a 0,49–0,88. `large-v3-turbo` (0,21) no mejora de verdad a `small` (0,22) y cuesta el doble de cómputo, por eso se elige `small` en CPU. En quechua de Huaylas Whisper alucina castellano y Meta MMS `qwh` sí produce quechua.

## Limitaciones

1. **Manuscritos y letra pintada a mano.** Ninguno de los dos OCR lee cursiva del siglo XIX ni carteles pintados: en `doc_011`
   PaddleOCR no detectó ninguna línea y en la partida de 1897 generó más caracteres falsos que texto real. Los OCR clásicos también
   leen texto ajeno a la escena (globos de una tienda junto a una placa), lo que infla el CER.
2. **Cómputo en CPU y diarización imperfecta.** Sin GPU, PaddleOCR tardó ≈ 54 s por página (además, oneDNN falla con
   PaddlePaddle 3.3 en Windows y hubo que desactivarlo) y el ASR corrió cerca del tiempo real. La diarización a veces crea un
   hablante extra por un monosílabo; y el quechua de Huaylas no pudo medirse con WER porque no hay transcripción humana disponible.

## Ejecutar en local

```bash
cd tarea_2
pip install -r requirements.txt
streamlit run app.py
```

Para regenerar los resultados (no es necesario para ver el dashboard): `uv sync --group docai --group audio`, instalar Tesseract 5
(`winget install UB-Mannheim.TesseractOCR`), `python corpus.py` y ejecutar los dos notebooks.

## Estructura

```
tarea_2/
├── 01_extraccion.ipynb      OCR, ASR, seudonimización, limpieza y EDA (ejecutado)
├── 02_evaluacion.ipynb      CER/WER, comparación de modelos, LLM y auditoría (ejecutado)
├── app.py                   dashboard Streamlit
├── corpus.py                catálogo y descarga del corpus
├── requirements.txt         dependencias del dashboard
├── datos/
│   ├── documentos.csv  transcripciones.csv  extraccion_llm.csv  fuentes.csv
│   ├── segmentos.csv        turnos de habla con tiempos (diarización)
│   ├── metricas_*.csv  comparativa_modelos.csv  evaluacion_textos.csv  auditoria_llm.csv
│   ├── referencias/README.md  reglas de la transcripción manual
│   └── ejemplos/            10 clips OpenSLR 73 publicables
├── modelos/                 (tessdata de Tesseract, no versionado)
└── evidencias_ia/           capturas de la conversación con Claude Code
```

## Bitácora

Issues del repositorio: *T2 – Parte 1: Corpus y extracción (OCR + ASR)*, *T2 – Parte 2: Evaluación y extracción estructurada*,
*T2 – Parte 3: Dashboard y despliegue*. La primera versión del trabajo usaba datos simulados; se descartó y se rehízo con corpus
real (ver `evidencias_ia/`).

## Formato de entrega

```
Tarea 2 – Individual
Fuentes: Wikimedia Commons / OpenSLR 73
Estudiante: (nombre completo) (@fampueroc)
Dashboard público (obligatorio): https://voces-peruanas-fampueroc.streamlit.app/
Carpeta del trabajo: https://github.com/fampueroc/Data-Science-Python/tree/main/tarea_2
Resultados Test: WER: 0.22 | CER: 0.58 | Acuerdo LLM-Humano: 15/20
```
