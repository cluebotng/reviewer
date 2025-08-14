import sys
from pathlib import Path

import prometheus_client

from cbng_reviewer.utils.config import load_config

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG = load_config(BASE_DIR)

SECRET_KEY = CONFIG["django"]["secret_key"]
DEBUG = CONFIG["django"]["debug"]

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django_prometheus",
    "social_django",
    "rest_framework",
    "django_bootstrap5",
    "cbng_reviewer",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "social_django.middleware.SocialAuthExceptionMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "cbng_reviewer.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
            ],
        },
    },
]

WSGI_APPLICATION = "cbng_reviewer.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": CONFIG["mysql"]["default"]["schema"],
        "HOST": CONFIG["mysql"]["default"]["host"],
        "PORT": CONFIG["mysql"]["default"]["port"],
        "USER": CONFIG["mysql"]["default"]["user"],
        "PASSWORD": CONFIG["mysql"]["default"]["password"],
        "OPTIONS": {"charset": "utf8mb4", "ssl_mode": "DISABLED"},
    },
    "replica": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": CONFIG["mysql"]["replica"]["schema"],
        "HOST": CONFIG["mysql"]["replica"]["host"],
        "PORT": CONFIG["mysql"]["replica"]["port"],
        "USER": CONFIG["mysql"]["replica"]["user"],
        "PASSWORD": CONFIG["mysql"]["replica"]["password"],
        "OPTIONS": {"charset": "utf8mb4", "ssl_mode": "DISABLED"},
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(asctime)s %(levelname)s %(filename)s %(funcName)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "": {"handlers": ["console"], "level": "INFO", "propagate": True, "stream": sys.stdout},
    },
}

SOCIAL_AUTH_MEDIAWIKI_KEY = CONFIG["oauth"]["key"]
SOCIAL_AUTH_MEDIAWIKI_SECRET = CONFIG["oauth"]["secret"]
SOCIAL_AUTH_MEDIAWIKI_URL = "https://meta.wikimedia.org/w/index.php"
SOCIAL_AUTH_MEDIAWIKI_CALLBACK = "oob"

AUTHENTICATION_BACKENDS = [
    "social_core.backends.mediawiki.MediaWiki",
]
AUTH_USER_MODEL = "cbng_reviewer.User"
LOGIN_URL = "/oauth/login/mediawiki/"
LOGIN_REDIRECT_URL = "/"
SOCIAL_AUTH_PROTECTED_USER_FIELDS = ["groups"]

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
}

BOOTSTRAP5 = {
    "css_url": {
        "url": "https://tools-static.wmflabs.org/cdnjs/ajax/libs/bootstrap/5.3.7/css/bootstrap.min.css",
        "crossorigin": "anonymous",
    },
    "javascript_url": {
        "url": "https://tools-static.wmflabs.org/cdnjs/ajax/libs/bootstrap/5.3.7/js/bootstrap.bundle.min.js",
        "crossorigin": "anonymous",
    },
}

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

WIKIPEDIA_USERNAME = CONFIG["wikipedia"]["username"]
WIKIPEDIA_PASSWORD = CONFIG["wikipedia"]["password"]

WIKIPEDIA_NAMESPACE_NAME_TO_ID = {
    "special": -1,
    "media": -2,
    "main": 0,
    "talk": 1,
    "user": 2,
    "user talk": 3,
    "wikipedia": 4,
    "wikipedia talk": 5,
    "file": 6,
    "file talk": 7,
    "mediawiki": 8,
    "mediawiki talk": 9,
    "template": 10,
    "template talk": 11,
    "help": 12,
    "help talk": 13,
    "category": 14,
    "category talk": 15,
    "portal": 100,
    "portal talk": 101,
    "book": 108,
    "book talk": 109,
    "draft": 118,
    "draft talk": 119,
    "timedtext": 710,
    "timedtext talk": 711,
    "module": 828,
    "module talk": 829,
    "gadget": 2300,
    "gadget talk": 2301,
    "gadget definition": 2302,
    "gadget definition talk": 2303,
}
WIKIPEDIA_NAMESPACE_ID_TO_NAME = {v: k for k, v in WIKIPEDIA_NAMESPACE_NAME_TO_ID.items()}

IRC_RELAY_HOST = CONFIG["irc_relay"]["host"]
IRC_RELAY_PORT = CONFIG["irc_relay"]["port"]
IRC_RELAY_CHANNEL = CONFIG["irc_relay"]["channel"]

REDIS_HOST = CONFIG["redis"]["host"]
REDIS_PORT = CONFIG["redis"]["port"]
REDIS_DB = CONFIG["redis"]["db"]
REDIS_PASSWORD = CONFIG["redis"]["password"]

CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_BROKER_URL = (
    f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    if REDIS_PASSWORD
    else f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
)

CBNG_MINIMUM_CLASSIFICATIONS_FOR_EDIT = 2
CBNG_MINIMUM_EDITS_FOR_USER_ACCURACY = 20
CBNG_CLEANUP_USER_DAYS = 30
CBNG_RECENT_EDIT_WINDOW_DAYS = 14
CBNG_SAMPLED_EDITS_QUANTITY = 1  # An edit a day keeps the daemons at bay
CBNG_SAMPLED_EDITS_LOOKBACK_DAYS = 7
CBNG_SAMPLED_EDITS_EDIT_SET = "Sampled Main Namespace Edits"
CBNG_REPORT_EDIT_SET = "Report Interface Import"
CBNG_ADMIN_ONLY = CONFIG["cbng"]["admin_only"]
CBNG_ENABLE_IRC_MESSAGING = CONFIG["cbng"]["enable_irc_messaging"]
CBNG_ENABLE_USER_MESSAGING = CONFIG["cbng"]["enable_user_messaging"]

# No default metrics
PROMETHEUS_METRIC_NAMESPACE = "cbng_reviewer"
prometheus_client.REGISTRY.unregister(prometheus_client.GC_COLLECTOR)
prometheus_client.REGISTRY.unregister(prometheus_client.PLATFORM_COLLECTOR)
prometheus_client.REGISTRY.unregister(prometheus_client.PROCESS_COLLECTOR)
