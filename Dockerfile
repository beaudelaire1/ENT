FROM node:22-alpine AS visual-runtime
WORKDIR /visual
COPY package.json ./
COPY tools/vendor-three.mjs ./tools/vendor-three.mjs
RUN npm install --ignore-scripts --no-audit --no-fund \
    && npm run vendor \
    && mkdir -p /vendor \
    && cp -R src/static/vendor/. /vendor/

FROM python:3.12.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_DEBUG=false

RUN apt-get update \
    && apt-get install --no-install-recommends -y curl postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=visual-runtime /vendor/ /app/src/static/vendor/
RUN mkdir -p /app/src/data /app/src/media /app/src/staticfiles /app/run \
    && python src/manage.py generate_chime \
    && python src/manage.py collectstatic --noinput \
    && addgroup --system myent \
    && adduser --system --ingroup myent --home /app myent \
    && chown -R myent:myent /app/src/data /app/src/media /app/src/staticfiles /app/run

USER myent
WORKDIR /app/src
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:8000/healthz/ || exit 1

CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind=0.0.0.0:8000 --workers=3 --threads=2 --timeout=${GUNICORN_TIMEOUT:-900} --access-logfile=- --error-logfile=-"]
