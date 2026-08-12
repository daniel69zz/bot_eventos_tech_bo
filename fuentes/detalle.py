"""
Enriquecimiento de detalle leyendo la página INDIVIDUAL del evento (sin login).

Dos estrategias, según la fuente:

1. Luma (lu.ma) — renderiza en el servidor y mete todo en <script id="__NEXT_DATA__">:
       props.pageProps.initialData.data.event
           - start_at  -> "2026-02-11T16:30:00.000Z"  (ISO en UTC)
           - timezone  -> "America/La_Paz"
           - name, geo_address_info { city, address, region, country }
       props.pageProps.initialData.data.description_mirror -> descripción (rich-text)

2. Eventbrite y Meetup — publican JSON-LD estándar (schema.org/Event) en
   <script type="application/ld+json">: startDate, location.address, description.

En ambos casos sacamos la FECHA REAL del evento (en vez de que el LLM la adivine),
la ciudad y la descripción. Si algo falla, devolvemos el candidato sin tocar.
"""
import json
import re
from datetime import datetime, timedelta, timezone

import config
import red

# Bolivia siempre es UTC-4 (sin horario de verano); sirve de respaldo si no se
# puede resolver la zona horaria nombrada del evento.
_TZ_BOLIVIA = timezone(timedelta(hours=-4))
_RE_NEXT = re.compile(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
_RE_JSONLD = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I)
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BotEventosBolivia/1.0)"}

# Fuentes cuya página individual sabemos leer.
FUENTES_CON_DETALLE = {"Luma", "Eventbrite", "Meetup"}


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


