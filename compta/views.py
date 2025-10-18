import os
import requests
from rest_framework import decorators, permissions, status, generics
from django.utils.dateparse import parse_datetime, parse_date
from compta.models import (
    API_CHOICES,
    NETWORK_CHOICES,
    SOURCE_CHOICES,
    TYPE_CHOICES,
    APIBalanceUpdate,
    APITransaction,
    MobCashApp,
    MobCashAppBalanceUpdate,
    Transaction,
    UserTransactionFilter,
)
from django.utils import timezone
from django.db.models import Sum
from typing import List
from rest_framework.response import Response
from datetime import timedelta
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from compta.serializers import (
    APITransactionSerializer,
    MobCashAppSerializer,
    TransactionSerializer,
    UserTransactionFilterSerializer,
)
from django.contrib.auth.models import User
from django.utils.formats import number_format


class ComptatView(decorators.APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, *args, **kwargs):
        transactions = Transaction.objects.all().order_by("-created_at")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        last = request.GET.get("last")

        # Récupération des filtres en listes
        source_list = request.GET.getlist("source")
        network_list = request.GET.getlist("network")
        api_list = request.GET.getlist("api")
        type_list = request.GET.getlist("type")
        mobcash_list = request.GET.getlist("mobcash")

        now = timezone.now()
        if last:
            if last == "yesterday":
                start_date = now - timedelta(days=1)
                end_date = now
            elif last == "3_days":
                start_date = now - timedelta(days=3)
            elif last == "7_days":
                start_date = now - timedelta(days=7)
            elif last == "30_days":
                start_date = now - timedelta(days=30)
            elif last == "1_year":
                start_date = now - timedelta(days=365)
            elif last in ["always", "all"]:
                start_date = None
                end_date = None
        else:
            if not start_date:
                start_date = None  # Par défaut pas de date actuelle

        if start_date and isinstance(start_date, str):
            start_date = parse_datetime(start_date)
        if end_date and isinstance(end_date, str):
            end_date = parse_datetime(end_date)

        if start_date:
            transactions = transactions.filter(created_at__gte=start_date)
        if end_date:
            transactions = transactions.filter(created_at__lte=end_date)
        if source_list:
            transactions = transactions.filter(source__in=source_list)
        if network_list:
            transactions = transactions.filter(network__in=network_list)
        if api_list:
            transactions = transactions.filter(api__in=api_list)
        if mobcash_list:
            transactions = transactions.filter(mobcash__in=mobcash_list)
        if type_list:
            transactions = transactions.filter(type__in=type_list)

        # --- Calcul des soldes ---

        api_balances = {}
        for api_obj in APITransaction.objects.all():
            name = api_obj.name
            balance_updates = APIBalanceUpdate.objects.filter(api_transaction=api_obj)

            if start_date and end_date:
                updates_in_period = balance_updates.filter(
                    created_at__gte=start_date, created_at__lte=end_date
                )
            elif start_date and not end_date:
                updates_in_period = balance_updates.filter(created_at__gte=start_date)
            else:
                updates_in_period = balance_updates.none()

            if updates_in_period.exists():
                last_update = updates_in_period.order_by("-created_at").first()
                balance = last_update.balance
            elif start_date:
                last_update_before = (
                    balance_updates.filter(created_at__lt=start_date)
                    .order_by("-created_at")
                    .first()
                )
                if last_update_before:
                    balance = last_update_before.balance
                else:
                    balance = api_obj.balance
            else:
                balance = api_obj.balance
            api_balances[name] = balance

        mobcash_balances = {}
        for mobcash_obj in MobCashApp.objects.all():
            name = mobcash_obj.name
            balance_updates = MobCashAppBalanceUpdate.objects.filter(
                mobcash_balance=mobcash_obj
            )

            if start_date and end_date:
                updates_in_period = balance_updates.filter(
                    created_at__gte=start_date, created_at__lte=end_date
                )
            elif start_date and not end_date:
                updates_in_period = balance_updates.filter(created_at__gte=start_date)
            else:
                updates_in_period = balance_updates.none()

            if updates_in_period.exists():
                last_update = updates_in_period.order_by("-created_at").first()
                balance = last_update.balance
            elif start_date:
                last_update_before = (
                    balance_updates.filter(created_at__lt=start_date)
                    .order_by("-created_at")
                    .first()
                )
                if last_update_before:
                    balance = last_update_before.balance
                else:
                    balance = mobcash_obj.balance
            else:
                balance = mobcash_obj.balance
            mobcash_balances[name] = balance

        total_api_balance = sum(api_balances.values())
        total_mobcash_balance = sum(mobcash_balances.values())
        # total_api_balance = (
        #     APITransaction.objects.all().aggregate(total=Sum("balance"))["total"] or 0
        # )
        # total_mobcash_balance = MobCashApp.objects.all().aggregate(
        #     total=Sum("balance")
        # )["total"]  or 0
        total_balance = total_api_balance + total_mobcash_balance

        data = {
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "last": last,
                "source": source_list,
                "network": network_list,
                "api": api_list,
                "mobcash": mobcash_list,
                "type": type_list,
            },
            "total": transactions.count(),
            "mobcash_fee": transactions.aggregate(total=Sum("mobcash_fee"))["total"]
            or 0,
            "blaffa_fee": transactions.aggregate(total=Sum("blaffa_fee"))["total"] or 0,
            "amount": transactions.aggregate(total=Sum("amount"))["total"] or 0,
            "mobcash_stats": get_mobcash_stat(transactions),
            "api_stats": get_api_stat(transactions),
            "network_stats": get_network_stat(transactions),
            "source_stats": get_source_stat(transactions),
            "type_stats": get_type_stat(transactions),
            "balances": {
                "api_balances": api_balances,
                "mobcash_balances": mobcash_balances,
                "total_api_balance": total_api_balance,
                "total_mobcash_balance": total_mobcash_balance,
                "total_balance": total_balance,
            },
        }

        UserTransactionFilter.objects.update_or_create(
            user=request.user,
            defaults={
                "last": last,
                "start_date": start_date,
                "end_date": end_date,
                "source": source_list,
                "network": network_list,
                "api": api_list,
                "type": type_list,
                "mobcash": mobcash_list,
            },
        )
        return Response(data)

