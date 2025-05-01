import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
import API.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "WebApp.settings")
print("ASGI loaded, websocket ready.")
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(API.routing.websocket_urlpatterns)
    ),
})
