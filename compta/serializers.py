import os
from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone

from compta.models import APISetting, MobCashSetting, Notification, Transaction
from compta.utils import send_mails, valider_password
from compta.view_2 import send_telegram_message

class RegisterUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
        ]
    def create(self, validated_data):
        user = User.objects.create(
            first_name=validated_data.get("first_name"),
            last_name=validated_data.get("last_name"),
            email=validated_data.get("email"),
            is_active=True,
            username= validated_data.get("email")
        )
        password = f"Default@{timezone.now().year}"
        user.set_password(password)
        user.username = user
        user.link_created_at = timezone.now()
        user.save()
        send_mails(
            subject="Compte ",
            to_email=user.email,
            template_name="new_account.html",
            context={"user": user, "password": password},
        )
        return user


class SendOtpSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordConfirmSerializer(serializers.Serializer):
    otp = serializers.CharField()
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

    def validate(self, data):
        new_password = data.get("new_password")
        confirm_password = data.get("confirm_password")
        if new_password != confirm_password:
            raise serializers.ValidationError({"password": "PASSWORD_NO_MATCH"})
        password_return = valider_password(password=data.get("new_password"))
        if password_return == False:
            raise serializers.ValidationError({"password": "PASSWORD_NOT_STRONG"})
        if password_return == "1":
            raise serializers.ValidationError(
                {"password": "You can't use your phone as a password "}
            )
        if password_return == "0":
            raise serializers.ValidationError(
                {"password": "You can't use your email as a password "}
            )
        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

    def validate(self, data):
        new_password = data.get("new_password")
        confirm_password = data.get("confirm_password")
        if new_password != confirm_password:
            raise serializers.ValidationError(
                {"PASSWORD_NO_MATCH": "PASSWORD_NO_MATCH"}
            )
        password_return = valider_password(password=data.get("new_password"))
        if password_return == False:
            raise serializers.ValidationError(
                {"PASSWORD_NOT_STRONG": "PASSWORD_NOT_STRONG"}
            )
        if password_return == "1":
            raise serializers.ValidationError(
                {"CANT_USE_PHONE": "You can't use your phone as a password "}
            )
        if password_return == "0":
            raise serializers.ValidationError(
                {"CANT_USE_EMAIL": "You can't use your email as a password "}
            )
        return data


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class RefreshObtainSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class UpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
        ]


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"

    def create(self, validated_data):
        mobcash_name = validated_data.get("mobcash")
        transaction_type = validated_data.get("type")
        api_name = validated_data.get("api")

        mobcash_config, _ = MobCashSetting.objects.get_or_create(name=mobcash_name)
        api_config, _ = APISetting.objects.get_or_create(name=api_name)

        if transaction_type == "depot":
            validated_data["mobcash_fee"] = mobcash_config.deposit_fee
        elif transaction_type == "retrait":
            validated_data["mobcash_fee"] = mobcash_config.retrait_fee

        transaction = Transaction.objects.create(**validated_data)

        alerts = []

        if (
            mobcash_config.can_send_alert
            and transaction.mobcash_balance <= mobcash_config.minimun_balance_amount
        ):
            alerts.append(
                {
                    "title": f"Solde critique MobCash: {transaction.mobcash}",
                    "content": f"Le solde est à {transaction.mobcash_balance} FCFA pour {transaction.mobcash} (seuil: {mobcash_config.minimun_balance_amount})",
                }
            )

        if (
            api_config.can_send_alert
            and transaction.api_balance <= api_config.minimun_balance_amount
        ):
            alerts.append(
                {
                    "title": f"Solde critique API: {transaction.api}",
                    "content": f"Le solde est à {transaction.api_balance} FCFA pour {transaction.api} (seuil: {api_config.minimun_balance_amount})",
                }
            )

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
