from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://portalinvestigacion.uniovi.es"
ROOT = Path(__file__).parent
CARPETA_HTML_SCRIPTS_DATA = ROOT / "html_grupos"
SALIDA_JSON = ROOT / "json" / "grupos_detalle.json"
URL_LISTADO_GRUPOS = f"{BASE}/grupos/buscar"

session = requests.Session()
session.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
        )
    }
)


def limpiar_texto(texto: str | None) -> str:
    return " ".join((texto or "").split()).strip()


def normalizar_etiqueta(texto: str | None) -> str:
    texto_limpio = limpiar_texto(texto).strip(" :").lower()
    texto_limpio = texto_limpio.replace("-", " ").replace("_", " ")
    texto_limpio = unicodedata.normalize("NFKD", texto_limpio)
    texto_limpio = "".join(caracter for caracter in texto_limpio if not unicodedata.combining(caracter))
    return limpiar_texto(texto_limpio)


def obtener_html(url: str) -> str:
    respuesta = session.get(url, timeout=30)
    respuesta.raise_for_status()
    return respuesta.text


def carpeta_html_disponible() -> Path | None:
    if CARPETA_HTML_SCRIPTS_DATA.exists() and any(CARPETA_HTML_SCRIPTS_DATA.glob("*.html")):
        return CARPETA_HTML_SCRIPTS_DATA
    return None


def cargar_fuentes_grupos() -> list[dict[str, str]]:
    carpeta = carpeta_html_disponible()
    if carpeta is not None:
        return [{"modo": "local", "path": str(path_html), "url": ""} for path_html in sorted(carpeta.glob("*.html"))]

    html_listado = obtener_html(URL_LISTADO_GRUPOS)
    soup = BeautifulSoup(html_listado, "html.parser")
    enlaces = soup.select('a[href*="/grupos/"][href*="/detalle"]')

    fuentes: list[dict[str, str]] = []
    vistos: set[str] = set()

    for enlace in enlaces:
        href = limpiar_texto(enlace.get("href", ""))
        if not href:
            continue

        url_detalle = urljoin(BASE, href)
        if url_detalle in vistos:
            continue
        vistos.add(url_detalle)

        match = re.search(r"/grupos/(\d+)/detalle", href)
        grupo_id = match.group(1) if match else "0"
        acronimo = limpiar_texto(enlace.get_text(" ", strip=True))
        acronimo = acronimo.split(" ", 1)[0] if acronimo else grupo_id
        fuentes.append({"modo": "web", "path": f"grupo_{acronimo}_{grupo_id}.html", "url": url_detalle})

    return fuentes


def extraer_texto_etiqueta(soup: BeautifulSoup, etiqueta: str) -> str:
    patron = re.compile(rf"^{re.escape(etiqueta)}\s*(.+)$", re.I)
    for nodo in soup.find_all(string=True):
        texto = limpiar_texto(str(nodo))
        coincidencia = patron.match(texto)
        if coincidencia:
            return coincidencia.group(1).strip()
    return ""


def extraer_grupo_desde_nombre_archivo(path_html: Path) -> tuple[str, str]:
    match = re.match(r"^grupo_(.+)_(\d+)\.html$", path_html.name)
    if match:
        return limpiar_texto(match.group(1)), match.group(2)
    return "", ""


def extraer_acronimo_grupo(soup: BeautifulSoup) -> str:
    h1 = soup.select_one("div.grupo-nombre h1.original span.original")
    if h1:
        return limpiar_texto(h1.get_text(" ", strip=True))
    h1 = soup.find("h1")
    if h1:
        return limpiar_texto(h1.get_text(" ", strip=True))
    return ""


def extraer_titulo_grupo(soup: BeautifulSoup) -> str:
    h2 = soup.select_one("div.grupo-nombre h2")
    if h2:
        return limpiar_texto(h2.get_text(" ", strip=True))
    return ""


def extraer_detalles_grupo(soup: BeautifulSoup) -> dict[str, str]:
    def formatear_fecha(fecha: str) -> str:
        fecha_limpia = limpiar_texto(fecha)
        match = re.match(r"^(\d{1,2})(?:\s+de)?\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)(?:\s+de)?\s+(\d{4})$", fecha_limpia)
        if not match:
            return fecha_limpia

        meses = {
            "january": "01",
            "february": "02",
            "march": "03",
            "april": "04",
            "may": "05",
            "june": "06",
            "july": "07",
            "august": "08",
            "september": "09",
            "october": "10",
            "november": "11",
            "december": "12",
            "enero": "01",
            "febrero": "02",
            "marzo": "03",
            "abril": "04",
            "mayo": "05",
            "junio": "06",
            "julio": "07",
            "agosto": "08",
            "septiembre": "09",
            "octubre": "10",
            "noviembre": "11",
            "diciembre": "12",
        }
        dia, mes, anio = match.groups()
        mes_numero = meses.get(normalizar_etiqueta(mes))
        if not mes_numero:
            return fecha_limpia
        return f"{anio}-{mes_numero}-{int(dia):02d}"

    detalles: dict[str, str] = {}
    for bloque in soup.select("div.grupo-detalles__detalles p.grupo-detalles__detalle"):
        spans = bloque.find_all("span")
        if not spans:
            continue
        etiqueta = normalizar_etiqueta(spans[0].get_text())
        if etiqueta in {"constituido el", "date of inception"} and len(spans) > 1:
            detalles["fecha_constitucion"] = formatear_fecha(spans[1].get_text())
        elif etiqueta in {"activo hasta", "active until"} and len(spans) > 1:
            detalles["fecha_cierre"] = formatear_fecha(spans[1].get_text())
        elif etiqueta in {"departamento", "department"}:
            enlace = bloque.select_one("a")
            if enlace:
                detalles["departamento"] = limpiar_texto(enlace.get_text(" ", strip=True))
        elif etiqueta in {"instituto/centro", "institute/centre", "institute/center"}:
            enlace = bloque.select_one("a")
            if enlace:
                detalles["instituto"] = limpiar_texto(enlace.get_text(" ", strip=True))
    return detalles


