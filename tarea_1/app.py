"""Dashboard de la Tarea 1: clasificador de titulares peruanos.

Uso:  streamlit run app.py
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

AQUI = Path(__file__).parent
CATEGORIAS = ["politica", "economia", "deportes", "ciencia_tecnologia"]
UMBRAL_DUDA = 0.60   # por debajo, la app avisa que el modelo no está seguro

st.set_page_config(page_title="Titulares peruanos", layout="wide")


# ---------------------------------------------------------------- carga
@st.cache_data
def cargar_datos():
    ruta = AQUI / "datos" / "noticias.csv"
    return pd.read_csv(ruta) if ruta.exists() else pd.DataFrame()


@st.cache_data
def cargar_metricas():
    ruta = AQUI / "datos" / "metricas.json"
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}


@st.cache_resource(show_spinner="Cargando el modelo…")
def cargar_modelo():
    """BETO fine-tuned si está en modelo/ (pesa ~400 MB y no va a GitHub); si no, el plan B TF-IDF."""
    carpeta = AQUI / "modelo"
    if (carpeta / "config.json").exists() and any(carpeta.glob("*.safetensors")):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        tok = AutoTokenizer.from_pretrained(carpeta)
        modelo = AutoModelForSequenceClassification.from_pretrained(carpeta).eval()
        nombres = [modelo.config.id2label[i] for i in range(modelo.config.num_labels)]

        def predecir(texto):
            x = tok(texto, return_tensors="pt", truncation=True, max_length=64)
            with torch.no_grad():
                return torch.softmax(modelo(**x).logits[0], -1).numpy(), nombres

        return "BETO (fine-tuning)", predecir

    plan_b = carpeta / "tfidf_logreg.joblib"
    if plan_b.exists():
        m = joblib.load(plan_b)

        def predecir(texto):
            return m["clasificador"].predict_proba(m["vectorizador"].transform([texto]))[0], list(m["clasificador"].classes_)

        return "TF-IDF + regresión logística (plan B: falta el modelo BETO)", predecir
    return None, None


datos, metricas = cargar_datos(), cargar_metricas()
nombre_modelo, predecir = cargar_modelo()

# ---------------------------------------------------------------- encabezado
st.title("¿Se pueden convertir titulares peruanos en un clasificador de noticias?")
st.caption(
    "Tarea 1 · Ciencia de Datos con Python · Noticias de El Comercio clasificadas en "
    "política, economía, deportes y ciencia y tecnología."
)

if metricas:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Noticias en el dataset", metricas["n_noticias"])
    c2.metric("F1 macro en test", f"{metricas['f1_test']:.3f}",
              help="Calculado solo sobre el test reservado. En 3 semillas: " + ", ".join(map(str, metricas["f1_test_3_semillas"])))
    c3.metric("Accuracy en test", f"{metricas['acc_test']:.1%}")
    c4.metric("Etiquetas corregidas a mano", metricas["etiquetas_corregidas_a_mano"],
              help="Filas donde la auditoría cambió la etiqueta que traía la sección del diario.")
else:
    st.warning("No encuentro datos/metricas.json. Corre primero 02_clasificacion.ipynb.")

tab_vivo, tab_modelo, tab_datos = st.tabs(["Clasificar un titular", "Qué tan bueno es el modelo", "Los datos"])

# ---------------------------------------------------------------- 1. en vivo
with tab_vivo:
    if predecir is None:
        st.error("No hay ningún modelo en modelo/. Corre 02_clasificacion.ipynb para generarlo.")
    else:
        st.caption(f"Modelo en uso: **{nombre_modelo}**")
        ejemplos = [
            "Congreso aprueba nuevo retiro de fondos de AFP",
            "Alianza Lima venció 2-0 a Sporting Cristal y se mantiene en la punta",
            "Dólar cierra a la baja y el BCR mantiene la tasa de referencia",
            "Google presenta un nuevo modelo de inteligencia artificial",
            "El gato de mi vecino se perdió en Miraflores",
        ]
        elegido = st.selectbox("Prueba con un ejemplo o escribe el tuyo abajo", ["(escribir el mío)"] + ejemplos)
        texto = st.text_area(
            "Titular", value="" if elegido == "(escribir el mío)" else elegido, height=90,
            placeholder="Ej.: Ministro de Economía anuncia nuevas medidas tributarias",
        ).strip()

        if texto:
            probs, nombres = predecir(texto)
            orden = np.argsort(-probs)
            mejor, p = nombres[orden[0]], float(probs[orden[0]])

            izq, der = st.columns([1, 2])
            with izq:
                st.metric("Categoría predicha", mejor)
                st.metric("Confianza", f"{p:.1%}")
                if p < UMBRAL_DUDA:
                    st.warning(
                        "El modelo no está seguro. Puede ser un titular ambiguo o de un tema que no es "
                        "ninguna de las 4 categorías: el modelo siempre elige una, aunque ninguna encaje."
                    )
            with der:
                graf = pd.DataFrame({"categoría": nombres, "probabilidad": probs}).sort_values("probabilidad")
                fig = px.bar(graf, x="probabilidad", y="categoría", orientation="h", text=graf.probabilidad.map("{:.1%}".format))
                fig.update_traces(marker_color=["#C44E52" if c == mejor else "#9AA5B1" for c in graf["categoría"]], textposition="outside")
                fig.update_layout(xaxis_range=[0, 1.1], height=260, margin=dict(l=0, r=0, t=10, b=0), xaxis_title=None, yaxis_title=None)
                st.plotly_chart(fig, width="stretch")
        else:
            st.info("Escribe un titular para clasificarlo.")

# ---------------------------------------------------------------- 2. modelo
with tab_modelo:
    if not metricas:
        st.info("Sin métricas todavía.")
    else:
        st.subheader("Comparación de enfoques en el test reservado")
        comp = pd.DataFrame(metricas["comparacion"]).T.rename(columns={
            "f1_macro_test": "F1 macro", "accuracy_test": "Accuracy", "ms_por_titular": "ms por titular"})
        st.dataframe(comp.style.format({"F1 macro": "{:.3f}", "Accuracy": "{:.1%}", "ms por titular": "{:.1f}"}, na_rep="–"),
                     width="stretch")
        st.caption(
            "«Subsección» predice la categoría sin leer el texto, solo por la subsección del diario: es el piso que hay "
            "que superar para decir que el modelo aprendió algo del lenguaje."
        )

        izq, der = st.columns(2)
        with izq:
            st.subheader("Matriz de confusión")
            cm = np.array(metricas["matriz_confusion"])
            fig = px.imshow(cm, x=CATEGORIAS, y=CATEGORIAS, text_auto=True, color_continuous_scale="Blues",
                            labels=dict(x="predicha", y="real", color="n"))
            fig.update_layout(coloraxis_showscale=False, height=380, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, width="stretch")
        with der:
            st.subheader("Por categoría")
            rep = pd.DataFrame(metricas["reporte_por_clase"]).T.loc[CATEGORIAS, ["precision", "recall", "f1-score", "support"]]
            st.dataframe(rep.style.format({"precision": "{:.2f}", "recall": "{:.2f}", "f1-score": "{:.2f}", "support": "{:.0f}"}),
                         width="stretch")
            st.caption(f"Test de {metricas['n_test']} noticias: con tan pocas, una sola noticia mueve el recall de una clase varios puntos.")

# ---------------------------------------------------------------- 3. datos
with tab_datos:
    if datos.empty:
        st.info("Sin datos todavía.")
    else:
        cat = st.multiselect("Categoría", CATEGORIAS, default=CATEGORIAS)
        buscar = st.text_input("Buscar en el titular")
        vista = datos[datos.etiqueta.isin(cat)]
        if buscar:
            vista = vista[vista.titular.str.contains(buscar, case=False, na=False)]

        izq, der = st.columns(2)
        conteo = vista.etiqueta.value_counts().reindex(CATEGORIAS).fillna(0).reset_index()
        conteo.columns = ["categoría", "noticias"]
        izq.plotly_chart(px.bar(conteo, x="categoría", y="noticias", text="noticias").update_layout(height=300, margin=dict(t=10)),
                         width="stretch")
        por_dia = vista.groupby(["fecha", "etiqueta"]).size().reset_index(name="noticias")
        der.plotly_chart(px.bar(por_dia, x="fecha", y="noticias", color="etiqueta").update_layout(height=300, margin=dict(t=10)),
                         width="stretch")

        st.dataframe(vista[["titular", "seccion_original", "etiqueta", "fecha", "url"]], width="stretch", hide_index=True,
                     column_config={"url": st.column_config.LinkColumn("enlace")})
        st.caption(f"{len(vista)} noticias · fuente: El Comercio ({metricas.get('fecha_extraccion', '')})")
