from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync


class JsonWebsocketConsumer(JsonWebsocketConsumer):
    def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            print("User non authentifie")
            self.close()
        else:
            print("User authentifie")
            self.accept()
            self.group_name = f"private_channel_{str(user.id)}"
            async_to_sync(self.channel_layer.group_add)(
                self.group_name, self.channel_name
            )

    def notification(self, event):
        self.send_json(
            {
                "data": event.get("data"),
                "type": event.get("type"),
            }
        )

    def stat_data(self, event):
        print(f"Le statistic a ete envoyer avec {event}")
        self.send_json({"type": "stat_data", "data": event.get("data")})

    def disconnect(self, code):
        print("User est deconnecter")
        user = self.scope["user"]
        if not user.is_authenticated:
            self.close()
        else:
            async_to_sync(self.channel_layer.group_discard)(
                self.group_name, self.channel_name
            )
