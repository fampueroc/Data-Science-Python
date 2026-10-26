"""Catálogo y descarga del corpus real de la Tarea 2 (documentos + audio peruanos).

    uv run python tarea_2/corpus.py

Todo el material tiene licencia libre y se descarga a `datos/raw/` (fuera de Git):

- Documentos: imágenes de Wikimedia Commons (dominio público, CC0, CC BY, CC BY-SA).
  La licencia y el autor se leen de la API de Commons al descargar, no se escriben a mano.
- Audio: entrevistas de Wikimedia Commons (CC BY-SA 4.0 / CC BY 4.0) y frases leídas de
  OpenSLR 73 (Google, CC BY-SA 4.0), estas últimas con su transcripción humana oficial.

Buenas prácticas: User-Agent descriptivo y pausa de 1,5 s entre solicitudes.
"""
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parent
RAW = RAIZ / "datos" / "raw"
DIR_DOCS = RAW / "documentos"
DIR_AUDIO = RAW / "audio"
API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "tarea2-voces-peruanas/1.0 (curso Data Science con Python; github.com/fampueroc)"}
PAUSA = 1.5

# id: (tipo, archivo en Commons, descripción corta)
DOCUMENTOS = {
    # 8 impresos nítidos
    "doc_001": ("impreso", "Acta de Creación de los Símbolos para el Distrito de Mache.jpg", "Resolución de alcaldía de Mache, La Libertad (2016)"),
    "doc_002": ("impreso", "500000 Intis 1988(Front).jpg", "Billete de 500 000 intis (1988)"),
    "doc_003": ("impreso", "1000 Intis 1988(Front).jpg", "Billete de 1000 intis (1988)"),
    "doc_004": ("impreso", "Pisco-punch-mercurio-peruano-1791.jpg", "Mercurio Peruano (1791)"),
    "doc_005": ("impreso", "El Comercio 1945.jpg", "Portada de El Comercio (1945)"),
    "doc_006": ("impreso", "El Comercio Issue 12.jpg", "El Comercio, número 12 (1839)"),
    "doc_007": ("impreso", "Constitucion politica. De la Republica peruana jurada en Lima el 20 de noviembre de 1823 (IA constitucionpoli00peru).pdf", "Portada de la Constitución peruana de 1823"),
    # revisión visual: la postal de la Oficina de Teléfonos casi no tiene texto -> se reemplazó por esta carta
    # mecanografiada (texto impreso a máquina, no manuscrito)
    "doc_008": ("impreso", "4000004161-0016 - Carta de Carlos J. Bachmann. 1914 julio 4, Maldonado; para Ricardo Palma, Lima.pdf", "Carta mecanografiada a Ricardo Palma (1914)"),
    # 8 fotos con perspectiva, sombras o inclinación
    "doc_009": ("foto", "Placa Calle Capon.jpg", "Placa de la Calle Capón, Lima"),
    "doc_010": ("foto", "Menu Levaggi 09052010.jpg", "Pizarra de menú escrita con tiza, Lince"),
    "doc_011": ("foto", "Cartel Picante de cuy.JPG", "Cartel pintado «Picante de cuy», Ingenio, Junín"),
    "doc_012": ("foto", "Letrero con el antiguo nombre de la calle 15.jpg", "Letrero con el antiguo nombre de una calle, Centro de Lima"),
    "doc_013": ("foto", "Casa de José Santos Chocano en Lima - Placa (izq.).jpg", "Placa en la casa de José Santos Chocano, Lima"),
    "doc_014": ("foto", "Placa del ex-Círculo Militar del Perú en Lima.jpg", "Placa del ex Círculo Militar del Perú, Lima"),
    "doc_015": ("foto", "LimaPlacaCatedral1985.JPG", "Placa conmemorativa en la Catedral de Lima (1985)"),
    "doc_016": ("foto", "Placa de Mariano Nechochea en el Saga Falabella de Miraflores (Lima, Perú) (detalle).jpg", "Placa de Mariano Necochea, Miraflores"),
    # 9 manuscritos
    "doc_017": ("manuscrito", "Acta de Independencia Peru.jpg", "Acta de la Independencia del Perú (1821)"),
    "doc_018": ("manuscrito", "Tarjeta de Ricardo Palma a Luis Antonio Eguiguren Escudero 24 octubre 1912.png", "Tarjeta manuscrita de Ricardo Palma (1912)"),
    "doc_019": ("manuscrito", "Peruvian Telephone Company receipt Lima 1895.JPG", "Recibo de la Peruvian Telephone Company llenado a mano (1895)"),
    "doc_020": ("manuscrito", "Asiento de la partida de bautismo de Raúl Porras Barrenechea.jpg", "Asiento de partida de bautismo (1897)"),
    "doc_021": ("manuscrito", "4000004161-0003 - Carta de Carlos J. Bachmann. 1912 junio 10, Riberalta; para Ricardo Palma, Lima.pdf", "Carta manuscrita a Ricardo Palma (1912)"),
    "doc_022": ("manuscrito", "Fiesta de los Collasuyos.jpg", "Guamán Poma, Nueva corónica: fiesta de los Collasuyos (1615)"),
    "doc_023": ("manuscrito", "Nueva coronica.jpg", "Guamán Poma, Nueva corónica y buen gobierno: portada (1615)"),
    "doc_024": ("manuscrito", "Capac Raymi.jpg", "Guamán Poma, Nueva corónica: Capac Raymi (1615)"),
    "doc_025": ("manuscrito", "\"El primer nueva crónica y buen gobierno\" by Felipe Guamán Poma de Ayala, pg 862.png", "Guamán Poma, Nueva corónica: página 862 (1615)"),
}

