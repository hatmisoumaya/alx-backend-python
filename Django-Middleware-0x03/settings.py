import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",

    "chats.middleware.RequestLoggingMiddleware",
    "chats.middleware.RestrictAccessByTimeMiddleware",
    "chats.middleware.OffensiveLanguageMiddleware",
    "chats.middleware.RolepermissionMiddleware",

    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "request_file": {
            "class": "logging.FileHandler",
            "filename": os.path.join(BASE_DIR, "requests.log"),
            "encoding": "utf-8",
        },
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {
        "request_logger": {
            "handlers": ["request_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
