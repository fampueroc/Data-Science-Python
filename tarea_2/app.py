"""Dashboard · Tarea 2 — Voces y documentos peruanos: del archivo escaneado al texto buscable.

    streamlit run app.py

Solo lee los CSV que producen 01_extraccion.ipynb y 02_evaluacion.ipynb: no carga OCR, ASR ni LLM,
así que funciona en el plan gratuito de Streamlit Community Cloud.
"""
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATOS = Path(__file__).resolve().parent / "datos"
EJEMPLOS = DATOS / "ejemplos"
# documento con nombres de personas privadas vivas: se muestra su texto seudonimizado, no la imagen
SIN_IMAGEN = {"doc_001"}

st.set_page_config(page_title="Voces y documentos peruanos", page_icon="🎙️", layout="wide")


@st.cache_data
def leer(nombre):
    ruta = DATOS / nombre
    return pd.read_csv(ruta, keep_default_na=False) if ruta.exists() else pd.DataFrame()


docs, audios, fuentes = leer("documentos.csv"), leer("transcripciones.csv"), leer("fuentes.csv")
llm, segmentos = leer("extraccion_llm.csv"), leer("segmentos.csv")
met_docs, met_audio, comparativa = leer("metricas_documentos.csv"), leer("metricas_audio.csv"), leer("comparativa_modelos.csv")
eval_textos, auditoria = leer("evaluacion_textos.csv"), leer("auditoria_llm.csv")

fuentes = fuentes.set_index("id") if not fuentes.empty else fuentes
campos = {r.id: json.loads(r.campos_json) for r in llm.itertuples()} if not llm.empty else {}
audios["fuente"] = audios["id"].map(fuentes["tipo"]).map({"entrevista": "Entrevista (Commons)", "lectura": "Lectura (OpenSLR 73)"})

# ───────────────────────────────────────────── encabezado
st.title("🎙️ ¿Pueden convertir documentos escaneados y entrevistas en audio en un archivo de texto estructurado y buscable?")
st.markdown(
    f"**{len(docs)} documentos peruanos** (impresos, fotos y manuscritos) leídos con **PaddleOCR** y "
    f"**{audios['duracion_seg'].sum() / 60:.0f} minutos de entrevistas y lecturas** transcritos con **faster-whisper** "
    "(VAD + diarización) y **Meta MMS** para quechua. Los textos se seudonimizaron, un LLM local (Qwen2.5) extrajo campos "
    "en JSON y los modelos se evaluaron contra transcripciones manuales de 10 documentos y 10 clips."
)
with st.expander("Método y fuentes"):
    st.markdown(
        "- **Corpus real** de Wikimedia Commons (dominio público, CC0, CC BY, CC BY-SA) y OpenSLR 73 (CC BY-SA 4.0). "
        "Licencia y autor de cada archivo en la pestaña *Datos*.\n"
        "- **Todo corre en local y gratis**: PaddleOCR 3.7, Tesseract 5.4, faster-whisper, Meta MMS, Qwen2.5-1.5B. "
        "Este dashboard no ejecuta modelos: muestra resultados precalculados en los notebooks.\n"
        "- **Seudonimización**: nombres de personas privadas → `[PERSONA_n]`; personajes históricos se mantienen. "
        "Las imágenes y audios solo se muestran si su licencia lo permite y no exponen datos personales."
    )

# ───────────────────────────────────────────── filtros
st.sidebar.header("🔍 Búsqueda y filtros")
buscar = st.sidebar.text_input("Buscar en textos OCR y ASR", placeholder="Ej.: Lima, independencia, Perú, planta…").strip()
tipos = st.sidebar.multiselect("Tipo de documento", ["impreso", "foto", "manuscrito"], default=["impreso", "foto", "manuscrito"])
modelos_ocr = st.sidebar.multiselect("Modelo OCR", sorted(docs["modelo_ocr"].unique()), default=sorted(docs["modelo_ocr"].unique()))
fuentes_audio = st.sidebar.multiselect("Fuente de audio", sorted(audios["fuente"].dropna().unique()),
                                       default=sorted(audios["fuente"].dropna().unique()))
