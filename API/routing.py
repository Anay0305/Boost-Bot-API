from django.urls import path
from .consumer import BoostConsumer

websocket_urlpatterns = [
    path("ws/api/", BoostConsumer.as_asgi()),
]
