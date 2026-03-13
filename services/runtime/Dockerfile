FROM python:3.13-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY services/runtime/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/runtime/alembic.ini /app/alembic.ini
COPY services/runtime/alembic /app/alembic
COPY services/runtime/app /app/app
RUN find /app -type d -name __pycache__ -prune -exec rm -rf {} + \
    && find /app -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
