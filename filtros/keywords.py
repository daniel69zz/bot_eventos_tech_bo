"""
Filtro barato por keywords (corre ANTES del LLM para no gastar llamadas al modelo).
Un resultado pasa si su texto (titulo + snippet) contiene:
  - al menos una keyword de tipo de evento, Y
  - al menos una keyword de lugar (ciudad o Bolivia).
"""
import unicodedata

import config


def _normalizar(texto: str) -> str:
    """minúsculas + sin acentos, para comparar de forma robusta."""
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto


def pasa_filtro(resultado: dict) -> bool:
    texto = _normalizar(f"{resultado['titulo']} {resultado['snippet']}")
    tiene_evento = any(kw in texto for kw in config.KEYWORDS_EVENTO)
    tiene_lugar = any(kw in texto for kw in config.KEYWORDS_LUGAR)
    return tiene_evento and tiene_lugar


def filtrar(resultados: list[dict]) -> list[dict]:
    pasados = [r for r in resultados if pasa_filtro(r)]
    print(f"[keywords] {len(pasados)}/{len(resultados)} pasaron el filtro por keywords.")
    return pasados