def extraer_clasificaciones_grupo(soup: BeautifulSoup) -> dict[str, str]:
    clasif: dict[str, str] = {}
    campos = {
        "area rama conocimiento": "rama_conocimiento",
        "rama de conocimiento": "rama_conocimiento",
        "area anep": "area_anep",
        "area cct": "area_cct",
    }
    for li in soup.select("ul.grupo-clasificaciones > li"):
        spans = li.find_all("span")
        if len(spans) >= 2:
            campo = normalizar_etiqueta(spans[0].get_text())
            valor = limpiar_texto(spans[1].get_text()).rstrip(",")
            clave = campos.get(campo, campo)
            clasif[clave] = valor
    return clasif


def extraer_especialidades_grupo(soup: BeautifulSoup) -> list[str]:
    especialidades: list[str] = []
    for enlace in soup.select("section.publicaciones-topics-topn ol li > a"):
        textos = [limpiar_texto(str(nodo)) for nodo in enlace.children if isinstance(nodo, str)]
        especialidad = limpiar_texto(" ".join(texto for texto in textos if texto))
        if especialidad:
            especialidades.append(especialidad)
    return especialidades


def extraer_responsable_grupo(soup: BeautifulSoup) -> str:
    """Devuelve la URL del responsable del grupo desde la cabecera  ."""
    for bloque in soup.select("div.grupo-detalles__detalles p.grupo-detalles__detalle"):
        spans = bloque.find_all("span", recursive=False)
        if not spans:
            continue
        etiqueta = normalizar_etiqueta(spans[0].get_text())
        if "responsable" not in etiqueta and "leader" not in etiqueta:
            continue
        enlace = bloque.select_one("a[href*='/investigadores/']")
        if enlace:
            href = limpiar_texto(enlace.get("href", ""))
            url = urljoin(BASE, href)
            return url
        span_item = bloque.select_one("span.item")
        if span_item:
            return ""
    return ""


def extraer_miembros_grupo(soup: BeautifulSoup, responsable_url: str = "") -> list[dict[str, str]]:
    miembros: list[dict[str, str]] = []

    # Buscar el contenedor de los items de miembros
    items = soup.select("section#miembros div.grupo-miembros__item")

    vistos: set[str] = set()
    for item in items:
        # Buscar el enlace al detalle dentro del item
        enlace = item.select_one("div.c-persona-card__detalles a[href*='/investigadores/'][href*='/detalle']")
        if not enlace:
            continue

        href = limpiar_texto(enlace.get("href", ""))
        if not href:
            continue

        url_detalle = urljoin(BASE, href)
        if url_detalle in vistos:
            continue
        vistos.add(url_detalle)

        es_ip = False

        # 1) Detectar IP por el rol visible en la tarjeta del miembro
        rol_elem = item.select_one("div.c-persona-card__rol")
        if rol_elem:
            rol_texto = limpiar_texto(rol_elem.get_text()).lower()
            if "responsable" in rol_texto:
                es_ip = True

        # 2) Respalo: comparar con la URL del responsable de la cabecera del grupo
        if not es_ip and responsable_url and url_detalle == responsable_url:
            es_ip = True

        nombre_listado = limpiar_texto(enlace.get_text(" ", strip=True))
        miembros.append({
            "url_detalle": url_detalle,
            "nombre_listado": nombre_listado,
            "es_ip": es_ip
        })

    return miembros


def extraer_colaboradores_grupo(soup: BeautifulSoup) -> list[dict[str, str]]:
    colaboradores: list[dict[str, str]] = []
    for sec in soup.select("section.grupo-miembros"):
        h2 = sec.select_one("h2")
        titulo = normalizar_etiqueta(h2.get_text(" ", strip=True)) if h2 else ""
        if "olaborador" not in titulo and "contributor" not in titulo:
            continue
        for item in sec.select("div.grupo-miembros__item"):
            enlace = item.select_one("div.c-persona-card__detalles a[href*='/investigadores/'][href*='/detalle']")
            if not enlace:
                continue
            href = limpiar_texto(enlace.get("href", ""))
            if not href:
                continue
            nombre = limpiar_texto(enlace.get_text(" ", strip=True))
            colaboradores.append({
                "nombre": nombre,
                "url_detalle": urljoin(BASE, href),
            })
    return colaboradores


