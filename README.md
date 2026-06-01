# 🤖 Bot de eventos tech en Bolivia

Te avisa por **Telegram** sobre hackathones, meetups, conferencias y eventos tech
en **La Paz, Cochabamba y Santa Cruz** (y hackathones online para Bolivia).

## Cómo funciona

```
Serper API (Google)        ← una sola fuente, trae también links de Facebook/TikTok/
   │                          Instagram/Eventbrite ya indexados (sin scrapear nada)
   ▼
Filtro por keywords        ← gratis: descarta lo que no es "evento + lugar"
   ▼
Dedup por URL              ← no re-procesa lo ya visto (estado en enviados.json)
   ▼
Filtro + resumen con LLM   ← confirma que es evento real y lo resume en 1 línea
   ▼
Telegram                   ← te llega el aviso
```

Corre en tu PC con **Docker** (busca solo cada 8 horas) o a mano con Python.

---

## Configuración (una sola vez, ~10 min)

Necesitás 3 cosas: bot de Telegram, una API key de Serper, y una API de LLM.

### 1. Bot de Telegram

1. En Telegram, hablá con **@BotFather** → `/newbot` → seguí los pasos.
2. Te da un **token** (ej. `8123456:AAH...`). Ese es `TELEGRAM_BOT_TOKEN`.
3. Para el `TELEGRAM_CHAT_ID`: escribíle algo a tu bot, después abrí en el navegador
   `https://api.telegram.org/bot<TU_TOKEN>/getUpdates` y copiá el número de
   `"chat":{"id": ...}`. Ese es tu `TELEGRAM_CHAT_ID`.

### 2. Serper (resultados de Google, busca toda la web)

1. Registrate en https://serper.dev → **API Key** → copiá la clave. Eso es `SERPER_API_KEY`.
2. Serper devuelve resultados reales de Google y **busca toda la web** (sin el límite
   de 50 dominios que ahora tiene Google Custom Search).
3. Capa gratis: **2,500 búsquedas por única vez** (no se renueva), válidas 6 meses.
   El bot usa ~6 por corrida, 3 corridas/día = 18/día → ~540/mes. Da para varios meses.
   Después se paga por uso (~$1 por cada 1,000 búsquedas).

### 3. LLM (filtro fino + resumen)

Por defecto usa **Groq** (capa gratis generosa, rápido):

1. Creá una API key en https://console.groq.com/keys → es `LLM_API_KEY`.
2. Dejá `LLM_BASE_URL=https://api.groq.com/openai/v1` y
   `LLM_MODEL=llama-3.3-70b-versatile`.

> Como la API es compatible con OpenAI, podés cambiar a OpenAI, OpenRouter o un
> Ollama local solo cambiando `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY`.
> Si dejás `LLM_API_KEY` vacío, el bot funciona igual pero sin filtro fino
> (manda lo que pasó las keywords, sin resumir).

---

## Dejarlo corriendo con Docker (recomendado: busca cada 8h)

Requiere **Docker Desktop** instalado.

```powershell
Copy-Item .env.example .env   # y completá tus valores
docker compose up -d --build  # lo levanta en segundo plano
```

- Busca al arrancar y después **cada 8 horas** (cambiá `INTERVALO_HORAS` en
  `docker-compose.yml` si querés otra frecuencia).
- Ver logs en vivo: `docker compose logs -f`
- Detenerlo: `docker compose down`
- `restart: unless-stopped` hace que vuelva a levantar solo si reiniciás la PC
  (mientras Docker Desktop arranque con Windows).
- `enviados.json` se monta como volumen, así que recuerda los avisos ya enviados
  entre reinicios.

## Probarlo a mano (sin Docker)

```powershell
pip install -r requirements.txt
Copy-Item .env.example .env   # y completá tus valores
python run_local.py           # corre una sola vez
```

---

## Personalizar

Todo lo editable está en `config.py`:

- `QUERIES`: qué busca (agregá/quitá búsquedas o cambiá `site:`). Cada query = 1 crédito Serper.
- `KEYWORDS_EVENTO` / `KEYWORDS_LUGAR`: el filtro barato.
- Frecuencia de búsqueda: `INTERVALO_HORAS` en `docker-compose.yml` (por defecto 8h).

## Estructura

```
config.py            parámetros y credenciales
main.py              orquesta el pipeline (una corrida)
scheduler.py         loop para Docker: corre cada INTERVALO_HORAS
run_local.py         correr en tu PC leyendo .env (una vez)
estado.py            dedup por URL (enviados.json)
notificador.py       envío a Telegram
fuentes/serper.py    búsqueda en Serper (Google)
filtros/keywords.py  filtro barato
filtros/llm.py       filtro fino + resumen
Dockerfile           imagen del bot
docker-compose.yml   levanta el contenedor (cada 8h)
```