def _fecha_de_iso(valor: str) -> str | None:
    """Fecha 'YYYY-MM-DD' de un startDate de JSON-LD.

    Acá NO convertimos zonas: schema.org da la hora local del evento (con o sin
    offset), así que la parte de fecha ya es la correcta para el asistente."""
    if not isinstance(valor, str) or not valor.strip():
        return None
    try:
        return datetime.fromisoformat(valor.strip().replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        # Algunos sitios mandan solo la fecha, o formatos raros.
        m = re.match(r"(\d{4}-\d{2}-\d{2})", valor.strip())
        return m.group(1) if m else None


def _bajar(url: str) -> str | None:
    try:
        r = red.pedir("GET", url, etiqueta="detalle", intentos=config.HTTP_INTENTOS,
                      headers=_HEADERS, timeout=15)
        return r.text
    except Exception as e:
        print(f"[detalle] No se pudo leer {url[:50]}: {e}")
        return None


# --------------------------------------------------------------------------
# Luma
# --------------------------------------------------------------------------
def _extraer_next_data(html: str) -> dict | None:
    m = _RE_NEXT.search(html)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
        return data["props"]["pageProps"]["initialData"]["data"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def _campos_luma(html: str) -> dict | None:
    """-> {nombre, fecha, ciudad, lugar, descripcion} o None si no se pudo leer."""
    data = _extraer_next_data(html)
    if not data or "event" not in data:
        return None
    ev = data["event"]
    geo = ev.get("geo_address_info") or {}
    ciudad = geo.get("city") or ""
    return {
        "nombre": ev.get("name") or "",
        "fecha": _fecha_local(ev.get("start_at", ""), ev.get("timezone", "")),
        "ciudad": ciudad,
        "lugar": ", ".join(x for x in [geo.get("address"), ciudad] if x),
        "descripcion": _texto_de_mirror(data.get("description_mirror")),
    }


# --------------------------------------------------------------------------
# JSON-LD (Eventbrite, Meetup y cualquier sitio que marque schema.org/Event)
# --------------------------------------------------------------------------
def _es_evento(nodo) -> bool:
    tipo = nodo.get("@type") if isinstance(nodo, dict) else None
    if isinstance(tipo, str):
        return tipo.endswith("Event")
    if isinstance(tipo, list):
        return any(isinstance(t, str) and t.endswith("Event") for t in tipo)
    return False


def _buscar_evento(nodo):
    """Busca el primer objeto Event dentro del JSON-LD (puede venir suelto, en
    una lista, o dentro de @graph)."""
    if isinstance(nodo, dict):
        if _es_evento(nodo):
            return nodo
        for clave in ("@graph", "itemListElement", "item", "subEvent"):
            encontrado = _buscar_evento(nodo.get(clave))
            if encontrado:
                return encontrado
    elif isinstance(nodo, list):
        for elemento in nodo:
            encontrado = _buscar_evento(elemento)
            if encontrado:
                return encontrado
    return None


def _primero(valor):
    """schema.org permite valor único o lista; nos quedamos con el primero."""
    return valor[0] if isinstance(valor, list) and valor else valor


def _campos_jsonld(html: str) -> dict | None:
    for bloque in _RE_JSONLD.findall(html):
        try:
            datos = json.loads(bloque.strip())
        except json.JSONDecodeError:
            continue
        ev = _buscar_evento(datos)
        if not ev:
            continue

        lugar_obj = _primero(ev.get("location")) or {}
        direccion = _primero(lugar_obj.get("address")) if isinstance(lugar_obj, dict) else None
        ciudad = ""
        partes_lugar = []
        if isinstance(lugar_obj, dict) and lugar_obj.get("name"):
            partes_lugar.append(str(lugar_obj["name"]))
        if isinstance(direccion, dict):
            ciudad = str(direccion.get("addressLocality") or "")
            calle = direccion.get("streetAddress")
            partes_lugar.extend(str(x) for x in [calle, ciudad] if x)
        elif isinstance(direccion, str):
            partes_lugar.append(direccion)

        descripcion = ev.get("description") or ""
        if isinstance(descripcion, str):
            descripcion = " ".join(re.sub(r"<[^>]+>", " ", descripcion).split())
        else:
            descripcion = ""

        return {
            "nombre": str(ev.get("name") or ""),
            "fecha": _fecha_de_iso(ev.get("startDate", "")),
            "ciudad": ciudad,
            "lugar": ", ".join(dict.fromkeys(partes_lugar)),
            "descripcion": descripcion,
        }
    return None


# --------------------------------------------------------------------------
def enriquecer(candidato: dict) -> dict:
    """Rellena fecha_oficial / ciudad_oficial y mejora el snippet. Nunca lanza:
    ante cualquier fallo deja el candidato igual."""
    html = _bajar(candidato["url"])
    if html is None:
        return candidato

    try:
        campos = _campos_luma(html) if candidato.get("fuente") == "Luma" else _campos_jsonld(html)
    except Exception as e:
        print(f"[detalle] Error parseando {candidato['url'][:50]}: {e}")
        return candidato
    if not campos:
        return candidato

    if campos["fecha"]:
        candidato["fecha_oficial"] = campos["fecha"]
    if campos["ciudad"]:
        candidato["ciudad_oficial"] = campos["ciudad"]

    # Reescribimos el snippet con la info estructurada para que el LLM clasifique
    # y resuma con datos reales en vez del snippet pobre de Google.
    extras = []
    if campos["nombre"]:
        extras.append(campos["nombre"])
    if campos["fecha"]:
        extras.append(f"Fecha: {campos['fecha']}")
    if campos["lugar"]:
        extras.append(f"Lugar: {campos['lugar']}")
    if campos["descripcion"]:
        extras.append(campos["descripcion"][:500])
    if extras:
        candidato["snippet"] = " | ".join(extras)

    print(f"[detalle] {candidato['fuente']} OK: {candidato['url'][:45]} -> "
          f"{campos['fecha'] or 'sin fecha'}")
    return candidato


def enriquecer_lista(candidatos: list[dict]) -> list[dict]:
    """Enriquece in-place los candidatos de fuentes con detalle (un GET c/u)."""
    con_detalle = [c for c in candidatos if c.get("fuente") in FUENTES_CON_DETALLE]
    if con_detalle:
        print(f"[detalle] Enriqueciendo {len(con_detalle)} candidato(s) con página propia...")
    for c in con_detalle:
        enriquecer(c)
    return candidatos
