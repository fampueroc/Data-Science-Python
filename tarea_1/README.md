# Tarea 1 · Noticias peruanas: del titular al clasificador

**Pregunta guía:** ¿se pueden convertir titulares peruanos en un clasificador de noticias?

**Respuesta breve**: sí, con matices. Un BERT en español afinado con 259 titulares clasifica en 4 categorías con
F1 macro ≈ 0,87 en un test reservado de 56 noticias. Pero predecir la categoría sin leer el texto solo por la
subsección del diario, da 0,89, así que el número mide cuánto coincide el modelo con la clasificación del medio y no
tanto cuánto «entiende» de noticias. Los detalles y el porqué están abajo.

## 1. Datos

| | |
|---|---|
| Medio | El Comercio (`elcomercio.pe`), opción B |
| Extracción | 18 de octubre de 2026; notas publicadas entre el 6 y el 18 de octubre |
| Candidatas | 400 (las 100 URLs más recientes de los sitemaps de política, economía, deportes y tecnología) |
| Descartadas al extraer | 18 (notas de otras secciones del diario, bajada ausente, URL repetida). Ver `datos/raw/descartes.json` |
| Descartadas en la auditoría | 12 (no encajan en ninguna de las 4 categorías) |
| **Dataset final** | **370 noticias**: política 97 · economía 93 · deportes 98 · ciencia y tecnología 82 |
| Columnas de `datos/noticias.csv` | `titular, bajada, medio, seccion_original, url, fecha, etiqueta` |

**Cortesía con el medio.** `robots.txt` no prohíbe las páginas de artículos ni los sitemaps (el notebook lo comprueba
con `urllib.robotparser`). User-Agent descriptivo, 1,5 s entre pedidos y máximo 1 reintento. Cada artículo se guarda en
`datos/raw/` a medida que se descarga, de modo que el scraping se puede reanudar si se corta. No hizo falta RSS.
Una muestra de 30 URLs respondió 200 en 30.

## 2. Cómo se etiquetó

1. **Etiqueta provisional:** la sección del sitemap de donde salió la URL.
2. **LLM:** Qwen2.5-1.5B-Instruct en local. Se le pide una letra y se leen las probabilidades del primer token
   (idea de la clase 8: la confianza sale de la distribución del modelo). Incluye una opción «ninguna».
   Coincide con la sección en 84,6 % de las noticias.
3. **Auditoría manual** de los 59 desacuerdos (`datos/revision_desacuerdos.csv`) y de 30 noticias al azar
   (`datos/auditoria_muestra.csv`). Resultado: 12 descartes y 10 etiquetas corregidas.

**Cómo se hizo la auditoría, con transparencia.** Para los 59 desacuerdos partí de una propuesta preparada con ayuda
de un asistente de IA (columna `propuesta_asistente`) y la revisé fila por fila; **coincidí con la propuesta en 58 de
59**. Por eso esa parte no es una segunda opinión independiente. La muestra aleatoria de 30 sí se etiquetó a mano sin
propuesta previa: ahí la sección del diario acierta en 93,3 % y el LLM también (con n = 30, ±9 puntos).

## 3. Resultados en el test reservado

Partición 70/15/15 estratificada con semilla 42 (259 / 55 / 56). El test se separó **después** de fijar las etiquetas
y se usó una sola vez, al final. Todos los modelos ven solo el titular.

| Modelo | F1 macro | Accuracy | ms/titular |
|---|---:|---:|---:|
| Subsección del diario (sin leer el texto) | 0,892 | 89,3 % | 0 |
| Zero-shot XNLI en español | 0,521 | 58,9 % | 114 |
| TF-IDF + regresión logística | 0,770 | 76,8 % | 0,4 |
| Embeddings e5 + regresión logística | 0,897 | 89,3 % | 15 |
| Qwen 1.5B zero-shot (titular + bajada) | 0,714 | 89,3 % | n/d |
| **BETO afinado (desplegado)** | **0,874** | 87,5 % | 30 |

