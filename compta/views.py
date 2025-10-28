import json
import os
import requests
from rest_framework import decorators, permissions, status, generics
from rest_framework.response import Response
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from datetime import time, datetime
from django.contrib.auth.models import User

from pusher import Pusher
from compta.models import APIBalanceUpdate, APITransaction, MobCashApp, MobCashAppBalanceUpdate, Transaction, UserTransactionFilter
from compta.serializers import APITransactionSerializer, MobCashAppSerializer, PusherAuthSerializer, TransactionSerializer, UserTransactionFilterSerializer
from compta.services.filter_service import FilterService
from compta.services.balance_service import BalanceService
from compta.services.stats_services import StatsService
from compta.services.transaction_service import TransactionService
from django.utils import timezone
from celery import shared_task
pusher_client = Pusher(
    app_id=os.getenv("PUSER_ID"),
    key=os.getenv("PUSHER_KEY"),
    secret=os.getenv("PUSHER_SECRET"),
    cluster="eu",
    ssl=False,
)
class ComptatView(decorators.APIView):
    """
    Vue principale pour récupérer les statistiques de comptabilité

    Logique :
    - Si des filtres sont envoyés → les utiliser
    - Si aucun filtre envoyé → charger le dernier filtre sauvegardé
    - Si is_all_date = True → ignorer start_date et end_date
    - Si start_date est null → prendre la date d'aujourd'hui
    """

    permission_classes = [permissions.IsAdminUser]

    def get(self, request, *args, **kwargs):
        # 1. Parser les filtres
        filters = FilterService.parse_filters_from_request(request)

        # 2. Gérer is_all_date (toutes les dates depuis la création)
        if filters.get("is_all_date"):
            filters["start_date"] = None
            filters["end_date"] = None

        # 3. Récupérer et filtrer les transactions
        transactions = TransactionService.get_all_transactions()
        transactions = FilterService.apply_filters(transactions, filters)

        # 4. Calculer les agrégats
        aggregates = TransactionService.get_transaction_aggregates(transactions)

        # 5. Calculer les balances actuelles (pas de période)
        balances = BalanceService.get_all_balances()

        # 6. Calculer les stats
        stats = StatsService.get_all_stats(transactions)

        # 7. Sauvegarder le filtre
        FilterService.save_user_filter(request.user, filters)

        # 8. Construire la réponse
        data = {
            "filters": {
                "start_date": filters.get("start_date"),
                "end_date": filters.get("end_date"),
                "last": filters.get("last"),
                "is_all_date": filters.get("is_all_date", False),
                "source": filters.get("source", []),
                "network": filters.get("network", []),
                "api": filters.get("api", []),
                "mobcash": filters.get("mobcash", []),
                "type": filters.get("type", []),
            },
            "total": aggregates["total"],
            "mobcash_fee": aggregates["mobcash_fee"],
            "blaffa_fee": aggregates["blaffa_fee"],
            "amount": aggregates["amount"],
            "mobcash_stats": stats["mobcash_stats"],
            "api_stats": stats["api_stats"],
            "network_stats": stats["network_stats"],
            "source_stats": stats["source_stats"],
            "type_stats": stats["type_stats"],
            "balances": balances,
        }

        return Response(data)

from decimal import Decimal
from datetime import datetime, date

