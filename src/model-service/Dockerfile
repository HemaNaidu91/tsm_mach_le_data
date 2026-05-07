FROM python:3.12-slim

ARG MODEL_SERVICE_EXTRA=cpu

ENV HOST=0.0.0.0 \
    PORT=8001 \
    MODEL_SERVICE_ARTIFACT_CACHE_DIR=/app/artifacts \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN python -m pip install --no-cache-dir --upgrade pip uv

COPY pyproject.toml ./
RUN uv pip install --system --no-cache -r pyproject.toml --extra "${MODEL_SERVICE_EXTRA}"

RUN addgroup --system app \
    && adduser --system --home /app --ingroup app app \
    && mkdir -p /app/artifacts \
    && chown -R app:app /app


COPY --chown=app:app *.py ./
COPY . .

USER app

EXPOSE 8001

CMD ["python", "model-service.py"]
