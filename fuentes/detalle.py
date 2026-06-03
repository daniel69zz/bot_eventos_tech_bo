"""
Enriquecimiento de detalle por página INDIVIDUAL de Luma (sin login).

Las páginas de evento de lu.ma renderizan en el servidor e incluyen todo el
detalle en un <script id="__NEXT_DATA__">. Estructura confirmada:
    props.pageProps.initialData.data.event
        - start_at  -> "2026-02-11T16:30:00.000Z"  (ISO en UTC)
        - timezone  -> "America/La_Paz"
        - name, geo_address_info { city, address, region, country }
    props.pageProps.initialData.data.description_mirror -> descripción (rich-text)

Para cada candidato cuya fuente sea Luma bajamos su página y extraemos la FECHA
REAL del evento (en vez de que el LLM la adivine), la ciudad y la descripción.
Si algo falla, devolvemos el candidato sin tocar (modo degradado).
"""
import json
import re
from datetime import datetime, timedelta, timezone

import requests

# Bolivia siempre es UTC-4 (sin horario de verano); sirve de respaldo si no se
# puede resolver la zona horaria nombrada del evento.
_TZ_BOLIVIA = timezone(timedelta(hours=-4))
_RE_NEXT = re.compile(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BotEventosBolivia/1.0)"}


def _texto_de_mirror(nodo) -> str:
    """Aplana el rich-text (ProseMirror) de description_mirror a texto plano."""
    partes: list[str] = []

    def walk(n):
        if isinstance(n, dict):
            if n.get("type") == "text" and n.get("text"):
                partes.append(n["text"])
            for v in n.get("content", []) or []:
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)

    walk(nodo)
    return " ".join(" ".join(partes).split())


def _fecha_local(start_at: str, tz_nombre: str) -> str | None:
    """Convierte start_at (ISO UTC) a la fecha LOCAL del evento -> 'YYYY-MM-DD'."""
    if not start_at:
        return None
    try:
        dt = datetime.fromisoformat(start_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    tz = _TZ_BOLIVIA
    if tz_nombre:
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(tz_nombre)
        except Exception:
            tz = _TZ_BOLIVIA  # respaldo: UTC-4 (exacto para eventos en Bolivia)
    return dt.astimezone(tz).date().isoformat()


def _extraer_data(html: str) -> dict | None:
    m = _RE_NEXT.search(html)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
        return data["props"]["pageProps"]["initialData"]["data"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def enriquecer(candidato: dict) -> dict:
    """Rellena fecha_oficial / ciudad_oficial y mejora el snippet de un evento de
    Luma. Nunca lanza: ante cualquier fallo deja el candidato igual."""
    try:
        r = requests.get(candidato["url"], headers=_HEADERS, timeout=15)
        r.raise_for_status()
        data = _extraer_data(r.text)
    except Exception as e:
        print(f"[detalle] No se pudo leer {candidato['url'][:50]}: {e}")
        return candidato

    if not data or "event" not in data:
        return candidato
    ev = data["event"]

    fecha = _fecha_local(ev.get("start_at", ""), ev.get("timezone", ""))
    if fecha:
        candidato["fecha_oficial"] = fecha

    geo = ev.get("geo_address_info") or {}
    ciudad = geo.get("city") or ""
    if ciudad:
        candidato["ciudad_oficial"] = ciudad

    descripcion = _texto_de_mirror(data.get("description_mirror"))
    lugar = ", ".join(x for x in [geo.get("address"), ciudad] if x)

    # Reescribimos el snippet con la info estructurada para que el LLM clasifique
    # y resuma con datos reales en vez del snippet pobre de Google.
    extras = []
    if ev.get("name"):
        extras.append(ev["name"])
    if fecha:
        extras.append(f"Fecha: {fecha}")
    if lugar:
        extras.append(f"Lugar: {lugar}")
    if descripcion:
        extras.append(descripcion[:500])
    if extras:
        candidato["snippet"] = " | ".join(extras)

    print(f"[detalle] Luma OK: {candidato['url'][:45]} -> {fecha or 'sin fecha'}")
    return candidato


def enriquecer_lista(candidatos: list[dict]) -> list[dict]:
    """Enriquece in-place los candidatos de Luma (un GET por evento)."""
    luma = [c for c in candidatos if c.get("fuente") == "Luma"]
    if luma:
        print(f"[detalle] Enriqueciendo {len(luma)} candidato(s) de Luma...")
    for c in luma:
        enriquecer(c)
    return candidatos
