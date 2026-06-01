FROM python:3.11-slim

# Logs sin buffer para verlos en tiempo real con `docker logs`
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias primero (mejor cacheo de capas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código
COPY . .

# Corre el planificador: busca al arrancar y luego cada INTERVALO_HORAS (8 por defecto)
CMD ["python", "scheduler.py"]
