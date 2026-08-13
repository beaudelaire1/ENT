from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
# La suite de tests s'exécute avec les réglages de production en intégration continue.
# Deux d'entre eux n'ont pourtant aucun sens sous `manage.py test`, où rien n'est servi
# à personne : ils sont neutralisés ici plutôt qu'un par un.
RUNNING_TESTS = "test" in sys.argv

# Commandes qui n'ouvrent aucune base. Elles s'exécutent pendant la construction de
# l'image Docker, avec DJANGO_DEBUG=false et sans DATABASE_URL — aucun secret de base
# n'existe encore à ce moment-là. Exiger la base ici ferait échouer la construction
# elle-même, bien avant qu'il soit question de servir quoi que ce soit.
DATABASE_FREE_COMMANDS = {"collectstatic", "generate_chime", "makemessages", "compilemessages"}
BUILDING_IMAGE = bool(DATABASE_FREE_COMMANDS.intersection(sys.argv))


def allowed_hosts(raw: list[str]) -> list[str]:
    """Le domaine configuré, et toujours `127.0.0.1` en plus — jamais à sa place.

    Le `HEALTHCHECK` de l'image sonde le conteneur en interne via
    `curl http://127.0.0.1:8000/healthz/`, un contrat fixe gravé dans le `Dockerfile`,
    indépendant de tout domaine. La valeur par défaut de `DJANGO_ALLOWED_HOSTS` couvrait
    ce cas — mais seulement tant que la variable restait absente : la poser sur un vrai
    domaine, comme l'exige toute mise en production, faisait disparaître `127.0.0.1` avec
    elle. Chaque sonde recevait alors un `DisallowedHost`, silencieusement jusqu'à ce
    qu'une alerte d'erreur existe pour le signaler — ce qui a motivé cette fonction.
    """
    return list({*raw, "127.0.0.1"})


ALLOWED_HOSTS = allowed_hosts(env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1"))
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")
CSP_EXTERNAL_MEDIA_SOURCES = env_list("CSP_EXTERNAL_MEDIA_SOURCES")
SITE_URL = os.getenv("SITE_URL", "http://localhost:8000").rstrip("/")

if not DEBUG and SECRET_KEY == "dev-only-insecure-key-change-me":
    raise ImproperlyConfigured("DJANGO_SECRET_KEY doit être défini par un secret long en production.")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "storages",
    "accounts",
    "core",
    "dashboard",
    "planner",
    "library",
    "formations",
    "sablier",
    "notifications",
]


def build_middleware(debug: bool) -> list[str]:
    """La pile de middlewares, dont WhiteNoise n'est monté qu'en production.

    WhiteNoise sert les fichiers déjà collectés dans STATIC_ROOT et court-circuite la vue
    de `staticfiles`. En développement il servait donc la copie figée de la dernière
    `collectstatic`, avec des en-têtes de cache longue durée : toute modification de CSS ou
    de JavaScript restait invisible dans le navigateur, sans erreur ni indice, et on
    cherchait la faute dans le code plutôt que dans le fichier servi.
    """
    return [
        "django.middleware.security.SecurityMiddleware",
        *([] if debug else ["whitenoise.middleware.WhiteNoiseMiddleware"]),
        "core.middleware.RequestIdMiddleware",
        "core.middleware.SecurityHeadersMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.locale.LocaleMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "accounts.middleware.UserTimezoneMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
    ]


MIDDLEWARE = build_middleware(DEBUG)

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.shell_context",
            ],
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


def database_from_url(url: str) -> dict[str, object]:
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("DATABASE_URL doit utiliser postgresql://")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "localhost",
        "PORT": parsed.port or 5432,
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }


