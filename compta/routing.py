from django.urls import path

from compta import consumer


websocket_urlpatterns = [
    path('ws/socket', consumer.JsonWebsocketConsumer.as_asgi()),
]
