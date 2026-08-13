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
# `/app/run` porte le calendrier de Celery beat. Il est créé et donné à `myent` ici, dans
# l'image : Docker recopie le propriétaire du répertoire de l'image quand il monte un
# volume nommé vide par-dessus. Sans cela le volume appartient à root, le conteneur
# tourne sous `myent`, et beat s'arrête sur « Permission denied » — en boucle, jusqu'à ce
# que l'orchestrateur déclare le déploiement en échec et démonte l'ensemble.
#
# Sous `/app` et non sous `/var/run` : ce dernier est un lien symbolique vers `/run` dans
# les images Debian, et un volume monté à travers un lien n'a pas un comportement évident.
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

# `exec` remplace le shell pour que gunicorn reçoive bien les signaux d'arrêt.
# Le délai par défaut de 60 s tuait le worker au milieu d'un téléversement volumineux :
# une piste de 1 Go met plusieurs minutes à monter sur une connexion domestique.
CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind=0.0.0.0:8000 --workers=3 --threads=2 --timeout=${GUNICORN_TIMEOUT:-900} --access-logfile=- --error-logfile=-"]

