"""
ASGI config for puente_sistema project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'puente_server.settings')

def get_websocket_urlpatterns():
    from puente_app.routing import websocket_urlpatterns
    return websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter(
        get_websocket_urlpatterns()
    ),
})
