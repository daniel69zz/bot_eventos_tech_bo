"""
Planificador para correr el bot dentro de Docker.
Ejecuta el pipeline una vez al arrancar y luego cada INTERVALO_HORAS (por defecto 8h).

Las credenciales se leen de variables de entorno (las inyecta docker-compose
desde el archivo .env). No usa run_local.py.
"""
import os
import time
import traceback

import main

INTERVALO_HORAS = float(os.environ.get("INTERVALO_HORAS", "8"))
INTERVALO_SEG = int(INTERVALO_HORAS * 3600)


def loop() -> None:
    print(f"[scheduler] Arrancando. Buscará cada {INTERVALO_HORAS} horas.", flush=True)
    while True:
        try:
            main.main()
        except Exception:
            # Un error en una corrida no debe matar el contenedor: log y seguir.
            print("[scheduler] Error en la corrida:", flush=True)
            traceback.print_exc()

        print(f"[scheduler] Durmiendo {INTERVALO_HORAS} horas hasta la próxima búsqueda.", flush=True)
        time.sleep(INTERVALO_SEG)


if __name__ == "__main__":
    loop()
