"""
Helper para correr el bot en tu PC: lee un archivo .env y luego ejecuta main.
Uso:  python run_local.py
(En GitHub Actions NO se usa esto; ahí las variables vienen de los Secrets.)
"""
import os


def cargar_env(ruta=".env"):
    if not os.path.exists(ruta):
        print("No existe .env — copiá .env.example a .env y completalo.")
        return
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            os.environ[clave.strip()] = valor.strip()


if __name__ == "__main__":
    cargar_env()
    import main
    main.main()
