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

    # 3b. Enriquecer eventos de Luma con su FECHA y descripción reales (lee la
    #     página individual; un GET por candidato nuevo de Luma).
    candidatos = detalle.enriquecer_lista(candidatos)

    # 4. Filtro fino + resumen con el LLM
    eventos = llm.filtrar(candidatos)

    # 5. Enviar a Telegram
    notificador.enviar(eventos)

    # 6. Marcar como procesados TODOS los candidatos que entraron al LLM
    #    (no solo los aprobados) para no re-evaluar la misma basura en cada corrida.
    estado.marcar_enviados(candidatos)

    print(f"=== Listo: {len(eventos)} eventos nuevos avisados. ===")


if __name__ == "__main__":
    main()