modelos_asr = st.sidebar.multiselect("Modelo ASR", sorted(audios["modelo_asr"].unique()), default=sorted(audios["modelo_asr"].unique()))
dmax = float(audios["duracion_seg"].max())
rango = st.sidebar.slider("Duración del clip (s)", 0.0, dmax, (0.0, dmax))


def contiene(serie):
    return serie.str.contains(buscar, case=False, regex=False) if buscar else pd.Series(True, index=serie.index)


docs_f = docs[docs["tipo"].isin(tipos) & docs["modelo_ocr"].isin(modelos_ocr) & contiene(docs["texto_ocr"])]
audios_f = audios[audios["fuente"].isin(fuentes_audio) & audios["modelo_asr"].isin(modelos_asr)
                  & audios["duracion_seg"].between(*rango) & contiene(audios["texto_asr"])]
st.sidebar.caption(f"{len(docs_f)} de {len(docs)} documentos · {len(audios_f)} de {len(audios)} clips")

# ───────────────────────────────────────────── indicadores
def metrica(modalidad, modelo_contiene):
    if comparativa.empty:
        return None
    fila = comparativa[(comparativa["modalidad"] == modalidad) & comparativa["modelo"].str.contains(modelo_contiene, regex=False)]
    return float(fila["error"].iloc[0]) if len(fila) else None


c = st.columns(5)
c[0].metric("Documentos procesados", len(docs))
c[1].metric("Minutos de audio transcritos", f"{audios['duracion_seg'].sum() / 60:.1f}", f"{len(audios)} clips")
cer_p, cer_t = metrica("documentos", "PaddleOCR"), metrica("documentos", "Tesseract")
c[2].metric("CER PaddleOCR (10 docs)", f"{cer_p:.1%}" if cer_p is not None else "—",
            f"Tesseract {cer_t:.1%}" if cer_t is not None else None, delta_color="off")
wer_s, wer_t = metrica("audio", "small"), metrica("audio", "turbo")
c[3].metric("WER Whisper small (10 clips)", f"{wer_s:.1%}" if wer_s is not None else "—",
            f"turbo {wer_t:.1%}" if wer_t is not None else None, delta_color="off")
hechas = auditoria["correcto"].astype(str).str.strip().isin(["0", "1"]) if not auditoria.empty else pd.Series(dtype=bool)
if len(hechas) and hechas.all():
    ok = int(auditoria["correcto"].astype(int).sum())
    c[4].metric("Acuerdo LLM vs. auditoría humana", f"{ok / len(auditoria):.0%}", f"{ok}/{len(auditoria)} correctas", delta_color="off")
else:
    c[4].metric("Acuerdo LLM vs. auditoría humana", "—", "auditoría pendiente", delta_color="off")

tab_res, tab_docs, tab_aud, tab_quien, tab_datos = st.tabs(
    ["📊 Resultados", "📄 Documentos", "🎧 Audios", "👥 Quién dijo qué", "💾 Datos"])

# ───────────────────────────────────────────── resultados
with tab_res:
    g1, g2 = st.columns(2)
    with g1:
        conteo = docs_f.groupby("tipo").size().reindex(["impreso", "foto", "manuscrito"], fill_value=0).reset_index(name="documentos")
        fig = px.bar(conteo, x="tipo", y="documentos", text="documentos", color="tipo",
                     title="Documentos por tipo (según filtros)")
        fig.update_layout(template="plotly_white", showlegend=False)
        st.plotly_chart(fig, width="stretch")
    with g2:
        fig = px.histogram(audios_f, x="duracion_seg", color="fuente", nbins=20,
                           labels={"duracion_seg": "duración (s)"}, title="Duración de los clips (según filtros)")
        fig.update_layout(template="plotly_white")
        st.plotly_chart(fig, width="stretch")
    if not met_docs.empty and not met_audio.empty:
        g3, g4 = st.columns(2)
        with g3:
            d = met_docs.melt(id_vars=["id", "tipo"], value_vars=["cer_paddle", "cer_tesseract"], var_name="modelo", value_name="CER")
            d["modelo"] = d["modelo"].map({"cer_paddle": "PaddleOCR", "cer_tesseract": "Tesseract"})
            fig = px.bar(d.groupby(["tipo", "modelo"])["CER"].mean().reset_index(), x="tipo", y="CER", color="modelo",
                         barmode="group", category_orders={"tipo": ["impreso", "foto", "manuscrito"]},
                         title="Error de caracteres por tipo de documento (muestra de 10)")
            fig.update_layout(template="plotly_white")
            st.plotly_chart(fig, width="stretch")
        with g4:
            cols = [c_ for c_ in met_audio.columns if c_.startswith("wer_")]
            a = met_audio.melt(id_vars=["id", "fuente"], value_vars=cols, var_name="modelo", value_name="WER")
            a["modelo"] = a["modelo"].str.removeprefix("wer_")
            fig = px.bar(a.groupby(["fuente", "modelo"])["WER"].mean().reset_index(), x="fuente", y="WER", color="modelo",
                         barmode="group", title="Error de palabras por fuente de audio (muestra de 10)")
            fig.update_layout(template="plotly_white")
            st.plotly_chart(fig, width="stretch")
        st.subheader("Tabla comparativa de modelos")
        st.dataframe(comparativa.assign(error=comparativa["error"].round(3)), width="stretch", hide_index=True)
    else:
        st.info("Las métricas de evaluación aparecerán cuando se ejecute 02_evaluacion.ipynb.")

