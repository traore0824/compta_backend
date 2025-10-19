import os
import requests
from rest_framework import decorators, permissions, status, generics
from rest_framework.response import Response
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import User

from compta.models import APIBalanceUpdate, APITransaction, MobCashApp, MobCashAppBalanceUpdate, UserTransactionFilter
from compta.serializers import APITransactionSerializer, MobCashAppSerializer, TransactionSerializer, UserTransactionFilterSerializer
from compta.services.filter_service import FilterService
from compta.services.balance_service import BalanceService
from compta.services.stats_services import StatsService
from compta.services.transaction_service import TransactionService


class ComptatView(decorators.APIView):
    """
    Vue principale pour récupérer les statistiques de comptabilité

    Logique :
    - Si des filtres sont envoyés → les utiliser
    - Si aucun filtre envoyé → charger le dernier filtre sauvegardé
    - Si start_date est null → prendre la date d'aujourd'hui
    """

    permission_classes = [permissions.IsAdminUser]

    def get(self, request, *args, **kwargs):
        # 1. Parser les filtres
        filters = FilterService.parse_filters_from_request(request)
        
        # 2. Récupérer et filtrer les transactions
        transactions = TransactionService.get_all_transactions()
        transactions = FilterService.apply_filters(transactions, filters)
        
        # 3. Calculer les agrégats
        aggregates = TransactionService.get_transaction_aggregates(transactions)
        
        # 4. Calculer les balances
        balances = BalanceService.get_all_balances(
            filters.get('start_date'),
            filters.get('end_date')
        )
        
        # 5. Calculer les stats
        stats = StatsService.get_all_stats(transactions)
        
        # 6. Sauvegarder le filtre
        FilterService.save_user_filter(request.user, filters)
        
        # 7. Construire la réponse (FORMAT EXACT comme avant)
        data = {
            "filters": {
                "start_date": filters.get('start_date'),
                "end_date": filters.get('end_date'),
                "last": filters.get('last'),
                "source": filters.get('source', []),
                "network": filters.get('network', []),
                "api": filters.get('api', []),
                "mobcash": filters.get('mobcash', []),
                "type": filters.get('type', []),
            },
            "total": aggregates['total'],
            "mobcash_fee": aggregates['mobcash_fee'],
            "blaffa_fee": aggregates['blaffa_fee'],
            "amount": aggregates['amount'],
            "mobcash_stats": stats['mobcash_stats'],
            "api_stats": stats['api_stats'],
            "network_stats": stats['network_stats'],
            "source_stats": stats['source_stats'],
            "type_stats": stats['type_stats'],
            "balances": balances,
        }
        
        return Response(data)


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

        # Si start_date est null, prendre aujourd'hui
        if not filters.get("start_date"):
            from django.utils import timezone

            filters["start_date"] = timezone.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        # Récupérer et filtrer les transactions
        transactions = TransactionService.get_all_transactions()
        transactions = FilterService.apply_filters(transactions, filters)

        # Calculer les agrégats et balances
        aggregates = TransactionService.get_transaction_aggregates(transactions)
        balances = BalanceService.get_all_balances(
            filters.get("start_date"), filters.get("end_date")
        )

        # Construire le message stats
        stats = {
            "type": "stats_update",
            "context": "user_filter",
            "data": {
                **aggregates,
                "balances": balances,
            },
        }

        # Envoyer via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{user.id}_channel",
            {"type": "stat_data", "message": stats},
        )
    except Exception as e:
        # Log l'erreur (à adapter selon ton système de logging)
        print(f"Erreur send_stats_to_user: {e}")


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


class CreateTransaction(decorators.APIView):
    def post(self, request, *args, **kwargs):
        serializer = TransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transaction = serializer.save()
        send_stats_to_user()
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
        defaults = {
            "last": None,
            "start_date": None,
            "end_date": None,
            "source": None,
            "network": None,
            "api": None,
            "type": None,
            "mobcash": None,
        }
        filter_obj, created = UserTransactionFilter.objects.update_or_create(
            user=request.user, defaults=defaults
        )
        return Response(UserTransactionFilterSerializer(filter_obj).data, status=status.HTTP_200_OK)


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