from collections import OrderedDict


def get_mobcash_stat(transactions):
    mobcash_apps = MobCashApp.objects.all()
    data = {}
    for mobcash in mobcash_apps:
        name = mobcash.name
        txs = transactions.filter(mobcash=name)
        data[name] = {
            "total": txs.count(),
            "total_amount": txs.aggregate(total=Sum("amount"))["total"] or 0,
            "fee": txs.aggregate(total=Sum("mobcash_fee"))["total"] or 0,
            "image": mobcash.image,
            "balance": mobcash.balance,
        }
    sorted_data = OrderedDict(
        sorted(data.items(), key=lambda item: item[1]["balance"], reverse=True)
    )

    return sorted_data  


def get_api_stat(transactions):
    data = {}
    for value, label in API_CHOICES:
        txs = transactions.filter(api=value)
        data[value] = {
            "label": label,
            "total": txs.count(),
            "total_amount": txs.aggregate(total=Sum("amount"))["total"] or 0,
            "fee": txs.aggregate(total=Sum("mobcash_fee"))["total"] or 0,
            
        }
    return data


def get_network_stat(transactions):
    data = {}
    for value, label in NETWORK_CHOICES:
        txs = transactions.filter(network=value)
        data[value] = {
            "label": label,
            "total": txs.count(),
            "total_amount": txs.aggregate(total=Sum("amount"))["total"] or 0,
            "fee": txs.aggregate(total=Sum("mobcash_fee"))["total"] or 0,
        }
    return data


def get_source_stat(transactions):
    data = {}
    for value, label in SOURCE_CHOICES:
        txs = transactions.filter(source=value)
        data[value] = {
            "label": label,
            "total": txs.count(),
            "total_amount": txs.aggregate(total=Sum("amount"))["total"] or 0,
            "fee": txs.aggregate(total=Sum("mobcash_fee"))["total"] or 0,
        }
    return data


def get_type_stat(transactions):
    data = {}
    for value, label in TYPE_CHOICES:
        txs = transactions.filter(type=value)
        data[value] = {
            "label": label,
            "total": txs.count(),
            "total_amount": txs.aggregate(total=Sum("amount"))["total"] or 0,
            "fee": txs.aggregate(total=Sum("mobcash_fee"))["total"] or 0,
        }
    return data


