"""
Filtro barato por keywords (corre ANTES del LLM para no gastar llamadas al modelo).
Un resultado pasa si su texto (titulo + snippet) contiene:
  - al menos una keyword de evento/tema tech, Y
  - al menos una keyword de lugar (ciudad o Bolivia).

El emparejamiento es por PALABRA COMPLETA (no subcadena), para que acronimos
cortos como "ia", "aws", "gdg" o "sql" no generen falsos positivos dentro de
otras palabras (p. ej. "ia" dentro de "familia" o "noticia").
"""
import re
import unicodedata

import config


def _normalizar(texto: str) -> str:
    """minusculas + sin acentos, para comparar de forma robusta."""
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto


def _compilar(keywords: list[str]) -> re.Pattern:
    """Compila UNA sola regex con todas las keywords, exigiendo limites de palabra.
    Usa lookarounds (?<!\\w)/(?!\\w) en lugar de \\b para que tokens con simbolos
    o numeros como 'n8n', 'c#' o '.net' tambien respeten el limite de palabra."""
    # Normaliza y deduplica; ordena de mas larga a mas corta (no afecta el
    # resultado booleano, pero deja la alternancia mas legible/predecible).
    alternativas = sorted({_normalizar(k) for k in keywords}, key=len, reverse=True)
    patron = r"(?<!\w)(?:" + "|".join(re.escape(k) for k in alternativas) + r")(?!\w)"
    return re.compile(patron)


_RE_EVENTO = _compilar(config.KEYWORDS_EVENTO)
_RE_LUGAR = _compilar(config.KEYWORDS_LUGAR)


def pasa_filtro(resultado: dict) -> bool:
    texto = _normalizar(f"{resultado['titulo']} {resultado['snippet']}")
    if not _RE_EVENTO.search(texto):
        return False
    # Fuentes con detalle estructurado (Luma): el lugar lo confirma después
    # fuentes/detalle.py, así que no lo exigimos en el snippet.
    if resultado.get("fuente") in config.FUENTES_SIN_FILTRO_LUGAR:
        return True
    return bool(_RE_LUGAR.search(texto))


def filtrar(resultados: list[dict]) -> list[dict]:
    pasados = [r for r in resultados if pasa_filtro(r)]
    print(f"[keywords] {len(pasados)}/{len(resultados)} pasaron el filtro por keywords.")
    return pasados
