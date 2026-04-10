FROM python:3.13-slim

WORKDIR /app

# Copy everything first (needed for editable install)
COPY . .

# Install deps and spaCy model during build (baked into image)
RUN pip install --no-cache-dir -e "." && \
    python -m spacy download en_core_web_lg

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
