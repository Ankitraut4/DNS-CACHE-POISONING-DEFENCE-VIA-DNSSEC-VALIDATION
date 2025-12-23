FROM python:3.11-slim

WORKDIR /app

RUN pip install flask flask-cors

COPY index.html .
COPY server.py .

CMD ["python", "server.py"]
