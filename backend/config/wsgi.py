"""
WSGI config for Weather-Aware Truck Routing.
Vercel Python looks for either `application` or `app`.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
app = application  # Vercel entry alias
