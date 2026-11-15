FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PAYOPS_DB=/app/runtime/payops.sqlite3
COPY requirements.txt requirements.lock ./
RUN --mount=type=cache,target=/root/.cache/pip --mount=type=bind,source=.,target=/build,readonly \
    if [ -d /build/.wheelhouse ]; then \
      pip install --no-index --find-links=/build/.wheelhouse -r requirements.lock; \
    else pip install --timeout 120 --retries 5 -r requirements.lock; fi
COPY backend ./backend
COPY data ./data
COPY scripts ./scripts
COPY tests ./tests
COPY pytest.ini ./
COPY Dockerfile compose.yaml Makefile .dockerignore ./
COPY frontend/nginx.conf ./frontend/nginx.conf
RUN mkdir -p /app/runtime /app/reports && useradd --create-home payops && chown -R payops:payops /app
USER payops
EXPOSE 8000
CMD ["sh", "-c", "python -m backend.demo && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
