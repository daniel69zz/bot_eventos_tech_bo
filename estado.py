"""
Estado persistente: guarda las URLs ya enviadas para no repetir avisos.
Usa un simple JSON (enviados.json). En Docker se persiste con un volumen.
"""
import json
import os

ARCHIVO = os.path.join(os.path.dirname(__file__), "enviados.json")


def cargar() -> set[str]:
    if not os.path.exists(ARCHIVO):
        return set()
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def guardar(urls: set[str]) -> None:
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(sorted(urls), f, ensure_ascii=False, indent=2)


def filtrar_nuevos(resultados: list[dict]) -> list[dict]:
    """Devuelve solo los que no se enviaron antes (dedup por URL)."""
    enviados = cargar()
    nuevos, vistos_en_esta_corrida = [], set()
    for r in resultados:
        url = r["url"]
        if url in enviados or url in vistos_en_esta_corrida:
            continue
        vistos_en_esta_corrida.add(url)
        nuevos.append(r)
    print(f"[estado] {len(nuevos)} nuevos (de {len(resultados)} tras dedup por URL).")
    return nuevos


def marcar_enviados(resultados: list[dict]) -> None:
    enviados = cargar()
    enviados.update(r["url"] for r in resultados)
    guardar(enviados)
