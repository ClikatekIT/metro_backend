
import os

from pathlib import Path
from dotenv import load_dotenv
from decouple import config

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

GOOGLE_CREDENTIALS_PATH = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    os.path.join(os.path.dirname(__file__), "mineral-brand-445417-v2-fd4c4b38aa6b.json"),
)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CREDENTIALS_PATH

SECRET_KEY = config("SECRET_KEY", default="django-insecure-^5!i^3aa$k$q&=^-y%9@yqmk$-fy0#&udnlns*!=1lpoug5e3u")

DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="api.metrojobs.co.mz,localhost,127.0.0.1", cast=lambda v: [s.strip() for s in v.split(",")])

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
PAYPAL_MODE = "live"  # ou "live" para produção

MPESA_API_KEY = os.getenv("MPESA_API_KEY")
MPESA_PUBLIC_KEY = os.getenv("MPESA_PUBLIC_KEY")
MPESA_SERVICE_PROVIDER_CODE = os.getenv("MPESA_SERVICE_PROVIDER_CODE")
MPESA_URL = os.getenv("MPESA_PRODUTION_URL")

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET")

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = '/'

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# CORS_ALLOWED_ORIGINS = [
#     'http://localhost:3000',  # URL do seu projeto Next.js
# ]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://api.metrojobs.co.mz",
]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

CSRF_COOKIE_NAME = "csrftoken"
CSRF_COOKIE_SECURE = False  # Defina como True se estiver usando HTTPS
CSRF_COOKIE_HTTPONLY = False  # Certifique-se de que o cookie não está sendo bloqueado
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = False  # Defina como True se estiver usando HTTPS


CORS_ALLOW_HEADERS = [
    "content-type",
    "authorization",
    "accept",
    "origin",
    "user-agent",
    "X-CSRFToken",
    'x-requested-with',
]

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

SESSION_COOKIE_AGE = 14400
SESSION_EXPIRE_AT_BROWSER_CLOSE = False


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'social_django',
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    # 'django.middleware.common.CommonMiddleware',
    'curriculum',
    'carrier_guide',
    'entrevistas',
    'questions_personalidade',
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    # "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "metrojobs_django.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "metrojobs_django.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="metro"),
        "USER": config("DB_USER", default="metro"),
        "PASSWORD": config("DB_PASSWORD", default="metro_2024"),
        "HOST": config("DB_HOST", default="24.199.100.234"),
        "PORT": config("DB_PORT", default="5432"),
        "OPTIONS": {
            "connect_timeout": 300,
        },
    }
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'metro',  
#         'USER': 'postgres',  
#         'PASSWORD': 'Milaboss33',
#         'HOST': '127.0.0.1',
#         'PORT': '5432',
#         "OPTIONS": {
#             "connect_timeout": 300,  # Timeout de 10 segundos
#         },
#     }
# }
AUTH_USER_MODEL = "curriculum.User"


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
   # "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
     "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
       # "curriculum.renderers.PDFRenderer",  # Adicione o seu renderizador personalizado para PDF
    ),
}

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_TYPE_CLAIM": "token_type",
}

AUTHENTICATION_BACKENDS = [
    'social_core.backends.google.GoogleOAuth2',
    'django.contrib.auth.backends.ModelBackend',
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
