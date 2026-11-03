# Imagen para ejecutar los ejemplos sin instalar Python en tu computadora.
# Se usa con:  docker compose run --rm cliente python publicar.py

FROM python:3.13-slim

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "publicar.py"]
