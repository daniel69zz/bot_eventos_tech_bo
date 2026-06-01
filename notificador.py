"""
Notificador: envía los eventos nuevos a un chat de Telegram.
"""
import requests

import config

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
    ciudad = f" · 📍 {evento['ciudad']}" if evento.get("ciudad") else ""
    return (
        f"{emoji} <b>{evento.get('resumen', evento['titulo'])}</b>{ciudad}\n"
        f"<i>{evento['fuente']}</i>\n"
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