# id: (identificador de página en Commons, idioma, descripción corta)
# Se usa el número de página (https://commons.wikimedia.org/?curid=N) y no el título, porque varios títulos llevan el
# nombre de la persona entrevistada y aquí no se publican nombres de personas privadas.
AUDIOS_COMMONS = {
    "clip_001": (119251161, "es", "Entrevista en la calle a una vendedora, El Agustino (2022)"),
    "clip_002": (119251160, "es", "Entrevista en la calle a dos vendedoras, El Agustino (2022)"),
    "clip_003": (121219890, "es", "Dirigente de Fenmucarinap en conferencia de prensa (2022)"),
    "clip_004": (121219891, "es", "Representante de Fenmucarinap Apurímac en conferencia de prensa"),
    "clip_005": (126721889, "es", "Entrevista con megáfono y música de fondo, Huancayo"),
    "clip_006": (119262664, "es", "Mini entrevistas en el medio tiempo del repechaje Perú-Australia"),
    "clip_007": (119950449, "es", "Entrevista a una joven en una marcha"),
    "clip_008": (149433723, "es", "Celebración de la Santísima Trinidad, Shuyo (Áncash)"),
    "clip_009": (149433722, "es", "Celebración de la Santísima Trinidad, Pomabamba (Áncash)"),
    "clip_010": (133964620, "es", "Entrevista en una marcha, estudiante UNMSM"),
    "clip_011": (133964621, "es", "Entrevistas en una marcha, estudiante UNMSM"),
    "clip_012": (121363454, "es", "Entrevista registrada por estudiante UNMSM (1)"),
    "clip_013": (121363453, "es", "Entrevista registrada por estudiante UNMSM (2)"),
    "clip_014": (121363455, "es", "Entrevista registrada por estudiante UNMSM (3)"),
    "clip_015": (121363456, "es", "Entrevista registrada por estudiante UNMSM (4)"),
    "clip_016": (149666949, "es", "Testimonio, departamento de San Martín (Semillas de Conocimiento)"),
    "clip_017": (149666950, "es", "Testimonio 2, departamento de San Martín (Semillas de Conocimiento)"),
    "clip_018": (195401248, "qwh", "Quechua de Huaylas: planta medicinal awrinsha, Shansha"),
    "clip_019": (195381899, "qwh", "Quechua de Huaylas: planta medicinal españolada, Shansha"),
}

OPENSLR73 = "https://www.openslr.org/resources/73/es_pe_{sexo}.zip"
N_OPENSLR_POR_SEXO = 5          # 10 frases leídas: clip_020 a clip_029
SEMILLA = 2026


def _sesion():
    s = requests.Session()
    s.headers.update(UA)
    return s


