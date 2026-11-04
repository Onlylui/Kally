FROM python:3.12-slim

WORKDIR /app

# Primeiro só as dependências: o Docker reaproveita esta camada quando só o código muda.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY migrations/ migrations/
COPY tests/ tests/
COPY pytest.ini .

CMD ["python", "-m", "app.main"]