# ───────────────────────────────────────────── explorador de documentos
with tab_docs:
    if docs_f.empty:
        st.warning("Ningún documento coincide con la búsqueda o los filtros.")
    else:
        id_doc = st.selectbox("Documento", docs_f["id"],
                              format_func=lambda i: f"{i} · {docs.set_index('id').loc[i, 'tipo']} · {fuentes.loc[i, 'descripcion']}")
        d = docs.set_index("id").loc[id_doc]
        izq, der = st.columns([1.1, 1])
        with izq:
            st.markdown(f"**Fuente:** {d['fuente']} · [página en Commons]({fuentes.loc[id_doc, 'fuente_url']}) · "
                        f"autor: {fuentes.loc[id_doc, 'autor'] or '—'}")
            if id_doc in SIN_IMAGEN:
                st.caption("🔒 Imagen no mostrada: contiene nombres de personas privadas. Se publica solo el texto seudonimizado.")
            elif fuentes.loc[id_doc, "url_publica"]:
                st.image(fuentes.loc[id_doc, "url_publica"], width="stretch")
            st.markdown("**Texto OCR** (" + d["modelo_ocr"] + ")")
            st.text_area("ocr", d["texto_ocr"], height=220, label_visibility="collapsed")
        with der:
            st.markdown("**Campos extraídos por el LLM**")
            st.json(campos.get(id_doc, {}))
            if d["texto_referencia"]:
                st.markdown("**Muestra de evaluación** · referencia manual")
                st.text_area("ref", d["texto_referencia"], height=140, label_visibility="collapsed")
                if not met_docs.empty and id_doc in set(met_docs["id"]):
                    m = met_docs.set_index("id").loc[id_doc]
                    k1, k2 = st.columns(2)
                    k1.metric("CER PaddleOCR", f"{m['cer_paddle']:.1%}")
                    k2.metric("CER Tesseract", f"{m['cer_tesseract']:.1%}")
                    if not eval_textos.empty:
                        t = eval_textos[(eval_textos["id"] == id_doc) & (eval_textos["modelo"] == "tesseract")]
                        if len(t):
                            with st.expander("Ver texto de Tesseract"):
                                st.write(t["texto"].iloc[0])

# ───────────────────────────────────────────── explorador de audios
def reproducible(id_):
    "OpenSLR: copia local publicable. Commons: solo si la transcripción no tuvo nombres que seudonimizar."
    local = EJEMPLOS / f"{id_}.wav"
    if local.exists():
        return str(local)
    texto = audios.set_index("id").loc[id_, "texto_asr"]
    url = fuentes.loc[id_, "url_publica"] if id_ in fuentes.index else ""
    return url if url and "[PERSONA" not in texto else None


