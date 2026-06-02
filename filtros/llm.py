"""
Filtro/limpieza con LLM (etapa cara, corre DESPUÉS de keywords).

Toma los candidatos que ya pasaron keywords y le pide al modelo que, para cada uno:
  - decida si es REALMENTE un evento tech en La Paz / Cochabamba / Santa Cruz
    (o un hackathon online relevante para Bolivia),
  - genere un resumen de UNA línea, atractivo y claro.

Usa una API compatible con OpenAI (Groq gratis por defecto, o OpenAI/OpenRouter/Ollama).
Si no hay LLM_API_KEY configurada, devuelve los candidatos sin tocar (modo degradado).
"""
import json

import requests

import config

SYSTEM_PROMPT = (
    "Eres un clasificador de eventos de tecnología en Bolivia. "
    "Recibes una lista de resultados de búsqueda (titulo, snippet, fuente). "
    "Para cada uno decides si es un evento tech REAL y relevante: hackathon, meetup, "
    "datathon, conferencia, bootcamp, charla o taller de tecnología/programación, "
    "ubicado en La Paz, Cochabamba o Santa Cruz (Bolivia), o un hackathon online "
    "claramente abierto a bolivianos. Descarta: noticias genéricas, cursos pagados sin "
    "evento, resultados ambiguos o de otros países. "
    "Respondes SOLO con un JSON válido."
)

USER_TEMPLATE = (
    "Analiza estos resultados y devuelve un JSON con esta forma exacta:\n"
    '{{"eventos": [{{"indice": <int>, "es_evento": <bool>, '
    '"ciudad": "<La Paz|Cochabamba|Santa Cruz|Online|Bolivia>", '
    '"clave": "<id-corto-del-evento-en-kebab-case>", '
    '"resumen": "<una linea atractiva en espanol>"}}]}}\n\n'
    "Incluye en el array SOLO los que es_evento sea true.\n"
    "IMPORTANTE: varios resultados pueden referirse AL MISMO evento (su pagina de "
    "Facebook, su TikTok, su Eventbrite, su web, etc.). Asignales a esos la MISMA "
    '"clave" (por ejemplo "hackathon-utb-scz-2026"). Resultados de eventos distintos '
    "deben tener claves distintas.\n\n"
    "Resultados:\n{items}"
)


def _construir_items(candidatos: list[dict]) -> str:
    lineas = []
    for i, c in enumerate(candidatos):
        lineas.append(
            f"[{i}] fuente={c['fuente']} | titulo: {c['titulo']} | snippet: {c['snippet']}"
        )
    return "\n".join(lineas)


def filtrar(candidatos: list[dict]) -> list[dict]:
    if not candidatos:
        return []

    if not config.LLM_API_KEY:
        print("[llm] Sin LLM_API_KEY — se omite el filtro LLM, paso los candidatos tal cual.")
        for c in candidatos:
            c["resumen"] = c["titulo"]
            c["ciudad"] = ""
        return candidatos

    payload = {
        "model": config.LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_TEMPLATE.format(items=_construir_items(candidatos))},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {config.LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        r = requests.post(
            f"{config.LLM_BASE_URL}/chat/completions",
            headers=headers, json=payload, timeout=60,
        )
        r.raise_for_status()
        contenido = r.json()["choices"][0]["message"]["content"]
        data = json.loads(contenido)
    except Exception as e:
        print(f"[llm] Error llamando al LLM ({e}) — paso candidatos sin filtrar.")
        for c in candidatos:
            c["resumen"] = c["titulo"]
            c["ciudad"] = ""
        return candidatos

    seleccionados = []
    for ev in data.get("eventos", []):
        if not ev.get("es_evento"):
            continue
        idx = ev.get("indice")
        if idx is None or idx < 0 or idx >= len(candidatos):
            continue
        c = dict(candidatos[idx])
        c["resumen"] = ev.get("resumen", c["titulo"])
        c["ciudad"] = ev.get("ciudad", "")
        c["clave"] = ev.get("clave", "")
        seleccionados.append(c)

    print(f"[llm] {len(seleccionados)}/{len(candidatos)} confirmados como eventos por el LLM.")
    return _dedup_por_evento(seleccionados)


# Prioridad de fuente cuando varios resultados son el MISMO evento:
# preferimos páginas con info estructurada/oficial antes que redes sociales.
_PRIORIDAD_FUENTE = {
    "Eventbrite": 0, "Meetup": 1, "Web": 2,
    "Facebook": 3, "Instagram": 4, "TikTok": 5,
}


def _dedup_por_evento(eventos: list[dict]) -> list[dict]:
    """Colapsa resultados que el LLM marcó con la misma 'clave' (mismo evento bajo
    distintas URLs) en un solo aviso, eligiendo la mejor fuente."""
    mejor_por_clave: dict[str, dict] = {}
    sin_clave: list[dict] = []
    for ev in eventos:
        clave = (ev.get("clave") or "").strip()
        if not clave:
            sin_clave.append(ev)
            continue
        actual = mejor_por_clave.get(clave)
        if actual is None or _PRIORIDAD_FUENTE.get(ev["fuente"], 9) < _PRIORIDAD_FUENTE.get(actual["fuente"], 9):
            mejor_por_clave[clave] = ev

    unicos = list(mejor_por_clave.values()) + sin_clave
    descartados = len(eventos) - len(unicos)
    if descartados:
        print(f"[dedup] {descartados} resultados eran el mismo evento bajo otra URL — colapsados.")
    return unicos
