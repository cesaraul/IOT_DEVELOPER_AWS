FROM python:3.12-slim
# Lo único que hace falta: boto3 para leer tu cuenta. Nada de framework
# web — el servidor son doscientas líneas de la biblioteca estándar.
RUN pip install --no-cache-dir boto3
WORKDIR /srv
CMD ["python", "-u", "servidor.py"]
