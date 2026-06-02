"""
Notificador: envía los eventos nuevos a un chat de Telegram.
"""
from datetime import datetime, timedelta, timezone
from html import escape

import requests

import config

_TZ_BOLIVIA = timezone(timedelta(hours=-4))


def esc(texto: str) -> str:
    """Escapa caracteres reservados de HTML para parse_mode=HTML de Telegram."""
    return escape(texto or "", quote=False)


def _linea_fecha(evento: dict) -> str:
    f = evento.get("fecha_dt")
    if f is None:
        return "🗓️ <i>Fecha por confirmar</i>\n"
    hoy = datetime.now(_TZ_BOLIVIA).date()
    marca = " <i>(ya pasó)</i>" if f < hoy else ""
    return f"🗓️ {f.isoformat()}{marca}\n"

EMOJI_FUENTE = {
    "Facebook": "📘",
    "TikTok": "🎵",
    "Instagram": "📸",
    "Eventbrite": "🎟️",
    "Meetup": "🤝",
    "Web": "🌐",
}


def _formatear(evento: dict) -> str:
    emoji = EMOJI_FUENTE.get(evento["fuente"], "🌐")
    titular = esc(evento.get("resumen") or evento["titulo"])
    ciudad = f" · 📍 {esc(evento['ciudad'])}" if evento.get("ciudad") else ""

    # Descripción rica si el LLM logró extraer info; si no, caemos a solo
    # título + URL (sin línea de descripción).
    descripcion = (evento.get("descripcion") or "").strip()
    linea_desc = f"{esc(descripcion)}\n" if descripcion else ""

    return (
        f"{emoji} <b>{titular}</b>{ciudad}\n"
        f"{_linea_fecha(evento)}"
        f"{linea_desc}"
        f"<i>{esc(evento['fuente'])}</i>\n"
        f'<a href="{evento["url"]}">Ver más →</a>'
    )


def enviar(eventos: list[dict]) -> None:
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[telegram] Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID — no se envía nada.")
        return
    if not eventos:
        print("[telegram] No hay eventos nuevos para enviar.")
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    enviados_ok = 0
    for ev in eventos:
        payload = {
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": _formatear(ev),
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        try:
            r = requests.post(url, json=payload, timeout=20)
            r.raise_for_status()
            enviados_ok += 1
        except Exception as e:
            print(f"[telegram] Error enviando '{ev['titulo'][:40]}': {e}")

    print(f"[telegram] {enviados_ok}/{len(eventos)} mensajes enviados.")