BETO con 3 semillas: 0,874 · 0,905 · 0,857 (media 0,879 ± 0,020). El reporte por clase y la matriz de confusión están
en `02_clasificacion.ipynb` y en `datos/metricas.json`.

### Dos hallazgos
1. **La subsección casi basta.** Como las etiquetas nacen de la sección del diario, un «modelo» que ni lee el texto
   alcanza 0,89. Ningún modelo de texto lo supera con claridad, y BETO tampoco le gana a embeddings + regresión
   logística (diferencia de 1–2 noticias, dentro del ruido). Lo desplegué porque la tarea pide un Transformer afinado.
2. **Frontera política/economía.** De los 7 errores de BETO, dos confunden política con economía (mesa técnica UE–Minem
   por infraestructura, operativos contra la minería ilegal), y otros cuatro son notas de opinión o de `mundo` sobre
   turismo en EE. UU., con etiqueta discutible. `deportes` y `ciencia_tecnologia` salen con recall 1,00.

### Dos limitaciones
1. **Test de 56 noticias:** una noticia mueve ≈ 1,8 puntos de F1; las diferencias entre modelos cercanos no son concluyentes.
2. **Ventanas de tiempo distintas por categoría:** las 98 notas de deportes son de 3 días (16–18 oct.), tecnología llega hasta el
   6 de octubre. Palabras de la semana pueden pesar más que el vocabulario temático.

Además, el modelo **siempre elige una de las 4 categorías**: un titular sobre un gato perdido sale como ciencia y
tecnología con ~90 % de confianza. Ver la pestaña «Clasificar» del dashboard.

## 4. Cómo correrlo

```bash
cd tarea_1
pip install -r requirements.txt      # o, desde la raíz del repo: uv sync --group scraping --group hf --group llm --group deploy

jupyter lab                          # 01_recoleccion.ipynb, luego 02_clasificacion.ipynb
streamlit run app.py                 # dashboard en http://localhost:8501
```

- `01_recoleccion.ipynb` descarga ~400 páginas (~10 min por la pausa de cortesía) y reanuda desde `datos/raw/`.
- `02_clasificacion.ipynb` tarda ≈ 25 min en CPU y necesita descargar ~3 GB de modelos (Qwen, BETO, e5, XNLI).
  Las etiquetas del LLM se guardan en `datos/etiquetas_llm.csv`; si el archivo existe, no se vuelve a correr el LLM.
- **Pesos del modelo:** BETO afinado pesa ≈ 440 MB y GitHub rechaza archivos de más de 100 MB, así que `modelo/*.safetensors` está en
  `.gitignore`. Se regenera con el notebook 2. Si falta, el dashboard usa el modelo TF-IDF de `modelo/tfidf_logreg.joblib`
  (83 KB, sí versionado) y lo avisa en pantalla.

## 5. Estructura

```text
tarea_1/
├── 01_recoleccion.ipynb      # robots.txt, sitemaps, scraping reanudable, limpieza y EDA
├── 02_clasificacion.ipynb    # LLM, auditoría, partición, 6 modelos, test y análisis
├── app.py                    # dashboard Streamlit: clasificar en vivo, métricas y datos
├── requirements.txt
├── datos/
│   ├── noticias.csv          # entrega: 7 columnas, 370 filas
│   ├── etiquetas_llm.csv     # probabilidades del LLM y etiqueta final por noticia
│   ├── revision_desacuerdos.csv, auditoria_muestra.csv   # auditoría manual
│   ├── split.csv, predicciones_test.csv, metricas.json
│   └── raw/                  # artículos descargados y descartes
└── modelo/                   # config y tokenizador de BETO; tfidf_logreg.joblib (plan B)
```

## 6. Uso de IA

El enunciado lo permite. Un asistente de IA ayudó con el borrador del scraping, la plantilla del dashboard y la propuesta
inicial de la auditoría (ver sección 2). Las etiquetas finales, las decisiones de diseño y la lectura de resultados se
revisaron contra los datos y las salidas de los notebooks.
