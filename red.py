"""
Cliente HTTP compartido: reintentos con backoff exponencial.

Todas las APIs que usa el bot (Serper, el LLM, Telegram, las páginas de detalle)
fallan de vez en cuando por rate limit (429) o por un 5xx pasajero. Sin
reintentos, una corrida entera se perdía por un hipo de 2 segundos.

Reglas:
  - Reintenta solo errores transitorios (timeouts, 429 y 5xx). Un 401/404 no se
    reintenta: no va a mejorar solo.
  - Respeta el tiempo que pide el servidor: cabecera `Retry-After` (estándar) o
    `parameters.retry_after` (formato de Telegram). Si no dice nada, usa backoff
    exponencial con jitter.
  - Ante fallo definitivo lanza ErrorHttp; cada módulo decide qué hacer.
"""
import random
import time

import requests

# Códigos que vale la pena reintentar: rate limit y errores de servidor.
_REINTENTABLES = {408, 425, 429, 500, 502, 503, 504}

ESPERA_BASE_SEG = 2.0    # primer backoff; luego 4, 8, 16...
ESPERA_MAX_SEG = 60.0    # techo por espera individual


class ErrorHttp(Exception):
    """Falló la petición después de agotar los reintentos."""


def _espera_pedida_por_servidor(respuesta: requests.Response) -> float | None:
    """Segundos que el servidor pide esperar, o None si no lo indica."""
    cabecera = respuesta.headers.get("Retry-After")
    if cabecera:
        try:
            return float(cabecera)
        except ValueError:
            pass  # puede venir como fecha HTTP; caemos al backoff normal
    # Telegram: {"ok": false, "parameters": {"retry_after": 12}}
    try:
        valor = respuesta.json().get("parameters", {}).get("retry_after")
    except Exception:
        return None
    return float(valor) if isinstance(valor, (int, float)) else None


def _backoff(intento: int) -> float:
    """Espera exponencial (2, 4, 8...) con jitter para no sincronizar reintentos."""
    return min(ESPERA_MAX_SEG, ESPERA_BASE_SEG * (2 ** (intento - 1))) + random.uniform(0, 1)


def pedir(metodo: str, url: str, *, intentos: int = 3, etiqueta: str = "", **kwargs) -> requests.Response:
    """requests.request con reintentos. Devuelve la respuesta OK o lanza ErrorHttp."""
    prefijo = f"[{etiqueta}] " if etiqueta else ""
    ultimo_error = ""

    for intento in range(1, intentos + 1):
        espera = None
        try:
            respuesta = requests.request(metodo, url, **kwargs)
        except requests.RequestException as e:
            ultimo_error = f"{type(e).__name__}: {e}"
        else:
            if respuesta.status_code < 400:
                return respuesta
            ultimo_error = f"HTTP {respuesta.status_code}: {respuesta.text[:150]}"
            if respuesta.status_code not in _REINTENTABLES:
                raise ErrorHttp(f"{prefijo}{ultimo_error}")
            espera = _espera_pedida_por_servidor(respuesta)

        if intento == intentos:
            break
        if espera is None:
            espera = _backoff(intento)
        espera = min(espera, ESPERA_MAX_SEG)
        print(f"{prefijo}Intento {intento}/{intentos} falló ({ultimo_error}). Reintento en {espera:.1f}s.")
        time.sleep(espera)

    raise ErrorHttp(f"{prefijo}{intentos} intentos fallaron. Último error: {ultimo_error}")
