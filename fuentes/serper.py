"""
Fuente: Serper API (https://serper.dev) — resultados reales de Google.
Hace una llamada POST por cada query que le toca a esta corrida (ver rotación en
config.QUERIES_POR_CORRIDA) y devuelve una lista de resultados normalizados:
{titulo, url, snippet, fuente}.

A diferencia de Google Custom Search, Serper NO tiene el límite de 50 dominios:
busca en toda la web. El operador site: de las QUERIES sigue funcionando
porque por debajo son resultados de Google.
"""
from datetime import datetime, timedelta

import config
import estado
import red

ENDPOINT = "https://google.serper.dev/search"


def _rango_frescura() -> str:
    """Devuelve el valor 'tbs' para limitar a anuncios de los últimos
    config.DIAS_FRESCURA días, usando un rango de fechas personalizado de Google
    (cdr). Formato de fecha: M/D/YYYY."""
    hoy = datetime.now()
    desde = hoy - timedelta(days=config.DIAS_FRESCURA)
    return f"cdr:1,cd_min:{desde.strftime('%m/%d/%Y')},cd_max:{hoy.strftime('%m/%d/%Y')}"


def _detectar_fuente(url: str) -> str:
    u = url.lower()
    if "facebook.com" in u:
        return "Facebook"
    if "tiktok.com" in u:
        return "TikTok"
    if "instagram.com" in u:
        return "Instagram"
    if "eventbrite." in u:
        return "Eventbrite"
    if "meetup.com" in u:
        return "Meetup"
    if "lu.ma" in u or "luma.com" in u:
        return "Luma"
    return "Web"


def buscar() -> list[dict]:
    if not config.SERPER_API_KEY:
        print("[serper] Falta SERPER_API_KEY — se omite esta fuente.")
        return []

    headers = {
        "X-API-KEY": config.SERPER_API_KEY,
        "Content-Type": "application/json",
    }

    tbs = _rango_frescura()
    indices = estado.siguiente_bloque(len(config.QUERIES), config.QUERIES_POR_CORRIDA)
    queries = [config.QUERIES[i] for i in indices]
    if len(queries) < len(config.QUERIES):
        print(f"[serper] Rotación: queries {indices[0]}-{indices[-1]} de {len(config.QUERIES)} "
              f"({len(queries)} créditos esta corrida).")

    resultados: list[dict] = []
    for query in queries:
        payload = {
            "q": query,
            "num": min(config.RESULTADOS_POR_QUERY, 10),
            "hl": "es",
            "gl": "bo",        # geolocalización Bolivia
            "tbs": tbs,        # solo anuncios de los últimos config.DIAS_FRESCURA días
        }
        try:
            r = red.pedir("POST", ENDPOINT, etiqueta="serper", intentos=config.HTTP_INTENTOS,
                          headers=headers, json=payload, timeout=20)
            data = r.json()
        except Exception as e:
            print(f"[serper] Error en query '{query[:40]}...': {e}")
            continue

        for item in data.get("organic", []):
            url = item.get("link", "")
            resultados.append({
                "titulo": item.get("title", "").strip(),
                "url": url,
                "snippet": item.get("snippet", "").strip(),
                "fuente": _detectar_fuente(url),
            })

    print(f"[serper] {len(resultados)} resultados crudos de {len(queries)} queries.")
    return resultados