def _bajar(s, url, destino, intentos=6):
    """GET con reintentos: si el servidor responde 429 (demasiadas solicitudes), espera y vuelve a intentar."""
    for i in range(intentos):
        r = s.get(url, timeout=300)
        if r.status_code == 429:
            time.sleep(min(int(r.headers.get("Retry-After", 0)), 30) or 10 * (i + 1))
            continue
        r.raise_for_status()
        destino.write_bytes(r.content)
        time.sleep(PAUSA)
        return
    raise RuntimeError(f"Commons sigue respondiendo 429 para {url}")


def _api(s, params, intentos=6):
    "Consulta a la API de Commons con reintentos ante 429."
    for i in range(intentos):
        r = s.get(API, params=params | {"format": "json", "formatversion": 2}, timeout=60)
        if r.status_code != 429:
            r.raise_for_status()
            time.sleep(PAUSA)
            return r.json()
        time.sleep(15 * (i + 1))
    raise RuntimeError("Commons sigue respondiendo 429")


def metadatos_commons(claves, ancho=1600):
    """Licencia, autor, URL original y miniatura (para imágenes y PDF) de cada archivo de Commons.

    `claves`: títulos de archivo (str) o identificadores de página (int).
    """
    s, salida = _sesion(), {}
    for i in range(0, len(claves), 20):
        lote = claves[i:i + 20]
        por_id = isinstance(lote[0], int)
        sel = {"pageids": "|".join(map(str, lote))} if por_id else {"titles": "|".join("File:" + t for t in lote)}
        q = _api(s, sel | {"action": "query", "prop": "imageinfo", "iiprop": "url|size|mime|sha1|extmetadata",
                           "iiurlwidth": ancho, "iiextmetadatafilter": "LicenseShortName|Artist|DateTimeOriginal"})["query"]
        normal = {n["to"]: n["from"] for n in q.get("normalized", [])}
        for p in q["pages"]:
            titulo = p["pageid"] if por_id else normal.get(p["title"], p["title"]).removeprefix("File:")
            if "imageinfo" not in p:
                salida[titulo] = None
                continue
            ii = p["imageinfo"][0]
            m = ii.get("extmetadata", {})
            limpiar = lambda k: re.sub(r"<[^>]+>|\s+", " ", m.get(k, {}).get("value", "")).strip()
            sin_query = lambda u: u.split("?")[0]      # Commons agrega ?utm_... a las URLs
            salida[titulo] = {"licencia": limpiar("LicenseShortName"), "autor": limpiar("Artist")[:120],
                              "url_original": sin_query(ii["url"]),
                              "url_pagina": f"https://commons.wikimedia.org/?curid={p['pageid']}",
                              "url_descarga": sin_query(ii.get("thumburl", ii["url"])), "duracion": ii.get("duration"),
                              "sha1_commons": ii.get("sha1")}
    return salida


def bajar_documentos():
    """Descarga las 25 imágenes (miniatura de 1600 px; los PDF se convierten en su página 1)."""
    DIR_DOCS.mkdir(parents=True, exist_ok=True)
    meta = metadatos_commons([v[1] for v in DOCUMENTOS.values()])
    s, filas = _sesion(), []
    for id_, (tipo, titulo, desc) in DOCUMENTOS.items():
        m = meta.get(titulo)
        if m is None:
            print(f"  {id_}: NO EXISTE en Commons -> {titulo}")
            continue
        ext = Path(m["url_descarga"].split("?")[0]).suffix.lower() or ".jpg"
        destino = DIR_DOCS / f"{id_}{'.jpg' if ext == '.jpeg' else ext}"
        if not destino.exists():
            _bajar(s, m["url_descarga"], destino)
        filas.append({"id": id_, "modalidad": "documento", "tipo": tipo, "descripcion": desc,
                      "archivo": destino.relative_to(RAIZ).as_posix(), "titulo_commons": titulo, **m})
    return pd.DataFrame(filas)


def derivado_mp3(s, pageid):
    """URL del mp3 que Commons transcodifica de cada audio.

    Commons limita (429, espera de 10 min) la descarga masiva de archivos *originales* y pide usar
    derivados; el mp3 transcodificado tiene el mismo contenido y basta para transcribir.
    """
    q = _api(s, {"action": "query", "pageids": pageid, "prop": "videoinfo", "viprop": "derivatives"})
    derivados = q["query"]["pages"][0]["videoinfo"][0]["derivatives"]
    mp3 = [d["src"] for d in derivados if d.get("transcodekey") == "mp3"]
    return mp3[0] if mp3 else None


