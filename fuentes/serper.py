"""
Fuente: Serper API (https://serper.dev) — resultados reales de Google.
Hace una llamada POST por cada query de config.QUERIES y devuelve una lista
de resultados normalizados: {titulo, url, snippet, fuente}.

A diferencia de Google Custom Search, Serper NO tiene el límite de 50 dominios:
busca en toda la web. El operador site: de las QUERIES sigue funcionando
porque por debajo son resultados de Google.
"""
import requests

import config

ENDPOINT = "https://google.serper.dev/search"


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
    if "lu.ma" in u:
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

    resultados: list[dict] = []
    for query in config.QUERIES:
        payload = {
            "q": query,
            "num": min(config.RESULTADOS_POR_QUERY, 10),
            "hl": "es",
            "gl": "bo",        # geolocalización Bolivia
            "tbs": "qdr:m",    # solo resultados del último mes (qdr:w = semana, qdr:d = día)
        }
        try:
            r = requests.post(ENDPOINT, headers=headers, json=payload, timeout=20)
            r.raise_for_status()
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

    print(f"[serper] {len(resultados)} resultados crudos de {len(config.QUERIES)} queries.")
    return resultados
