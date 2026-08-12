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
    # --- Google general, por area tematica (cada string = 1 credito de Serper) ---
    'hackathon OR hackaton OR datathon OR meetup OR "evento tech" OR conferencia OR bootcamp OR taller tecnologia OR programacion Bolivia "La Paz" OR Cochabamba OR "Santa Cruz" 2026',
    'meetup OR taller OR charla OR conferencia "inteligencia artificial" OR IA OR "machine learning" OR ollama OR LLM OR chatgpt OR "ciencia de datos" Bolivia 2026',
    'meetup OR taller OR evento "node js" OR javascript OR python OR react OR "desarrollo de software" OR developer OR programacion Bolivia',
    'meetup OR taller OR conferencia ciberseguridad OR "seguridad informatica" OR hacking OR pentesting OR CTF Bolivia',
    'meetup OR taller OR evento blockchain OR criptomonedas OR cripto OR bitcoin OR ethereum OR web3 Bolivia',
    'meetup OR taller OR evento cloud OR AWS OR Azure OR DevOps OR Docker OR Kubernetes OR Linux OR "codigo abierto" Bolivia',
    'meetup OR taller OR evento "bases de datos" OR SQL OR "big data" OR "data science" OR "analitica de datos" Bolivia',
    'meetup OR taller OR evento n8n OR automatizacion OR "no code" OR "low code" OR RPA Bolivia',
    'GDG OR "Google Developer Group" OR "Women Techmakers" OR "AWS Community" OR "Python Bolivia" OR PyLadies OR DevFest Bolivia',
    # --- Charlas / conferencias / conversatorios con foco en LA PAZ ---
    # (formatos "de hablar", que las queries de arriba —centradas en hackathon/
    #  meetup/taller— suelen dejar pasar)
    'charla OR charlas OR conferencia OR conversatorio OR seminario OR "ciclo de charlas" OR panel OR "mesa redonda" tecnologia OR programacion OR "inteligencia artificial" OR software "La Paz" Bolivia 2026',
    'UMSA OR "Universidad Catolica" OR UCB OR UPB OR EMI OR Univalle OR Unifranz OR "La Salle" OR Loyola charla OR conferencia OR seminario OR congreso OR jornada informatica OR "ingenieria de sistemas" OR tecnologia "La Paz" Bolivia',
    '"GDG La Paz" OR "Python Bolivia" OR "Women Techmakers La Paz" OR "AWS User Group" OR "Bolivia Tech Hub" OR "Startup Bolivia" charla OR meetup OR conferencia OR taller "La Paz"',
    'site:lu.ma OR site:eventbrite.com OR site:meetup.com charla OR conferencia OR talk OR meetup tecnologia OR software OR IA OR data "La Paz" Bolivia',
    # --- Luma (muy usado por comunidades de IA / automatizacion / startups) ---
    'site:lu.ma hackathon OR meetup OR taller OR workshop OR conferencia tecnologia OR programacion Bolivia "Santa Cruz" OR "La Paz" OR Cochabamba',
    'site:lu.ma "inteligencia artificial" OR IA OR "machine learning" OR ollama OR LLM OR n8n OR automatizacion OR startup Bolivia',
    'site:lu.ma blockchain OR cripto OR web3 OR ciberseguridad OR AWS OR cloud OR DevOps OR "node js" OR python Bolivia',
    # --- Facebook (paginas/eventos indexados por Google) ---
    'site:facebook.com hackathon OR meetup OR datathon OR "evento tech" OR taller tecnologia Bolivia "La Paz" OR Cochabamba OR "Santa Cruz"',
    'site:facebook.com meetup OR taller OR workshop n8n OR automatizacion OR "inteligencia artificial" OR "no code" OR ciberseguridad Bolivia',
    # --- Otras plataformas ---
    'site:eventbrite.com tecnologia OR programacion OR startup OR "inteligencia artificial" OR ciberseguridad OR blockchain Bolivia',
    'site:tiktok.com hackathon OR "evento tech" OR meetup tecnologia Bolivia',
    'site:instagram.com hackathon OR meetup OR "evento tech" OR taller tecnologia Bolivia',
]

