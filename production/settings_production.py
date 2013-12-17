# Django settings for mystrade project.
from settings import * # take standard settings and override

###### PRODUCTION #####

DEBUG = False
TEMPLATE_DEBUG = DEBUG

# Required when DEBUG is False, ie in production, to prevent "host-poisoning attacks".
ALLOWED_HOSTS = [
    'mystrade.alwaysdata.net',
    '.mystra.de', # prefix with dot to allow domain and subdomains
]

ADMINS = (
    ('Emmanuel', 'emmanuel.bizieau@gmail.com'),
)

MANAGERS = ADMINS

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.alwaysdata.com'
EMAIL_PORT = 25
EMAIL_HOST_USER = 'mystrade@alwaysdata.net'
EMAIL_HOST_PASSWORD = 'alrolandxp80'
EMAIL_USE_TLS = True
EMAIL_SUBJECT_PREFIX = '[MysTrade] ' # for admins

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'mystrade_db',
        'USER': 'mystrade',
        'PASSWORD': 'alrolandxp80',
        'HOST': 'postgresql1.alwaysdata.com',
    }
}

STATIC_ROOT = os.path.join(SITE_ROOT, "..", "public", "static")

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.BrokenLinkEmailsMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'mystrade.middlewares.TimezoneMiddleware', # after AuthenticationMiddleware !
    'mystrade.middlewares.OnlineStatusMiddleware', # after AuthenticationMiddleware !
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

INSTALLED_APPS = (
     'django.contrib.auth',
     'django.contrib.contenttypes',
     'django.contrib.sessions',
     #'django.contrib.sites',
     'django.contrib.messages',
     'django.contrib.staticfiles',
     'django.contrib.admin',
     'django.contrib.admindocs',
     'django.contrib.humanize',
     'widget_tweaks',
     'django_extensions',
     #'debug_toolbar',
     'south',
) + MYSTRADE_APPS

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(levelname)s %(asctime)s %(name)s %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console':{
            'level': 'ERROR',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'game': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
        },
        'trade': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
        },
    }
}
