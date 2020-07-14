from settings import *


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'mysql',
        'USER': 'root',
        'PASSWORD': 'root',
        'HOST': '127.0.0.1',
        'PORT': '8877',
        'TEST': {'CHARSET': 'utf8mb4', 'COLLATION': 'utf8mb4_bin'},
    }
}
