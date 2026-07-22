import re
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE = "https://portalinvestigacion.uniovi.es"
URL_LISTADO = f"{BASE}/grupos/buscar"
OUT_DIR = Path(__file__).parent / "html_grupos"
OUT_DIR.mkdir(parents=True, exist_ok=True)
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
})

def obtener_html(url: str) -> str:
    r = session.get(url, timeout=30)
    r.raise_for_status()
    return r.text

def extraer_grupos(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    # Busca todos los enlaces (<a> en HTLM) que apunten al detalle de un grupo
    # Para considerarlo un enlace válido, el atributo href debe contener (*=):
    # "/grupos/" y "/detalle" 
    enlaces = soup.select('a[href*="/grupos/"][href*="/detalle"]')

    vistos = set()
    grupos = []

    for a in enlaces:
        href = a.get("href", "").strip()
        """
        Ejemplo de estructura HTML que buscamos:
        <a href="/grupos/14041/detalle">
            <strong>AECP</strong>
            Accionamientos Eléctricos
        </a>
        """
        # Devuelve todo el texto dentro del HTML ignorando las etiquetas,
        # separa cada parte recuperada con " " y elimina espacios al inicio y final
        texto = a.get_text(" ", strip=True)

        # Saltar enlaces vacíos
        if not href or not texto:
            continue
        
        url_detalle = urljoin(BASE, href)

        # Evitar duplicados por si el HTML repite enlaces
        clave = (texto, url_detalle)
        if not clave in vistos:
            vistos.add(clave)

        # La estructura que queda después de get_text es: "ACRONIMO Nombre del Grupo"
        m = re.match(r"^(\S+)\s+(.+)$", texto)
        if m:
            acronimo = m.group(1).strip()
            nombre = m.group(2).strip()
        else: # Fallback por si alguna entrada no sigue ese patrón (no hay match)
            acronimo = ""
            nombre = texto

        grupos.append({
            "acronimo": acronimo,
            "nombre_grupo": nombre,
            "link_detalle": url_detalle
        })

    # Ordenar alfabéticamente
    grupos.sort(key=lambda x: (x["acronimo"]))
    return grupos

def descargar_html_detalles(grupos: list[dict], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, grupo in enumerate(grupos, start=1):
        url = grupo["link_detalle"]

        # Sacar el id del grupo de la URL
        m = re.search(r"/grupos/(\d+)/detalle", url)
        grupo_id = m.group(1) if m else f"{i:03d}"

        # En el acrónimo del grupo, sustituir cualquier caracter peculiar por -
        # y luego eliminar - del principio y final.
        acr = re.sub(r"[^A-Za-z0-9_.+-]+", "", grupo["acronimo"]).strip("-")
        if not acr:
            raise ValueError(f"Acrónimo vacío para grupo con URL: {url}")
        elif not grupo_id:
            raise ValueError(f"ID vacío para grupo con URL: {url}")
        else:
            nombre = f"grupo_{acr}_{grupo_id}"

        filename = out_dir / f"{nombre}.html"

        try:
            html = obtener_html(url)
            filename.write_text(html, encoding="utf-8")
            print(f"[OK] {filename}")
        except Exception as e:
            print(f"[ERROR] {url} -> {e}")

def main():
    html_listado = obtener_html(URL_LISTADO)
    grupos = extraer_grupos(html_listado)

    df = pd.DataFrame(grupos)
    print(df.head(10))
    print(f"\nTotal grupos extraídos: {len(df)}")

    descargar_html_detalles(grupos, OUT_DIR)
    print(f"HTML descargados en: {OUT_DIR.resolve()}")

if __name__ == "__main__":
    main()