with tab_aud:
    if audios_f.empty:
        st.warning("Ningún clip coincide con la búsqueda o los filtros.")
    else:
        id_aud = st.selectbox("Clip", audios_f["id"],
                              format_func=lambda i: f"{i} · {audios.set_index('id').loc[i, 'duracion_seg']:.0f} s · {fuentes.loc[i, 'descripcion']}")
        a = audios.set_index("id").loc[id_aud]
        izq, der = st.columns([1.1, 1])
        with izq:
            st.markdown(f"**{fuentes.loc[id_aud, 'licencia']}** · [fuente]({fuentes.loc[id_aud, 'fuente_url']}) · "
                        f"idioma `{a['idioma']}` · {a['n_hablantes']} hablante(s)")
            src = reproducible(id_aud)
            if src:
                st.audio(src)
            else:
                st.caption("🔒 Audio no reproducible aquí: la persona dice su nombre. Se publica la transcripción seudonimizada.")
            st.markdown(f"**Transcripción** ({a['modelo_asr']})")
            st.text_area("asr", a["texto_asr"].replace(" [HABLANTE", "\n[HABLANTE"), height=260, label_visibility="collapsed")
        with der:
            st.markdown("**Campos extraídos por el LLM**")
            st.json(campos.get(id_aud, {}))
            if a["texto_referencia"]:
                st.markdown("**Muestra de evaluación** · referencia")
                st.write(a["texto_referencia"])
                if not met_audio.empty and id_aud in set(met_audio["id"]):
                    m = met_audio.set_index("id").loc[id_aud]
                    cols = [c_ for c_ in met_audio.columns if c_.startswith("wer_")]
                    for col, k in zip(cols, st.columns(len(cols))):
                        k.metric(f"WER {col.removeprefix('wer_')}", f"{m[col]:.1%}")
                    if not eval_textos.empty:
                        st.dataframe(eval_textos[eval_textos["id"] == id_aud][["modelo", "texto"]], hide_index=True,
                                     width="stretch")

# ───────────────────────────────────────────── quién dijo qué (diarización)
with tab_quien:
    st.markdown("Turnos de cada hablante con sus tiempos, a partir de la diarización (huellas de voz + clustering).")
    multi = audios[audios["n_hablantes"] >= 2]["id"].tolist()
    if multi and not segmentos.empty:
        id_m = st.selectbox("Entrevista con varios hablantes", multi,
                            format_func=lambda i: f"{i} · {audios.set_index('id').loc[i, 'n_hablantes']} hablantes · {fuentes.loc[i, 'descripcion']}")
        segs = segmentos[segmentos["id"] == id_m]
        quien = st.multiselect("Hablantes", sorted(segs["hablante"].unique()), default=sorted(segs["hablante"].unique()))
        resumen = segs.assign(dur=segs["fin"] - segs["inicio"]).groupby("hablante")["dur"].sum().reset_index()
        st.plotly_chart(px.bar(resumen, x="dur", y="hablante", orientation="h", labels={"dur": "segundos hablados"},
                               title="Tiempo de habla por hablante").update_layout(template="plotly_white", height=250),
                        width="stretch")
        avatares = ["🎤", "🗣️", "👤", "👥", "🙂"]
        for s in segs[segs["hablante"].isin(quien)].itertuples():
            n = int(s.hablante.lstrip("H")) - 1
            with st.chat_message("user" if n == 0 else "assistant", avatar=avatares[n % len(avatares)]):
                st.markdown(f"**{s.hablante}** `{s.inicio:.1f}–{s.fin:.1f} s`  \n{s.texto}")

# ───────────────────────────────────────────── datos descargables
with tab_datos:
    opciones = {"Documentos (OCR)": (docs_f, "documentos.csv"), "Transcripciones (ASR)": (audios_f.drop(columns="fuente"), "transcripciones.csv"),
                "Extracción LLM": (llm, "extraccion_llm.csv"), "Fuentes y licencias": (fuentes.reset_index(), "fuentes.csv")}
    if not comparativa.empty:
        opciones["Comparativa de modelos"] = (comparativa, "comparativa_modelos.csv")
    elegido = st.radio("Tabla", list(opciones), horizontal=True)
    tabla, nombre = opciones[elegido]
    st.dataframe(tabla, width="stretch", hide_index=True)
    st.download_button(f"⬇️ Descargar {nombre}", tabla.to_csv(index=False).encode("utf-8"), file_name=nombre, mime="text/csv")

st.caption("Tarea 2 · Data Science con Python 2026 · @fampueroc · textos revisados y seudonimizados · modelos abiertos en local")