# ----------------------------------------------------------------------------
# FILTRO POR KEYWORDS (etapa barata, antes del LLM)
# Un resultado pasa si: tiene AL MENOS una keyword de evento Y una ciudad/Bolivia.
# Todo se compara en minúsculas y sin acentos.
# ----------------------------------------------------------------------------
KEYWORDS_EVENTO = [
    # --- Formato del evento ---
    # OJO: el match es por palabra COMPLETA, así que los plurales van aparte
    # ("charla" no matchea "charlas").
    "hackathon", "hackaton", "hackathone", "datathon", "ideathon", "ideaton",
    "meetup", "meetups", "bootcamp", "conferencia", "conferencias", "congreso",
    "charla", "charlas", "taller", "talleres", "workshop", "workshops",
    "webinar", "webinars", "seminario", "seminarios", "masterclass", "curso",
    "diplomado", "capacitacion",
    "feria", "expo", "summit", "cumbre", "foro", "jornada", "jornadas", "encuentro",
    "devfest", "startup weekend", "demo day", "demoday", "tech talk", "code camp",
    "codecamp", "hacknight", "networking", "pitch", "evento tech",
    "evento de tecnologia", "feria tech",
    # --- Formatos "de hablar" (charlas/conferencias y parientes) ---
    "conversatorio", "conversatorios", "ciclo de charlas", "ciclo de conferencias",
    "panel", "mesa redonda", "coloquio", "simposio", "simposium", "ponencia",
    "ponencias", "keynote", "disertacion", "exposicion", "conferencia magistral",
    "charla tecnica", "open talk", "tech week", "semana de la ingenieria",
    "semana tecnologica",
    # --- Programacion / lenguajes / frameworks ---
    "programacion", "desarrollo de software", "developer", "fullstack", "full stack",
    "frontend", "front end", "backend", "back end", "node js", "nodejs", "javascript",
    "typescript", "react", "angular", "vue", "svelte", "next js", "nextjs", "python",
    "django", "flask", "fastapi", "java", "spring", "php", "laravel", "golang", "rust",
    "kotlin", "swift", "flutter", "dart", "c#", ".net", "ruby", "rails", "api", "graphql",
    # --- Inteligencia artificial / datos ---
    "inteligencia artificial", "ia", "ai", "machine learning", "aprendizaje automatico",
    "deep learning", "ml", "llm", "llms", "chatgpt", "gpt", "openai", "ollama", "gemini",
    "claude", "hugging face", "prompt engineering", "agentes de ia", "vision artificial",
    "computer vision", "nlp", "procesamiento de lenguaje natural", "redes neuronales",
    "data science", "ciencia de datos", "bases de datos", "base de datos", "sql",
    "postgresql", "postgres", "mysql", "mongodb", "big data", "data engineering",
    "ingenieria de datos", "analitica de datos", "data analytics", "power bi",
    "business intelligence", "etl",
    # --- Automatizacion / no-code ---
    "n8n", "automatizacion", "no code", "nocode", "low code", "lowcode", "zapier",
    "rpa", "make.com",
    # --- Cloud / DevOps ---
    "cloud", "computacion en la nube", "aws", "amazon web services", "azure",
    "google cloud", "gcp", "devops", "docker", "kubernetes", "k8s", "terraform",
    "ci cd", "cicd", "serverless", "microservicios",
    # --- Ciberseguridad ---
    "ciberseguridad", "seguridad informatica", "seguridad de la informacion", "hacking",
    "ethical hacking", "hacking etico", "pentesting", "pentest", "ctf", "owasp",
    "infosec", "red team", "blue team", "osint", "criptografia",
    # --- Blockchain / cripto ---
    "blockchain", "cadena de bloques", "criptomonedas", "cripto", "bitcoin", "ethereum",
    "web3", "nft", "defi", "smart contracts", "contratos inteligentes", "solidity",
    # --- Linux / open source ---
    "linux", "gnu linux", "ubuntu", "debian", "fedora", "arch linux", "open source",
    "codigo abierto", "software libre", "foss",
    # --- Comunidades / organizadores ---
    "gdg", "google developer", "google developers", "google developer group",
    "women techmakers", "aws community", "aws user group", "aws ug", "mvp",
    "python bolivia", "pyladies", "django girls", "developer circle", "mlsa",
    "github", "gitlab", "freecodecamp", "platzi",
    # --- Hardware / IoT / robotica ---
    "iot", "internet de las cosas", "robotica", "arduino", "raspberry pi", "electronica",
    "sistemas embebidos",
    # --- Producto / diseño / metodologias ---
    "ux", "ui", "ux ui", "experiencia de usuario", "product manager",
    "gestion de productos", "scrum", "agile", "agilidad", "metodologias agiles", "kanban",
    # --- Videojuegos / XR ---
    "game dev", "desarrollo de videojuegos", "videojuegos", "unity", "unreal", "godot",
    "realidad virtual", "vr", "realidad aumentada", "metaverso", "xr",
    # --- Startups / innovacion ---
    "startup", "startups", "emprendimiento", "innovacion", "fintech", "edtech",
    "tecnologia", "transformacion digital", "incubadora", "aceleradora",
]

