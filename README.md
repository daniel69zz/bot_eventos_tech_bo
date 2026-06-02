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
Filtro + datos con LLM     ← confirma que es evento real y extrae ciudad, fecha,
   │                          titular y una descripción con harto detalle
   ▼
Dedup por evento           ← colapsa el mismo evento que aparece en varias URLs
   │                          (Facebook + TikTok + web…) en un solo aviso
   ▼
Filtro y orden por fecha   ← prioriza eventos futuros; muestra pasados solo si
   │                          ocurrieron hace ≤ 7 días; descarta los más viejos
   ▼
Telegram                   ← te llega el aviso, con fecha y descripción
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

### 3. LLM (filtro fino, fecha y descripción)

Por defecto usa **Groq** (capa gratis generosa, rápido):

1. Creá una API key en https://console.groq.com/keys → es `LLM_API_KEY`.
2. Dejá `LLM_BASE_URL=https://api.groq.com/openai/v1` y
   `LLM_MODEL=llama-3.3-70b-versatile`.

> Como la API es compatible con OpenAI, podés cambiar a OpenAI, OpenRouter o un
> Ollama local solo cambiando `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY`.
> Si dejás `LLM_API_KEY` vacío, el bot funciona igual pero sin filtro fino
> (manda lo que pasó las keywords, sin descripción ni filtro de fecha).

---

## Qué te llega

Cada aviso incluye un titular, la **fecha** del evento, la fuente y una **descripción**
con la info que el LLM pudo extraer (organizador, lugar, cómo inscribirse, etc.):

```
🎟️ Hackathon de IA – UMSA La Paz 2026 · 📍 La Paz
🗓️ 2026-06-15
Hackathon de IA organizado por la UMSA el 15/06. Equipos de 3,
premios en efectivo. Inscripción gratuita en el link.
Eventbrite
Ver más →
```

Detalles del comportamiento:

- **Prioriza eventos futuros** (los más próximos primero). Los **pasados** solo se
  muestran si ocurrieron hace **≤ 7 días**; más viejos se descartan.
- Eventos con fecha que el LLM no logró deducir salen marcados *"Fecha por confirmar"*.
- Si el LLM no consigue suficiente info de un resultado, el mensaje cae al **mínimo:
  solo titular + URL**.
- La "info del contenido" sale del *snippet* de Google, no de la página real. Para
  webs/Eventbrite/Meetup suele venir completa; para Facebook/TikTok/Instagram es más
  pobre (tienen muros de login), así que ahí muchos avisos serán mínimos.

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

En `filtros/llm.py`:

- `DIAS_PASADO_MAX`: cuántos días hacia atrás se permite mostrar un evento ya pasado
  (por defecto `7`). Subilo si querés ver eventos pasados más antiguos.

## Estructura

```
config.py            parámetros y credenciales
main.py              orquesta el pipeline (una corrida)
scheduler.py         loop para Docker: corre cada INTERVALO_HORAS
run_local.py         correr en tu PC leyendo .env (una vez)
estado.py            dedup por URL (enviados.json)
notificador.py       envío a Telegram (formato + fecha del mensaje)
fuentes/serper.py    búsqueda en Serper (Google)
filtros/keywords.py  filtro barato
filtros/llm.py       filtro fino + descripción + dedup por evento + orden por fecha
Dockerfile           imagen del bot
docker-compose.yml   levanta el contenedor (cada 8h)
```
