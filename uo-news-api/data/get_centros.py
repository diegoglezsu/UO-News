from __future__ import annotations

import json
import re
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://portalinvestigacion.uniovi.es"
URL_OTROS_CENTROS = "https://www.uniovi.es/en/conocenos/otroscentros"
CENTRO_IDS_POR_DEFECTO = [
    47857,
    47868,
    47871,
    47865,
    47863,
    47861,
    47874,
    47872,
    47873,
    47859,
    47876,
    47869,
    47858,
    47864,
]

ROOT = Path(__file__).parent
CARPETA_HTML_CENTROS = ROOT / "html_centros"
SALIDA_JSON = ROOT / "json" / "centros_detalle.json"
TIMEOUT = 30
MAX_INVESTIGADORES = 1000
MAX_WORKERS = 6

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    )
}
_thread_local = threading.local()

EQUIVALENCIAS_NOMBRES = {
    "instituto universitario feijoo de estudios del siglo xviii":
        "Instituto Feijoo de Estudios del Siglo XVIII",
    "instituto universitario de neurociencias del principado de asturias":
        "Instituto de Neurociencias del Principado de Asturias",
    "instituto universitario de oncologia del pricipado de asturias":
        "Instituto Universitario de Oncologia",
    "instituto universitario de ciencias y tecnologias espaciales de asturias":
        "Instituto de Ciencias y Tecnologias Espaciales de Asturias",
    "centro universitario asturias raw materials institute":
        "Centro Universitario de Investigacion Asturias Raw Materials",
}


def limpiar_texto(texto: str | None) -> str:
    texto = (texto or "").replace("\u200b", "").replace("\ufeff", "")
    return " ".join(texto.split()).strip()


