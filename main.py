"""
Punto de entrada del bot de eventos tech en Bolivia.

Pipeline:
  Serper API  ->  filtro keywords  ->  filtro LLM  ->  dedup por URL  ->  Telegram

Se corre una vez por ejecución (ideal: cada 12h vía GitHub Actions / cron).
"""
from fuentes import serper, detalle
from filtros import keywords, llm
import estado
import notificador


def main() -> None:
    print("=== Bot de eventos tech Bolivia ===")

    # 1. Buscar en Serper (resultados de Google; trae links de Facebook/TikTok/etc.)
    crudos = serper.buscar()

    # 2. Filtro barato por keywords (evento + lugar)
    candidatos = keywords.filtrar(crudos)

    # 3. Quedarse solo con los que NO se enviaron antes (ahorra llamadas al LLM)
    candidatos = estado.filtrar_nuevos(candidatos)

    # 3b. Enriquecer con la FECHA y descripción reales de la página del evento
    #     (Luma, Eventbrite, Meetup; un GET por candidato nuevo de esas fuentes).
    candidatos = detalle.enriquecer_lista(candidatos)

    # 4. Filtro fino + resumen con el LLM, en lotes.
    #    `procesados` son los candidatos que el modelo SÍ llegó a evaluar.
    eventos, procesados = llm.filtrar(candidatos)

    # 5. Enviar a Telegram
    notificador.enviar(eventos)

    # 6. Marcar como procesados los que el LLM evaluó (aprobados o no) para no
    #    re-evaluar la misma basura. Los de un lote que falló NO se marcan: se
    #    reintentan en la próxima corrida en vez de perderse para siempre.
    estado.marcar_enviados(procesados)

    print(f"=== Listo: {len(eventos)} eventos nuevos avisados. ===")


if __name__ == "__main__":
    main()
