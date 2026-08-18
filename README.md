# 🤖 Bot de eventos tech en Bolivia

Te avisa por **Telegram** sobre hackathones, meetups, **charlas y conferencias** y
eventos tech en **La Paz, Cochabamba y Santa Cruz** (y hackathones online para Bolivia).

## Cómo funciona

```
Serper API (Google)        ← una sola fuente, trae también links de Facebook/TikTok/
   │                          Instagram/Eventbrite ya indexados (sin scrapear nada)
   │                          Las queries ROTAN entre corridas para gastar menos
   ▼
Filtro por keywords        ← gratis: descarta lo que no es "evento + lugar"
   ▼
Dedup por URL              ← no re-procesa lo ya visto (estado en enviados.json,
   │                          con caducidad; las páginas de comunidad se revisan
   │                          cada pocos días)
   ▼
Detalle del evento         ← para Luma / Eventbrite / Meetup abre la página y saca
   │                          la fecha y el lugar REALES (no los adivina el LLM)
   ▼
Filtro + datos con LLM     ← confirma que es evento real y extrae ciudad, fecha,
   │                          titular y una descripción con harto detalle (en lotes)
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
   Cada query de `config.QUERIES` = 1 crédito. Hay 21 queries, pero **no se corren
   todas en cada corrida**: `QUERIES_POR_CORRIDA` (8 por defecto) hace que cada
   corrida tome el siguiente bloque y siga donde quedó la anterior. Con 3 corridas
   al día son **24 créditos/día** (~720/mes) y la lista completa se recorre cada
   ~9 horas. Poné `QUERIES_POR_CORRIDA = 0` para correr todas siempre (63/día).
   Después se paga por uso (~$1 por cada 1,000 búsquedas).

### 3. LLM (filtro fino, fecha y descripción)

Por defecto usa **Groq** (capa gratis generosa, rápido):

1. Creá una API key en https://console.groq.com/keys → es `LLM_API_KEY`.
2. Dejá `LLM_BASE_URL=https://api.groq.com/openai/v1` y
   `LLM_MODEL=openai/gpt-oss-120b`.

> Ojo: Groq **dio de baja** `llama-3.3-70b-versatile` (y `llama-3.1-8b-instant`) el
> 17/06/2026; si lo usás te devuelve `404 model does not exist`. Los reemplazos son
> `openai/gpt-oss-120b` o `qwen/qwen3.6-27b`. La lista viva de modelos vigentes está
> en `GET https://api.groq.com/openai/v1/models`.

> Como la API es compatible con OpenAI, podés cambiar a OpenAI, OpenRouter o un
> Ollama local solo cambiando `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY`.
> El LLM es **obligatorio**: sin él no se avisa nada (mandar los resultados crudos
> de Google a Telegram era puro spam). Los candidatos quedan pendientes para la
> próxima corrida, así que no se pierde nada por configurarlo más tarde.

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
- Para **Luma, Eventbrite y Meetup** el bot abre la página del evento y usa la fecha
  y el lugar **reales** que publica el sitio, no los que deduce el LLM del snippet.
- Para el resto, la info sale del *snippet* de Google. Para webs propias suele venir
  completa; para Facebook/TikTok/Instagram es más pobre (tienen muros de login), así
  que ahí muchos avisos serán mínimos.
- Si la API del LLM falla (rate limit, caída), esos candidatos **no se avisan ni se
  dan por vistos**: se reintentan en la próxima corrida en vez de perderse.

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

## Tests

No necesitan nada extra (usan `unittest`, que viene con Python) ni tocan la red:

```powershell
python -m unittest discover -s tests -t .
```

---

## Personalizar

Todo lo editable está en `config.py`:

- `QUERIES`: qué busca (agregá/quitá búsquedas o cambiá `site:`). Cada query = 1 crédito Serper.
- `QUERIES_POR_CORRIDA`: cuántas queries corre cada vez (rotan). `0` = todas.
- `KEYWORDS_EVENTO` / `KEYWORDS_LUGAR`: el filtro barato. Ojo: el match es por
  **palabra completa**, así que los plurales van listados aparte ("charla" no
  matchea "charlas").
- `FUENTES_SIN_FILTRO_LUGAR`: fuentes a las que no se les exige ciudad en el snippet
  porque el lugar se confirma después leyendo la página (Luma).
- `DIAS_RETENCION_ESTADO` / `DIAS_REVISITA_HUB`: cuánto se recuerda una URL, y cada
  cuánto se vuelven a mirar las páginas de comunidad (facebook.com/GDGLaPaz…).
- `LOTE_LLM`: candidatos por llamada al modelo.
- `HTTP_INTENTOS` / `PAUSA_TELEGRAM_SEG`: reintentos ante 429/5xx y ritmo de envío.
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
red.py               cliente HTTP con reintentos y backoff (lo usan todos)
estado.py            dedup por URL con caducidad + rotación de queries (enviados.json)
notificador.py       envío a Telegram (formato + fecha del mensaje)
fuentes/serper.py    búsqueda en Serper (Google)
fuentes/detalle.py   fecha/lugar reales de la página del evento (Luma, Eventbrite, Meetup)
filtros/keywords.py  filtro barato
filtros/llm.py       filtro fino + descripción + dedup por evento + orden por fecha
tests/               tests con unittest (no tocan la red)
Dockerfile           imagen del bot
docker-compose.yml   levanta el contenedor (cada 8h)
```
