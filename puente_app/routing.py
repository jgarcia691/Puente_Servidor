from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/puente_app/$', consumers.PuenteConsumer.as_asgi()),
] 