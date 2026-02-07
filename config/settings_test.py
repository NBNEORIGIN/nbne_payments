from .settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

STRIPE_SECRET_KEY = 'sk_test_fake_key_for_testing'
STRIPE_WEBHOOK_SECRET = 'whsec_fake_secret_for_testing'
PAYMENTS_ENABLED = True
