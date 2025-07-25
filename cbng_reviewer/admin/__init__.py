from django.apps import apps
from django.contrib import admin
from django.contrib.admin.exceptions import AlreadyRegistered

# Django tries to load `admin.py`, we want to use that directory so handle the logic here
for model in apps.get_models():
    try:
        admin.site.register(model)
    except AlreadyRegistered:
        pass
