import os
import django
from django.core.asgi import get_asgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'compta_backend.settings')
application = get_asgi_application()

django.setup()
from django_channels_jwt_auth_middleware.auth import JWTAuthMiddlewareStack
from channels.auth import AuthMiddlewareStack
from channels.routing import URLRouter, ProtocolTypeRouter
from compta import routing

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": JWTAuthMiddlewareStack(
            URLRouter(routing.websocket_urlpatterns),
        ),
    }
)