def bajar_audios_commons():
    """Descarga las entrevistas de Commons (mp3 transcodificado por Commons, o el original si ya estaba)."""
    DIR_AUDIO.mkdir(parents=True, exist_ok=True)
    meta = metadatos_commons([v[0] for v in AUDIOS_COMMONS.values()])
    s, filas = _sesion(), []
    for id_, (pageid, idioma, desc) in AUDIOS_COMMONS.items():
        m = meta.get(pageid)
        if m is None:
            print(f"  {id_}: NO EXISTE en Commons -> curid {pageid}")
            continue
        ya = sorted(DIR_AUDIO.glob(f"{id_}.*"))
        if ya:
            destino = ya[0]
        else:
            url = derivado_mp3(s, pageid) or m["url_original"]
            destino = DIR_AUDIO / f"{id_}{Path(url).suffix.lower()}"
            _bajar(s, url, destino)
        m = m | {"url_descarga": url if not ya else m["url_original"]}
        filas.append({"id": id_, "modalidad": "audio", "tipo": "entrevista", "idioma": idioma, "descripcion": desc,
                      "archivo": destino.relative_to(RAIZ).as_posix(), "titulo_commons": pageid, **m})
    return pd.DataFrame(filas)


def bajar_openslr73():
    """Frases leídas en español peruano con transcripción humana oficial (OpenSLR 73).

    Reutiliza el lector por partes (HTTP Range) de `datos.py` de la Sesión 13: no se bajan
    los 900 MB de cada zip, solo las frases elegidas.
    """
    import random
    import zipfile
    sys.path.insert(0, str(RAIZ.parent / "sessions" / "13-audio-a-texto"))
    from datos import ZipRemoto, _guardar_16k

    DIR_AUDIO.mkdir(parents=True, exist_ok=True)
    indice = DIR_AUDIO / "openslr73.csv"
    if indice.exists():
        return pd.read_csv(indice)
    filas, n = [], 20
    for sexo in ["female", "male"]:
        z = zipfile.ZipFile(ZipRemoto(OPENSLR73.format(sexo=sexo)))
        lineas = z.read("line_index.tsv").decode("utf-8").strip().splitlines()
        tabla = pd.DataFrame([l.split("\t") for l in lineas], columns=["archivo_slr", "texto"])
        tabla["hablante"] = tabla["archivo_slr"].str.rsplit("_", n=1).str[0]
        tabla = tabla[tabla["texto"].str.split().str.len().between(10, 25)]
        hablantes = sorted(tabla["hablante"].unique())
        random.Random(SEMILLA).shuffle(hablantes)
        for h in hablantes[:N_OPENSLR_POR_SEXO]:
            fila = tabla[tabla["hablante"] == h].sample(1, random_state=SEMILLA).iloc[0]
            id_ = f"clip_{n:03d}"
            destino = DIR_AUDIO / f"{id_}.wav"
            _guardar_16k(z.read(f"{fila['archivo_slr']}.wav"), destino)
            filas.append({"id": id_, "modalidad": "audio", "tipo": "lectura", "idioma": "es",
                          "descripcion": f"Frase leída, hablante {'mujer' if sexo == 'female' else 'hombre'} (OpenSLR 73)",
                          "archivo": destino.relative_to(RAIZ).as_posix(), "titulo_commons": None,
                          "licencia": "CC BY-SA 4.0", "autor": "Google (Guevara-Rukoz et al., 2020)",
                          "url_original": OPENSLR73.format(sexo=sexo), "url_pagina": "https://www.openslr.org/73/",
                          "archivo_slr": f"{fila['archivo_slr']}.wav", "transcripcion_oficial": fila["texto"].strip()})
            n += 1
    tabla = pd.DataFrame(filas)
    tabla.to_csv(indice, index=False)
    return tabla


if __name__ == "__main__":
    docs = bajar_documentos()
    print(docs.groupby("tipo").size().to_string())
    aud = pd.concat([bajar_audios_commons(), bajar_openslr73()], ignore_index=True)
    print(f"{len(aud)} audios descargados")
