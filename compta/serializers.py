import os
from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone

from compta.models import APIBalanceUpdate, APITransaction, MobCashApp, MobCashAppBalanceUpdate, Notification, Transaction, UserTransactionFilter
from compta.utils import send_mails, valider_password
from compta.view_2 import send_telegram_message


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"

    def create(self, validated_data):
        mobcash_name = validated_data.get("mobcash")
        transaction_type = validated_data.get("type")
        api_name = validated_data.get("api")

        mobcash_config, _ = MobCashApp.objects.get_or_create(name=mobcash_name)
        api_config, _ = APITransaction.objects.get_or_create(name=api_name)

        if transaction_type == "depot":
            validated_data["mobcash_fee"] = (
                mobcash_config.deposit_fee_percent * validated_data.get("amount")
            ) / 100
        elif transaction_type == "retrait":
            validated_data["mobcash_fee"] = (
                mobcash_config.retrait_fee_percent * validated_data.get("amount")
            ) / 100

        transaction = Transaction.objects.create(**validated_data)

        alerts = []

        # if (
        #     mobcash_config.can_send_alert
        #     and transaction.mobcash_balance <= mobcash_config.minimun_balance_amount
        # ):
        #     alerts.append(
        #         {
        #             "title": f"Solde critique MobCash: {transaction.mobcash}",
        #             "content": f"Le solde est à {transaction.mobcash_balance} FCFA pour {transaction.mobcash} (seuil: {mobcash_config.minimun_balance_amount})",
        #         }
        #     )

        # if (
        #     api_config.can_send_alert
        #     and transaction.api_balance <= api_config.minimun_balance_amount
        # ):
        #     alerts.append(
        #         {
        #             "title": f"Solde critique API: {transaction.api}",
        #             "content": f"Le solde est à {transaction.api_balance} FCFA pour {transaction.api} (seuil: {api_config.minimun_balance_amount})",
        #         }
        #     )

        for alert in alerts:
            send_telegram_message(
                chat_id=os.getenv("ADMIN_CHAT_ID"), content=alert["content"]
            )
            Notification.objects.create(
                reference=transaction.reference,
                title=alert["title"],
                content=alert["content"],
            )

        return transaction


class MobCashAppSerializer(serializers.ModelSerializer):
    class Meta:
        model = MobCashApp
        fields = "__all__"


class APITransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = APITransaction
        fields = "__all__"


class APIBalanceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = APIBalanceUpdate
        fields = ["id", "api_transaction", "balance", "created_at"]


class MobCashAppBalanceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MobCashAppBalanceUpdate
        fields = ["id", "mobcash_balance", "balance", "created_at"]


class UserTransactionFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserTransactionFilter
        fields = "__all__"
        read_only_fields = ["user", "updated_at"]