def send_stats_to_user():
    user_filter = UserTransactionFilter.objects.first()
    transactions = Transaction.objects.all().order_by("-created_at")
    if not user_filter:
        return
    if user_filter and user_filter.last:
        now = timezone.now()
        if user_filter.last == "yesterday":
            start_date = now - timedelta(days=1)
            end_date = now
        elif user_filter.last == "3_days":
            start_date = now - timedelta(days=3)
            end_date = None
        elif user_filter.last == "7_days":
            start_date = now - timedelta(days=7)
            end_date = None
        elif user_filter.last == "30_days":
            start_date = now - timedelta(days=30)
            end_date = None
        elif user_filter.last == "1_year":
            start_date = now - timedelta(days=365)
            end_date = None
        elif user_filter.last in ["all", "always"]:
            start_date = None
            end_date = None
    else:
        start_date = user_filter.start_date
        end_date = user_filter.end_date

    if start_date and isinstance(start_date, str):
        start_date = parse_datetime(start_date)
    if end_date and isinstance(end_date, str):
        end_date = parse_datetime(end_date)

    if start_date:
        transactions = transactions.filter(created_at__gte=start_date)
    if end_date:
        transactions = transactions.filter(created_at__lte=end_date)

    if user_filter.source:
        transactions = transactions.filter(source=user_filter.source)
    if user_filter.network:
        transactions = transactions.filter(network=user_filter.network)
    if user_filter.api:
        transactions = transactions.filter(api=user_filter.api)
    if user_filter.mobcash:
        transactions = transactions.filter(mobcash=user_filter.mobcash)
    if user_filter.type:
        transactions = transactions.filter(type=user_filter.type)

    # Récupération des soldes API et MobCash avec la même logique que dans ComptatView.get

    api_balances = {}
    for api_obj in APITransaction.objects.all():
        name = api_obj.name

        balance_updates = APIBalanceUpdate.objects.filter(api_transaction=api_obj)
        if start_date and end_date:
            updates_in_period = balance_updates.filter(
                created_at__gte=start_date, created_at__lte=end_date
            )
        elif start_date and not end_date:
            updates_in_period = balance_updates.filter(created_at__gte=start_date)
        else:
            updates_in_period = balance_updates.none()

        if updates_in_period.exists():
            last_update = updates_in_period.order_by("-created_at").first()
            balance = last_update.balance
        elif start_date:
            last_update_before = (
                balance_updates.filter(created_at__lt=start_date)
                .order_by("-created_at")
                .first()
            )
            if last_update_before:
                balance = last_update_before.balance
            else:
                balance = api_obj.balance
        else:
            balance = api_obj.balance
        api_balances[name] = balance

    mobcash_balances = {}
    for mobcash_obj in MobCashApp.objects.all():
        name = mobcash_obj.name

        balance_updates = MobCashAppBalanceUpdate.objects.filter(
            mobcash_balance=mobcash_obj
        )
        if start_date and end_date:
            updates_in_period = balance_updates.filter(
                created_at__gte=start_date, created_at__lte=end_date
            )
        elif start_date and not end_date:
            updates_in_period = balance_updates.filter(created_at__gte=start_date)
        else:
            updates_in_period = balance_updates.none()

        if updates_in_period.exists():
            last_update = updates_in_period.order_by("-created_at").first()
            balance = last_update.balance
        elif start_date:
            last_update_before = (
                balance_updates.filter(created_at__lt=start_date)
                .order_by("-created_at")
                .first()
            )
            if last_update_before:
                balance = last_update_before.balance
            else:
                balance = mobcash_obj.balance
        else:
            balance = mobcash_obj.balance
        mobcash_balances[name] = balance

    total_api_balance = sum(api_balances.values())
    total_mobcash_balance = sum(mobcash_balances.values())
    total_balance = total_api_balance + total_mobcash_balance

    stats = {
        "type": "stats_update",
        "context": "user_filter",
        "data": {
            "total": transactions.count(),
            "amount": transactions.aggregate(total=Sum("amount"))["total"] or 0,
            "mobcash_fee": transactions.aggregate(total=Sum("mobcash_fee"))["total"]
            or 0,
            "blaffa_fee": transactions.aggregate(total=Sum("blaffa_fee"))["total"],
            "balances": {
                "api_balances": api_balances,
                "mobcash_balances": mobcash_balances,
                "total_api_balance": total_api_balance,
                "total_mobcash_balance": total_mobcash_balance,
                "total_balance": total_balance,
            },
        },
    }
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{User.objects.first().id}_channel",
        {"type": "stat_data", "message": stats},
    )


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
