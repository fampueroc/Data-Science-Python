# Muestra publicable (`datos/ejemplos/`)

Los 10 clips `clip_020.wav` a `clip_029.wav` son frases leídas en español peruano de **OpenSLR 73**
(*Crowdsourced high-quality Peruvian Spanish speech data set*, Google; Guevara-Rukoz et al., 2020), licencia
**CC BY-SA 4.0**, remuestreados a 16 kHz mono. Son voces anónimas que leen oraciones sin datos personales, por eso
el dashboard los puede reproducir con `st.audio`. En total pesan unos 2 MB.

Para el resto del corpus, el dashboard usa las URLs públicas de Wikimedia Commons registradas en
`datos/fuentes.csv` (`url_publica`). Las imágenes se muestran salvo `doc_001`, que contiene nombres de personas privadas vivas. Las entrevistas se reproducen solo si su transcripción no tuvo nombres que seudonimizar.

El corpus original completo (imágenes, audios y salidas de OCR/ASR/LLM) vive en `datos/raw/`, fuera de Git, y se recupera con
`python corpus.py` y los notebooks.
