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
    '"resumen": "<una linea atractiva en espanol>"}}]}}\n\n'
    "Incluye en el array SOLO los que es_evento sea true.\n\n"
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
        seleccionados.append(c)

    print(f"[llm] {len(seleccionados)}/{len(candidatos)} confirmados como eventos por el LLM.")
    return seleccionados