def normalizar_nombre(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", limpiar_texto(texto))
    return "".join(
        caracter for caracter in texto.lower()
        if not unicodedata.combining(caracter)
    )


def construir_url_centro(centro_id: int | str) -> str:
    return f"{BASE}/unidades/{centro_id}/investigadores"


def obtener_session() -> requests.Session:
    if not hasattr(_thread_local, "session"):
        _thread_local.session = requests.Session()
        _thread_local.session.headers.update(HEADERS)
    return _thread_local.session


def obtener_html(url: str, params: dict[str, int] | None = None) -> str:
    respuesta = obtener_session().get(url, params=params, timeout=TIMEOUT)
    respuesta.raise_for_status()
    return respuesta.text


def cargar_fuentes_centros() -> list[dict[str, str]]:
    fuentes: list[dict[str, str]] = []

    for centro_id in CENTRO_IDS_POR_DEFECTO:
        path_html = CARPETA_HTML_CENTROS / f"centro_{centro_id}.html"
        fuentes.append(
            {
                "modo": "local" if path_html.exists() else "web",
                "path": str(path_html),
                "url": construir_url_centro(centro_id),
                "centro_id": str(centro_id),
            }
        )

    return fuentes


def extraer_id_centro(path_html: Path, url_centro: str) -> str:
    match_archivo = re.match(r"^centro_(\d+)\.html$", path_html.name)
    if match_archivo:
        return match_archivo.group(1)

    match_url = re.search(r"/unidades/(\d+)/investigadores", url_centro)
    return match_url.group(1) if match_url else ""


def extraer_nombre_centro(soup: BeautifulSoup) -> str:
    titulo = soup.select_one("h1.unidad-header__nombre") or soup.find("h1")
    return limpiar_texto(titulo.get_text(" ", strip=True)) if titulo else ""


def extraer_periodo_centro(soup: BeautifulSoup) -> str:
    periodo = soup.select_one("p.unidad-header__periodo")
    return limpiar_texto(periodo.get_text(" ", strip=True)) if periodo else ""


def extraer_investigadores_centro(soup: BeautifulSoup) -> list[dict[str, str]]:
    investigadores: list[dict[str, str]] = []
    vistos: set[str] = set()

    for item in soup.select("section#miembros div.unidad-miembros__item"):
        enlace = item.select_one(
            "div.c-persona-card__detalles "
            "a[href*='/investigadores/'][href*='/detalle']"
        )
        if not enlace:
            continue

        href = limpiar_texto(enlace.get("href", ""))
        if not href:
            continue

        url_detalle = urljoin(BASE, href)
        if url_detalle in vistos:
            continue
        vistos.add(url_detalle)

        nombre = item.select_one("div.c-persona-card__nombre")
        apellidos = item.select_one("div.c-persona-card__apellidos")
        nombre_listado = limpiar_texto(
            " ".join(
                parte.get_text(" ", strip=True)
                for parte in (nombre, apellidos)
                if parte is not None
            )
        )
        if not nombre_listado:
            nombre_listado = limpiar_texto(enlace.get_text(" ", strip=True))

        investigadores.append(
            {
                "nombre_listado": nombre_listado,
                "url_detalle": url_detalle,
            }
        )

    return investigadores


def extraer_centros_uniovi() -> list[dict[str, str]]:
    html = obtener_html(URL_OTROS_CENTROS)
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(
        ".journal-content-article div.text > ul > li > ul > li"
    )
    centros: list[dict[str, str]] = []

    for item in items:
        nombre = limpiar_texto(item.get_text(" ", strip=True))
        if not nombre:
            continue

        match_acronimo = re.search(r"\s*\(([^()]+)\)\s*$", nombre)
        acronimo = limpiar_texto(match_acronimo.group(1)) if match_acronimo else ""
        if match_acronimo:
            nombre = limpiar_texto(nombre[:match_acronimo.start()])

        enlace = item.find("a", href=True)
        url = urljoin(URL_OTROS_CENTROS, enlace["href"]) if enlace else ""
        centros.append(
            {
                "nombre_centro": nombre,
                "acronimo": acronimo,
                "url_centro": url,
            }
        )

    return centros


def complementar_centros(
    centros: list[dict],
    centros_uniovi: list[dict[str, str]],
) -> list[dict]:
    centros_por_nombre = {
        normalizar_nombre(centro["nombre_centro"]): centro
        for centro in centros
    }

    for centro_uniovi in centros_uniovi:
        nombre_oficial = centro_uniovi["nombre_centro"]
        nombre_equivalente = EQUIVALENCIAS_NOMBRES.get(
            normalizar_nombre(nombre_oficial),
            nombre_oficial,
        )
        existente = centros_por_nombre.get(normalizar_nombre(nombre_equivalente))

        if existente is not None:
            existente["acronimo"] = centro_uniovi["acronimo"]
            continue

        nuevo = {
            "url_centro": centro_uniovi["url_centro"],
            "nombre_centro": nombre_oficial,
            "acronimo": centro_uniovi["acronimo"],
            "periodo": "",
            "investigadores": [],
        }
        centros.append(nuevo)
        centros_por_nombre[normalizar_nombre(nombre_oficial)] = nuevo

    return centros


def extraer_nombre_detalle(soup: BeautifulSoup) -> str:
    titulo = soup.select_one("h1.investigador-header__nombre") or soup.find("h1")
    return limpiar_texto(titulo.get_text(" ", strip=True)) if titulo else ""


def extraer_email_detalle(soup: BeautifulSoup) -> str:
    for bloque in soup.select("p.investigador-detalles__detalle"):
        etiqueta = bloque.find("span")
        if not etiqueta or limpiar_texto(etiqueta.get_text()).lower() not in {
            "email",
            "correo electronico",
            "correo electrónico",
        }:
            continue

        enlace = bloque.select_one('a[href^="mailto:"]')
        if enlace:
            email = limpiar_texto(enlace.get_text(" ", strip=True))
            if not email:
                email = limpiar_texto(enlace.get("href", ""))[7:]
            return email.lower()

    enlace = soup.select_one('a[href^="mailto:"]')
    if enlace:
        email = limpiar_texto(enlace.get_text(" ", strip=True))
        if not email:
            email = limpiar_texto(enlace.get("href", ""))[7:]
        return email.lower()

    return ""


def parsear_detalle_investigador(
    url_detalle: str,
    nombre_listado: str,
) -> dict[str, str]:
    html = obtener_html(url_detalle)
    soup = BeautifulSoup(html, "html.parser")
    email = extraer_email_detalle(soup)

    return {
        "nombre": extraer_nombre_detalle(soup) or nombre_listado,
        "email": email,
        "url_detalle": url_detalle,
    }


def parsear_centro(
    fuente: dict[str, str],
    cache_investigadores: dict[str, dict[str, str]],
) -> dict:
    path_html = Path(fuente["path"])
    url_centro = fuente["url"]

    if fuente.get("modo") == "local":
        html = path_html.read_text(encoding="utf-8", errors="ignore")
    else:
        html = obtener_html(
            url_centro,
            params={"size": MAX_INVESTIGADORES},
        )

    soup = BeautifulSoup(html, "html.parser")
    centro_id = fuente.get("centro_id") or extraer_id_centro(path_html, url_centro)
    investigadores_raw = extraer_investigadores_centro(soup)
    investigadores: list[dict[str, str]] = []

    nuevos = {
        investigador["url_detalle"]: investigador
        for investigador in investigadores_raw
        if investigador["url_detalle"] not in cache_investigadores
    }

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futuros = {
            executor.submit(
                parsear_detalle_investigador,
                url_detalle,
                investigador["nombre_listado"],
            ): (url_detalle, investigador)
            for url_detalle, investigador in nuevos.items()
        }
        for futuro in as_completed(futuros):
            url_detalle, investigador = futuros[futuro]
            try:
                cache_investigadores[url_detalle] = futuro.result()
            except requests.RequestException as error:
                cache_investigadores[url_detalle] = {
                    "nombre": investigador["nombre_listado"],
                    "email": "",
                    "url_detalle": url_detalle,
                    "error": str(error),
                }

    for investigador in investigadores_raw:
        investigadores.append(
            dict(cache_investigadores[investigador["url_detalle"]])
        )

    return {
        "url_centro": construir_url_centro(centro_id),
        "nombre_centro": extraer_nombre_centro(soup),
        "periodo": extraer_periodo_centro(soup),
        "investigadores": investigadores,
    }


def main() -> None:
    fuentes = cargar_fuentes_centros()
    cache_investigadores: dict[str, dict[str, str]] = {}
    resultados = []

    for fuente in fuentes:
        archivo_html = Path(fuente["path"])
        try:
            centro = parsear_centro(fuente, cache_investigadores)
            resultados.append(centro)
            print(
                f"[OK] {archivo_html.name} -> "
                f"{len(centro['investigadores'])} investigadores"
            )
        except (OSError, requests.RequestException) as error:
            print(f"[ERROR] {archivo_html.name}: {error}")

    try:
        centros_uniovi = extraer_centros_uniovi()
        resultados = complementar_centros(resultados, centros_uniovi)
        print(f"[OK] Pagina de Uniovi -> {len(centros_uniovi)} centros")
    except requests.RequestException as error:
        print(f"[ERROR] No se pudo complementar desde {URL_OTROS_CENTROS}: {error}")

    SALIDA_JSON.parent.mkdir(parents=True, exist_ok=True)
    SALIDA_JSON.write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"JSON guardado en: {SALIDA_JSON}")


if __name__ == "__main__":
    main()
