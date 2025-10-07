# ---- build stage ----
FROM python:3.11.9-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# ---- runtime ----
FROM python:3.11.9-slim
WORKDIR /app
ENV PORT=9009

# add a non-root user
RUN useradd -m appuser
USER appuser

COPY --chown=appuser:appuser . /app

# artifacts survive in mounted volume if provided
VOLUME ["/app/artifacts"]

EXPOSE 9009
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9009"]