class DecimalEncoder(json.JSONEncoder):
    """Encoder personnalisé pour gérer Decimal, datetime, etc."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def send_stats_to_user():
    """
    Envoie les stats en temps réel via WebSocket
    Utilise le dernier filtre de l'utilisateur
    """
    try:
        # Récupérer le premier utilisateur (à adapter selon ton besoin)
        user = User.objects.first()
        if not user:
            return

        # Charger le dernier filtre de l'utilisateur
        filters = FilterService.load_user_last_filter(user)
        filters = FilterService.process_dates(filters)

        # Gérer is_all_date
        if filters.get("is_all_date"):
            filters["start_date"] = None
            filters["end_date"] = None
        # Sinon, si start_date est null, prendre aujourd'hui
        elif not filters.get("start_date"):
            from django.utils import timezone

            filters["start_date"] = timezone.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        # Récupérer et filtrer les transactions
        transactions = TransactionService.get_all_transactions()
        transactions = FilterService.apply_filters(transactions, filters)

        # Calculer les agrégats, balances et stats
        aggregates = TransactionService.get_transaction_aggregates(transactions)
        balances = BalanceService.get_all_balances()
        stats = StatsService.get_all_stats(transactions)

        # Préparer les données
        stats_payload = {
            "filters": {
                "start_date": (
                    filters.get("start_date").isoformat()
                    if filters.get("start_date")
                    else None
                ),
                "end_date": (
                    filters.get("end_date").isoformat()
                    if filters.get("end_date")
                    else None
                ),
                "last": filters.get("last"),
                "is_all_date": filters.get("is_all_date", False),
                "source": filters.get("source", []),
                "network": filters.get("network", []),
                "api": filters.get("api", []),
                "mobcash": filters.get("mobcash", []),
                "type": filters.get("type", []),
            },
            "total": aggregates.get("total"),
            "mobcash_fee": aggregates.get("mobcash_fee"),
            "blaffa_fee": aggregates.get("blaffa_fee"),
            "amount": aggregates.get("amount"),
            "mobcash_stats": stats.get("mobcash_stats"),
            "api_stats": stats.get("api_stats"),
            "network_stats": stats.get("network_stats"),
            "source_stats": stats.get("source_stats"),
            "type_stats": stats.get("type_stats"),
            "balances": balances,
        }

        # Construire le message avec JSON encoder personnalisé
        data = {
            "type": "stats_update",
            "context": "user_filter",
            "data": json.dumps(stats_payload, cls=DecimalEncoder),  # ← CLEF ICI
        }

        # Envoyer via WebSocket
        response = {}
        message = "1111111111111111111"
        pusher_client.trigger(
            f"private-channel_1",
            "stat_data",
            data,
        )
        message2 = "222222222222222222"
        return {"message": message, "message2": message2}
    except Exception as e:
        # Log l'erreur (à adapter selon ton système de logging)
        print(f"Erreur send_stats_to_user: {e}")
        return str(e)


def send_telegram_message(chat_id, content):
    bot_token = os.getenv("TOKEN_BOT")
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    data = {
        "chat_id": chat_id,
        "text": content,
    }
    try:

        response = requests.post(api_url, data=data)
        return response.json()
    except:
        return None


@shared_task
def update_all_balance_process(transaction_id):
    get_api_balance()
    update_mobcash_balance(transaction=Transaction.objects.get(id=transaction_id))
    send_stats_to_user()


class CreateTransaction(decorators.APIView):
    def post(self, request, *args, **kwargs):
        serializer = TransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transaction = serializer.save()
        update_all_balance_process.delay(transaction.id)
        return Response(TransactionSerializer(transaction).data)


class UserTransactionFilterView(decorators.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        filter_obj, created = UserTransactionFilter.objects.get_or_create(user=user)
        serializer = UserTransactionFilterSerializer(filter_obj)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResetUserTransactionFilterView(decorators.APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, *args, **kwargs):
        today = timezone.localtime().date()

        defaults = {
            "last": None,
            "start_date": None,
            "end_date": None,
            "source": [],
            "network": [],
            "api": [],
            "type": [],
            "mobcash": [],
            "is_all_date": True,
            "periode": None,
        }
        filter_obj, created = UserTransactionFilter.objects.update_or_create(
            user=request.user, defaults=defaults
        )
        return Response(
            UserTransactionFilterSerializer(filter_obj).data, status=status.HTTP_200_OK
        )


class MobCashAppListView(generics.ListAPIView):
    queryset = MobCashApp.objects.all()
    serializer_class = MobCashAppSerializer
    permission_classes = [permissions.IsAdminUser]


class MobCashAppUpdateView(generics.RetrieveUpdateAPIView):
    queryset = MobCashApp.objects.all()
    serializer_class = MobCashAppSerializer
    permission_classes = [permissions.IsAdminUser]


class APITransactionListView(generics.ListAPIView):
    queryset = APITransaction.objects.all()
    serializer_class = APITransactionSerializer
    permission_classes = [permissions.IsAdminUser]


class APITransactionUpdateView(generics.RetrieveUpdateAPIView):
    queryset = APITransaction.objects.all()
    serializer_class = APITransactionSerializer
    permission_classes = [permissions.IsAdminUser]


def get_api_balance():
    url = "https://api.blaffa.net/blaffa/balance"
    headers = {
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url=url, headers=headers)
        response.raise_for_status()
        data = response.json()

        for api in APITransaction.objects.all():
            api_name = api.name.lower()

            if api_name in data:
                balance_data = data[api_name]

                # Ignorer les valeurs invalides ou en erreur
                if isinstance(balance_data, (int, float, str)):
                    try:
                        balance = float(balance_data)
                        api.balance = balance
                        api.save()

                        # Créer un enregistrement historique
                        APIBalanceUpdate.objects.create(
                            api_transaction=api, balance=balance
                        )

                    except ValueError:
                        # Si balance_data n’est pas convertible en float
                        continue

        return data
    
    except Exception as e:
        return {"error": str(e)}


def get_mobcash_balance():
    url = "https://api.blaffa.net/blaffa/mobcash-balance"
    headers = {
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url=url, headers=headers)
        response.raise_for_status()
        balances = response.json()  
        balance_dict = {
            item["app_name"].lower(): item["solde"]
            for item in balances
            if "app_name" in item and "solde" in item
        }

        for mobcash in MobCashApp.objects.all():
            app_name = mobcash.name.lower()

            if app_name in balance_dict:
                balance_value = balance_dict[app_name]

                try:
                    balance = float(balance_value)
                    mobcash.balance = balance
                    mobcash.save()

                    MobCashAppBalanceUpdate.objects.create(
                        mobcash_balance=mobcash, balance=balance
                    )

                except (ValueError, TypeError):
                    # Balance invalide ou non convertible
                    continue

        return balance_dict

    except Exception as e:
        return {"error": str(e)}


class APIBalanceView(decorators.APIView):
    permission_classes = [permissions.IsAdminUser]
    def get(self, request, *args, **kwargs):
        return Response(get_api_balance())


class MobCashBalance(decorators.APIView):
    permission_classes = [permissions.IsAdminUser]
    def get(self, request, *args, **kwargs):
        return Response(get_mobcash_balance())

class TestView(decorators.APIView):
    def post(self, request, *args, **kwargs):
        from compta.tasks import send_compta_summary
        response = send_compta_summary()
        return Response({"response": response})


class AuthenPusherUser(decorators.APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, *args, **kwargs):
        serializer = PusherAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        socket_id = serializer.validated_data["socket_id"]
        channel_name = f"private-channel_{request.user.id}"
        if not channel_name:
            return Response({"erreur": "Aucun channel trouvé"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            if channel_name.startswith("private"):
                auth = pusher_client.authenticate(channel=channel_name, socket_id=socket_id)
            else:
                auth = pusher_client.authenticate(
                    channel=channel_name,
                    socket_id=socket_id,
                    custom_data={
                        "user_id": request.user.id,
                        "user_info": {"username": request.user.username, "email": request.user.email},
                    },
                )
        except Exception as e:
            return Response({"erreur": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(auth, status=status.HTTP_200_OK)


def update_api_transaction_balance(transaction:Transaction):

    api_balance = transaction.api_balance
    if api_balance is None or api_balance == 0:
        return
    api_balance_instance = APITransaction.objects.filter(name=transaction.api).first()
    api_balance_instance.balance=api_balance
    api_balance_instance.save()
    APIBalanceUpdate.objects.create(
        api_transaction=api_balance_instance, balance=api_balance
    )


def update_mobcash_balance(transaction: Transaction):
    mobcash_balance = transaction.mobcash_balance
    if mobcash_balance is None or mobcash_balance==0:
        return
    mobcash_balance_instance = MobCashApp.objects.filter(
        name=transaction.mobcash
    ).first()
    mobcash_balance_instance.balance = mobcash_balance
    mobcash_balance_instance.save()
    MobCashAppBalanceUpdate.objects.create(
        mobcash_balance=mobcash_balance_instance, balance=mobcash_balance
    )
