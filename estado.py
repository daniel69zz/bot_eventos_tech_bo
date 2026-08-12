"""
Estado persistente en un solo archivo JSON (enviados.json).

Guarda dos cosas:
  - "urls": {url: fecha en que se procesó} — para no repetir avisos.
  - "rotacion": por qué query de config.QUERIES arranca la próxima corrida.

Formato en disco (version 2):
    {"version": 2, "urls": {"https://...": "2026-08-12"}, "rotacion": 8}

Se lee también el formato viejo (una lista plana de URLs) y se migra solo.

Dos reglas evitan que el archivo se vuelva una cárcel:
  - Caducidad: una URL se olvida después de config.DIAS_RETENCION_ESTADO días,
    así el archivo no crece para siempre y un evento anual vuelve a ser noticia.
  - Páginas hub: facebook.com/GDGLaPaz o meetup.com/grupo NO son un evento, son
    una página que publica eventos nuevos todo el tiempo. A esas las volvemos a
    revisar cada config.DIAS_REVISITA_HUB días en vez de bloquearlas para siempre.
"""
import json
import os
from datetime import date, datetime, timedelta
from urllib.parse import urlparse

import config

ARCHIVO = os.path.join(os.path.dirname(__file__), "enviados.json")
VERSION = 2

# Dominios donde una URL "corta" (sin ruta propia) es la página de una cuenta o
# comunidad, no un evento puntual.
_DOMINIOS_HUB = (
    "facebook.com", "instagram.com", "tiktok.com", "meetup.com",
    "linkedin.com", "twitter.com", "x.com", "youtube.com", "eventbrite.com",
)


def es_hub(url: str) -> bool:
    """True si la URL es la página de una cuenta/comunidad y no un evento."""
    try:
        partes = urlparse(url)
    except ValueError:
        return False
    dominio = partes.netloc.lower().removeprefix("www.").removeprefix("m.")
    if not any(dominio == d or dominio.endswith("." + d) for d in _DOMINIOS_HUB):
        return False
    ruta = [s for s in partes.path.split("/") if s]
    if "events" in ruta or "event" in ruta:
        return False          # .../events/123 sí es un evento concreto
    if ruta[:1] == ["o"]:
        return True           # eventbrite.com/o/organizador
    return len(ruta) <= 1     # facebook.com/GDGLaPaz, tiktok.com/@cuenta


def _hoy() -> date:
    return datetime.now().date()


def _parsear(valor: str) -> date | None:
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _leer() -> dict:
    """Lee el archivo y lo normaliza al formato actual (migra el viejo)."""
    if not os.path.exists(ARCHIVO):
        return {"version": VERSION, "urls": {}, "rotacion": 0}
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except Exception:
        return {"version": VERSION, "urls": {}, "rotacion": 0}

    if isinstance(datos, list):
        # Formato viejo: lista de URLs sin fecha. Les damos la fecha de hoy para
        # que caduquen a partir de ahora en vez de desaparecer de golpe.
        hoy = _hoy().isoformat()
        return {"version": VERSION, "urls": {u: hoy for u in datos if isinstance(u, str)}, "rotacion": 0}

    if not isinstance(datos, dict):
        return {"version": VERSION, "urls": {}, "rotacion": 0}

    urls = datos.get("urls")
    return {
        "version": VERSION,
        "urls": urls if isinstance(urls, dict) else {},
        "rotacion": datos.get("rotacion", 0) if isinstance(datos.get("rotacion"), int) else 0,
    }


def _guardar(estado: dict) -> None:
    # Escritura in-place (sin rename) para que funcione el bind mount de un solo
    # archivo que usa docker-compose.
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(
            {"version": VERSION, "urls": dict(sorted(estado["urls"].items())), "rotacion": estado["rotacion"]},
            f, ensure_ascii=False, indent=2,
        )


def _purgar(urls: dict[str, str]) -> tuple[dict[str, str], int]:
    """Saca las URLs más viejas que config.DIAS_RETENCION_ESTADO."""
    limite = _hoy() - timedelta(days=config.DIAS_RETENCION_ESTADO)
    vigentes = {}
    for url, valor in urls.items():
        fecha = _parsear(valor)
        if fecha is None or fecha >= limite:
            vigentes[url] = valor if fecha else _hoy().isoformat()
    return vigentes, len(urls) - len(vigentes)


def cargar() -> dict[str, str]:
    """Devuelve {url: fecha} ya purgado (para inspección/tests)."""
    return _purgar(_leer()["urls"])[0]


def _vencida(url: str, valor: str, hoy: date) -> bool:
    """True si toca volver a considerar esta URL (caducó su recuerdo)."""
    fecha = _parsear(valor)
    if fecha is None:
        return True
    dias = config.DIAS_REVISITA_HUB if es_hub(url) else config.DIAS_RETENCION_ESTADO
    return (hoy - fecha).days >= dias


def filtrar_nuevos(resultados: list[dict]) -> list[dict]:
    """Devuelve solo los que no se procesaron antes (o cuyo recuerdo ya caducó)."""
    estado = _leer()
    urls, purgadas = _purgar(estado["urls"])
    if purgadas:
        estado["urls"] = urls
        _guardar(estado)
        print(f"[estado] {purgadas} URLs olvidadas por antigüedad (>{config.DIAS_RETENCION_ESTADO}d).")

    hoy = _hoy()
    nuevos, vistos_en_esta_corrida, revisitas = [], set(), 0
    for r in resultados:
        url = r["url"]
        if url in vistos_en_esta_corrida:
            continue
        conocida = urls.get(url)
        if conocida is not None:
            if not _vencida(url, conocida, hoy):
                continue
            revisitas += 1
        vistos_en_esta_corrida.add(url)
        nuevos.append(r)

    extra = f" ({revisitas} son hubs que toca revisar de nuevo)" if revisitas else ""
    print(f"[estado] {len(nuevos)} nuevos (de {len(resultados)} tras dedup por URL){extra}.")
    return nuevos


def marcar_enviados(resultados: list[dict]) -> None:
    """Marca como procesadas las URLs indicadas (solo las que de verdad se
    evaluaron: si el LLM falló, esas NO se marcan y se reintentan después)."""
    if not resultados:
        return
    estado = _leer()
    estado["urls"], _ = _purgar(estado["urls"])
    hoy = _hoy().isoformat()
    for r in resultados:
        estado["urls"][r["url"]] = hoy
    _guardar(estado)


def siguiente_bloque(total: int, cantidad: int) -> list[int]:
    """Índices de queries que le tocan a esta corrida, rotando entre corridas.

    Devuelve `cantidad` índices consecutivos (circulares) empezando donde quedó
    la corrida anterior, y deja apuntado el arranque de la próxima."""
    if total <= 0:
        return []
    if cantidad <= 0 or cantidad >= total:
        return list(range(total))

    estado = _leer()
    inicio = estado["rotacion"] % total
    indices = [(inicio + i) % total for i in range(cantidad)]
    estado["rotacion"] = (inicio + cantidad) % total
    _guardar(estado)
    return indices
