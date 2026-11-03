FROM python:3.13-slim

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY dispositivo.py .

CMD ["python", "-u", "dispositivo.py"]