def database_config(url: str | None, *, debug: bool, allow_fallback: bool = False) -> dict[str, object]:
    """La base à utiliser, et le refus de démarrer sans elle en production.

    Sans `DATABASE_URL`, le repli SQLite écrit dans `src/data/`, un répertoire créé par
    l'image mais monté sur aucun volume. Une variable oubliée donnait donc une
    application qui démarre, fonctionne, accepte des comptes — et perd tout au
    redéploiement suivant, sans qu'aucune erreur n'ait jamais été levée. Le repli reste
    le confort du développement local ; hors débogage, il est refusé comme l'est déjà
    une clé secrète laissée par défaut.
    """
    if url:
        return database_from_url(url)
    if not debug and not allow_fallback:
        raise ImproperlyConfigured(
            "DATABASE_URL PostgreSQL est obligatoire hors débogage : "
            "le repli SQLite n'est pas persisté et serait perdu au redéploiement."
        )
    (BASE_DIR / "data").mkdir(exist_ok=True)
    return {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "data" / "db.sqlite3"}


DATABASES = {
    "default": database_config(os.getenv("DATABASE_URL"), debug=DEBUG, allow_fallback=RUNNING_TESTS or BUILDING_IMAGE)
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# La suite de tests crée des comptes en permanence ; le hachage par défaut, volontairement
# coûteux, y domine le temps d'exécution sans rien protéger. Uniquement sous `manage.py test`.
if RUNNING_TESTS:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = os.getenv("TIME_ZONE", "America/Cayenne")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
# Emplacement interne du proxy pour la remise des fichiers privés (`X-Accel-Redirect`).
# Vide, Django sert les fichiers lui-même et occupe un worker pendant tout le transfert :
# acceptable en développement, coûteux dès qu'une piste audio est écoutée en entier.
# Cet emplacement doit être déclaré `internal` côté proxy, jamais exposé publiquement.
MEDIA_INTERNAL_LOCATION = os.getenv("MEDIA_INTERNAL_LOCATION", "")

USE_S3 = env_bool("USE_S3", False)
STORAGES = {
    "staticfiles": {
        # Le stockage à manifeste renomme chaque fichier avec l'empreinte de son contenu.
        # Sous les tests, cela rendrait `sablier/decor.js` sous la forme
        # `sablier/decor.5871027460a5.js` : les vérifications qui s'assurent qu'aucune
        # ressource n'est chargée depuis un CDN échouaient sur le nom, sans que rien ne
        # soit cassé. La suite dépendait en outre d'un `collectstatic` préalable.
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG or RUNNING_TESTS
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
}
if USE_S3:
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL")
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME")
    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = 900
    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage"}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "accounts:login"

EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if os.getenv("EMAIL_HOST")
    else "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "MyENT <noreply@localhost>")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def redis_database(url: str, index: int) -> str:
    """La même instance Redis, sur une autre base.

    Le cache et le courtier Celery partageaient la base 0. Un `cache.clear()` — ou un
    `FLUSHDB` passé à la main un jour de dépannage — effaçait donc la file des tâches en
    attente avec les compteurs de connexion. Deux bases séparées coûtent une ligne et
    rendent l'erreur impossible.
    """
    head, _, tail = url.rpartition("/")
    return f"{head}/{index}" if head and tail.isdigit() else f"{url.rstrip('/')}/{index}"


# Le cache porte le compteur de tentatives de connexion : il doit être partagé entre les
# processus gunicorn. Redis quand il est configuré, mémoire locale en développement.
if os.getenv("REDIS_URL"):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": redis_database(REDIS_URL, 1),
        }
    }
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "10"))
LOGIN_LOCKOUT_SECONDS = int(os.getenv("LOGIN_LOCKOUT_SECONDS", "900"))

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = None
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 120
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "dispatch-due-reminders-every-minute": {
        "task": "planner.dispatch_due_reminders",
        "schedule": 60.0,
    }
}

# Les tests exécutent les tâches sur place. L'intégration continue fournit un courtier
# mais aucun worker : `delay()` y réussissait, la tâche partait en file, et personne ne
# l'exécutait jamais — la réindexation et les rappels restaient en attente jusqu'à la fin
# du test. En local, sans courtier, `core.queue.enqueue` retombait sur une exécution
# immédiate et masquait précisément ce cas.
if RUNNING_TESTS:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

