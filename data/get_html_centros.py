from __future__ import annotations

from pathlib import Path

import requests

BASE = "https://portalinvestigacion.uniovi.es"
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

OUT_DIR = Path(__file__).parent / "html_centros"
TIMEOUT = 30
MAX_INVESTIGADORES = 1000

session = requests.Session()
session.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
        )
    }
)


def construir_url(centro_id: int) -> str:
    return f"{BASE}/unidades/{centro_id}/investigadores"


def obtener_html(url: str) -> str:
    respuesta = session.get(
        url,
        params={"size": MAX_INVESTIGADORES},
        timeout=TIMEOUT,
    )
    respuesta.raise_for_status()
    return respuesta.text


def descargar_html_centros(
    centro_ids: list[int],
    out_dir: Path = OUT_DIR,
) -> tuple[int, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    descargados = 0
    errores = 0

    for centro_id in centro_ids:
        url = construir_url(centro_id)
        archivo = out_dir / f"centro_{centro_id}.html"

        try:
            html = obtener_html(url)
            archivo.write_text(html, encoding="utf-8")
            descargados += 1
            print(f"[OK] {archivo}")
        except requests.RequestException as error:
            errores += 1
            print(f"[ERROR] {url} -> {error}")

    return descargados, errores


def main() -> None:
    descargados, errores = descargar_html_centros(CENTRO_IDS_POR_DEFECTO)
    print(f"HTML descargados en: {OUT_DIR.resolve()}")
    print(f"Resultado: {descargados} descargados, {errores} errores")


if __name__ == "__main__":
    main()