def extraer_nombre_detalle(soup: BeautifulSoup) -> str:
    h1 = soup.select_one("h1.investigador-header__nombre") or soup.find("h1")
    if h1:
        return limpiar_texto(h1.get_text(" ", strip=True))
    return ""


def extraer_correo_detalle(soup: BeautifulSoup) -> str:
    for bloque in soup.select("p.investigador-detalles__detalle"):
        etiqueta = bloque.find("span")
        if not etiqueta:
            continue

        etiqueta_txt = limpiar_texto(etiqueta.get_text(" ", strip=True)).lower()
        if etiqueta_txt != "email":
            continue

        enlace = bloque.select_one('a[href^="mailto:"]')
        if enlace:
            correo = limpiar_texto(enlace.get_text(" ", strip=True))
            if not correo:
                href = limpiar_texto(enlace.get("href", ""))
                if href.lower().startswith("mailto:"):
                    correo = href[7:]
            return correo.lower()
    return ""


def extraer_id_uniovi(correo: str) -> str:
    correo_limpio = limpiar_texto(correo).lower()
    if "@" not in correo_limpio:
        return ""
    return correo_limpio.split("@", 1)[0]


def parsear_detalle_investigador(url_detalle: str, nombre_listado: str, es_ip: bool = False) -> dict[str, str]:
    html = obtener_html(url_detalle)
    soup = BeautifulSoup(html, "html.parser")

    nombre = extraer_nombre_detalle(soup) or nombre_listado
    email = extraer_correo_detalle(soup)
    id_uniovi = extraer_id_uniovi(email)

    return {
        "nombre": nombre,
        "email": email,
        "id_uniovi": id_uniovi,
        "url_detalle": url_detalle,
        "es_ip": es_ip
    }


def parsear_grupo(fuente: dict[str, str]) -> dict:
    modo = fuente.get("modo", "local")
    path_html = Path(fuente["path"])
    url_grupo = fuente.get("url", "")

    if modo == "web":
        html = obtener_html(url_grupo)
    else:
        html = path_html.read_text(encoding="utf-8", errors="ignore")

    soup = BeautifulSoup(html, "html.parser")

    acronimo_archivo, grupo_id = extraer_grupo_desde_nombre_archivo(path_html)
    titulo = extraer_titulo_grupo(soup)
    detalles = extraer_detalles_grupo(soup)
    clasificaciones = extraer_clasificaciones_grupo(soup)
    especialidades = extraer_especialidades_grupo(soup)
    colaboradores = extraer_colaboradores_grupo(soup)
    responsable_url = extraer_responsable_grupo(soup)

    miembros_raw = extraer_miembros_grupo(soup, responsable_url=responsable_url)
    miembros: list[dict[str, str]] = []
    for miembro in miembros_raw:
        try:
            detalle = parsear_detalle_investigador(
                miembro["url_detalle"],
                miembro["nombre_listado"],
                es_ip=miembro.get("es_ip", False)
            )
            if detalle["correo"]:
                miembros.append(detalle)
        except Exception as error:
            miembros.append(
                {
                    "nombre": miembro["nombre_listado"],
                    "email": "",
                    "id_uniovi": "",
                    "url_detalle": miembro["url_detalle"],
                    "es_ip": miembro.get("es_ip", False),
                    "error": str(error),
                }
            )

    return {
        "url_grupo": f"https://portalinvestigacion.uniovi.es/grupos/{grupo_id}/detalle",
        "grupo_acronimo": acronimo_archivo,
        "grupo_id": grupo_id,
        "nombre_grupo": titulo,
        "fecha_constitucion": detalles.get("fecha_constitucion", ""),
        "fecha_cierre": detalles.get("fecha_cierre", ""),
        "departamento": detalles.get("departamento", ""),
        "rama_conocimiento": clasificaciones.get("rama_conocimiento", ""),
        "area_anep": clasificaciones.get("area_anep", ""),
        "area_cct": clasificaciones.get("area_cct", ""),
        "especialidades": especialidades,
        "colaboradores": colaboradores,
        "miembros": miembros,
    }


def main() -> None:
    fuentes = cargar_fuentes_grupos()
    if not fuentes:
        print("No se encontraron HTML de grupos en data/html_grupos ni datos/html_grupos, y no se pudo inferir la lista desde la web.")
        return

    resultados = []
    for fuente in fuentes:
        archivo_html = Path(fuente["path"])
        try:
            grupo = parsear_grupo(fuente)
            resultados.append(grupo)
            print(f"[OK] {archivo_html.name} -> {len(grupo['miembros'])} miembros - {len(grupo['colaboradores'])} colaboradores")
        except Exception as error:
            print(f"[ERROR] {archivo_html.name}: {error}")

    SALIDA_JSON.parent.mkdir(parents=True, exist_ok=True)
    SALIDA_JSON.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON guardado en: {SALIDA_JSON}")


if __name__ == "__main__":
    main()