LIBRARY_MAX_UPLOAD_MB = int(os.getenv("LIBRARY_MAX_UPLOAD_MB", "25"))
AUDIO_MAX_TRACK_MB = int(os.getenv("AUDIO_MAX_TRACK_MB", "1024"))
AUDIO_DEFAULT_QUOTA_MB = int(os.getenv("AUDIO_DEFAULT_QUOTA_MB", "10240"))

# Un envoi volumineux est écrit sur disque plutôt que gardé en mémoire, sans quoi
# plusieurs téléversements simultanés suffiraient à saturer le conteneur.
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
# Ne concerne que les champs de formulaire hors fichiers : les pièces jointes ne sont
# pas comptées ici, la limite par piste s'en charge.
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


def optional_bool(raw: str | None) -> bool | None:
    """Un booléen à trois états : vrai, faux, ou « la variable n'a pas été posée »."""
    if raw is None or not raw.strip():
        return None
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def force_https(debug: bool, running_tests: bool, override: bool | None) -> bool:
    """HTTPS est exigé dès que possible — redirection, cookies, HSTS —, sauf exception explicite.

    `DEBUG` répond à une question — faut-il montrer les erreurs en détail ? — et gouvernait
    aussi une question sans rapport : ce déploiement reçoit-il vraiment du HTTPS ? Les deux
    coïncident presque toujours, mais pas dans la fenêtre où l'on teste derrière un nom sans
    certificat valable — un domaine généré par Coolify sur `sslip.io`, par exemple, que
    Coolify lui-même déconseille de certifier : le domaine est partagé par un grand nombre
    d'installations, et Let's Encrypt limite le nombre de certificats émis par domaine
    enregistré et par semaine. Forcer `DEBUG=true` pour lever la redirection ouvrirait alors
    les pages d'erreur détaillées de Django sur une adresse déjà publique — un risque bien
    plus large que celui qu'on cherchait à éviter.

    `DJANGO_FORCE_HTTPS`, explicitement posé, tranche la question sans toucher à `DEBUG`.
    Laissé absent, le comportement ne change pas : HTTPS reste exigé dès que `DEBUG` est
    faux, sauf sous les tests, où le client parle en clair et où la redirection court-
    circuiterait chaque requête avant qu'elle n'atteigne sa vue.
    """
    if override is not None:
        return override
    return not debug and not running_tests


FORCE_HTTPS = force_https(DEBUG, RUNNING_TESTS, optional_bool(os.getenv("DJANGO_FORCE_HTTPS")))
SECURE_SSL_REDIRECT = FORCE_HTTPS
SESSION_COOKIE_SECURE = FORCE_HTTPS
CSRF_COOKIE_SECURE = FORCE_HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_HSTS_SECONDS = 31536000 if FORCE_HTTPS else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = FORCE_HTTPS
SECURE_HSTS_PRELOAD = FORCE_HTTPS
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Une erreur serveur qui n'est vue de personne se répète. Sans dépendance externe, Django
# sait déjà écrire aux ADMINS ; le courriel n'est monté que si des destinataires existent
# et qu'un vrai serveur SMTP est configuré — sinon il finirait dans la console, où la
# trace complète est déjà écrite.
ADMINS = [(address.split("@")[0], address) for address in env_list("DJANGO_ADMINS")]
SERVER_EMAIL = os.getenv("SERVER_EMAIL", DEFAULT_FROM_EMAIL)
ALERT_BY_EMAIL = bool(ADMINS and EMAIL_HOST)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "{asctime} {levelname} {name} {message}", "style": "{"}},
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "plain"},
        "admins": (
            {"class": "django.utils.log.AdminEmailHandler", "level": "ERROR", "include_html": False}
            if ALERT_BY_EMAIL
            # `include_html` n'est pas un argument de NullHandler : le passer quand même
            # ferait échouer la configuration du journal au démarrage.
            else {"class": "logging.NullHandler"}
        ),
    },
    "root": {"handlers": ["console", "admins"], "level": os.getenv("LOG_LEVEL", "INFO")},
}