KEYWORDS_LUGAR = [
    # Pais / gentilicio
    "bolivia", "boliviano", "boliviana", "bolivianos",
    # Ciudades / departamentos
    "la paz", "el alto", "cochabamba", "santa cruz", "santa cruz de la sierra",
    "sucre", "tarija", "oruro", "potosi", "beni", "trinidad", "pando", "chuquisaca",
    "scz", "cocha",
    # Universidades (suelen organizar/anunciar estos eventos)
    "umsa", "umss", "upb", "ucb", "upsa", "univalle", "uagrm", "unifranz", "emi",
    "la salle", "loyola", "udabol", "usip", "epi",
    # Zonas de La Paz (a veces el anuncio dice la zona y no la ciudad)
    "sopocachi", "calacoto", "obrajes", "irpavi", "achumani", "san jorge",
    "zona sur", "miraflores",
]

# Fuentes cuya página individual trae ciudad/fecha estructuradas: no exigimos
# keyword de lugar en el snippet de Google (el snippet de lu.ma suele venir sin
# ciudad y perdíamos charlas reales de La Paz). El lugar se confirma después con
# fuentes/detalle.py y el LLM.
FUENTES_SIN_FILTRO_LUGAR = {"Luma"}

# ----------------------------------------------------------------------------
# FRESCURA: solo resultados PUBLICADOS/INDEXADOS por Google en los últimos N días.
# OJO: esto filtra por fecha de la PÁGINA (cuándo se anunció), NO por la fecha del
# evento. Es a propósito: queremos solo anuncios recientes y aceptamos perder
# eventos anunciados hace mucho aunque ocurran pronto.
# ----------------------------------------------------------------------------
DIAS_FRESCURA = 14          # ventana de antigüedad del anuncio (2 semanas)

RESULTADOS_POR_QUERY = 10   # cuántos resultados pide a Serper por búsqueda

# ----------------------------------------------------------------------------
# COSTO: cada query = 1 crédito de Serper. Con las 21 queries corriendo 3 veces
# al día serían 63 créditos/día y los 2.500 gratis se acaban en ~40 días.
# Por eso rotamos: cada corrida ejecuta solo un bloque de queries y la siguiente
# sigue donde quedó la anterior (el índice se guarda en enviados.json).
# Con 8 por corrida y 3 corridas/día: 24 créditos/día y la lista completa se
# recorre cada ~9 horas.
# Poné 0 para ejecutar TODAS las queries en cada corrida (comportamiento viejo).
# ----------------------------------------------------------------------------
QUERIES_POR_CORRIDA = 8

# ----------------------------------------------------------------------------
# ESTADO (enviados.json)
# ----------------------------------------------------------------------------
# Cuánto tiempo recordamos una URL ya procesada. Pasado ese plazo se olvida:
# el archivo no crece para siempre y un evento anual vuelve a ser noticia.
DIAS_RETENCION_ESTADO = 90
# Las páginas "hub" (facebook.com/GDGLaPaz, meetup.com/grupo…) no son un evento:
# publican eventos nuevos todo el tiempo. A esas las volvemos a mirar seguido en
# vez de bloquearlas para siempre.
DIAS_REVISITA_HUB = 7

# ----------------------------------------------------------------------------
# LLM
# ----------------------------------------------------------------------------
# Candidatos por llamada. Mandar 60 de una vez alarga el prompt y hace que el
# modelo desalinee los índices; en lotes chicos el mapeo es confiable.
LOTE_LLM = 20

# ----------------------------------------------------------------------------
# HTTP / Telegram
# ----------------------------------------------------------------------------
HTTP_INTENTOS = 3           # reintentos ante 429 / 5xx / timeouts
PAUSA_TELEGRAM_SEG = 1.5    # pausa entre mensajes (Telegram limita ~20/min por chat)
