"""
Configuración central del bot.
Todo lo sensible (API keys) se lee de variables de entorno.
Lo no sensible (queries, keywords) se edita acá directamente.
"""
import os

# ----------------------------------------------------------------------------
# CREDENCIALES (se leen de variables de entorno; en local desde el archivo .env)
# ----------------------------------------------------------------------------
# Serper (https://serper.dev) — resultados reales de Google, busca toda la web.
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# LLM — compatible con cualquier API estilo OpenAI (Groq, OpenRouter, OpenAI, Ollama local)
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile")

# ----------------------------------------------------------------------------
# QUÉ BUSCAR — cada string es una búsqueda independiente (1 crédito de Serper c/u).
# El operador site: fuerza a que aparezcan FB / TikTok / etc. ya indexados por Google.
# ----------------------------------------------------------------------------
QUERIES = [
    'hackathon OR meetup OR "evento tech" La Paz OR Cochabamba OR "Santa Cruz" Bolivia 2026',
    'site:facebook.com hackathon OR meetup OR datathon OR "evento tech" Bolivia "La Paz" OR Cochabamba OR "Santa Cruz"',
    'site:facebook.com meetup OR taller OR workshop n8n OR automatizacion OR "no code" Bolivia "Santa Cruz" OR "La Paz" OR Cochabamba',
    'site:tiktok.com hackathon OR evento tech Bolivia',
    'site:eventbrite.com tecnologia OR programacion OR startup Bolivia',
    'site:lu.ma hackathon OR meetup OR taller OR workshop tecnologia OR programacion Bolivia "Santa Cruz" OR "La Paz" OR Cochabamba',
    'site:lu.ma n8n OR automatizacion OR "no code" OR startup OR "inteligencia artificial" Bolivia',
    'site:instagram.com hackathon OR meetup OR evento tech Bolivia',
    'hackathon OR bootcamp OR conferencia programacion Bolivia 2026',
]

# ----------------------------------------------------------------------------
# FILTRO POR KEYWORDS (etapa barata, antes del LLM)
# Un resultado pasa si: tiene AL MENOS una keyword de evento Y una ciudad/Bolivia.
# Todo se compara en minúsculas y sin acentos.
# ----------------------------------------------------------------------------
KEYWORDS_EVENTO = [
    "hackathon", "hackaton", "hackathone", "datathon", "ideathon", "ideaton",
    "meetup", "bootcamp", "conferencia", "charla", "taller", "workshop",
    "evento tech", "evento de tecnologia", "feria tech", "startup weekend",
    "programacion", "developer", "devfest", "tech talk", "inteligencia artificial",
    "n8n", "automatizacion", "no code", "low code", "nocode", "lowcode",
]

KEYWORDS_LUGAR = [
    "la paz", "cochabamba", "santa cruz", "scz", "cocha", "bolivia",
    "umsa", "umss", "upb", "ucb", "upsa", "univalle", "el alto",
]

# Cuántas horas hacia atrás considerar "nuevo" no aplica acá (Serper no da fecha exacta),
# la deduplicación se hace por URL en estado.py
RESULTADOS_POR_QUERY = 10   # cuántos resultados pide a Serper por búsqueda
