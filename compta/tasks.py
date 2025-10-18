import os
from datetime import timedelta
from django.utils import timezone
from compta.models import Transaction, APITransaction, MobCashApp
import requests
from django.db.models import Sum
from django.utils.formats import number_format
from compta.view_2 import send_telegram_message
from celery import shared_task

from compta.views import get_api_balance, get_mobcash_balance


@shared_task
def send_compta_summary():
    now = timezone.now()
    twelve_hours_ago = now - timedelta(hours=12)

    # Transactions récentes
    recent_transactions = Transaction.objects.filter(created_at__gte=twelve_hours_ago)
    depot_count = recent_transactions.filter(type="depot").count()
    retrait_count = recent_transactions.filter(type="retrait").count()

    # Balances
    api_balance_total = (
        APITransaction.objects.aggregate(total=Sum("balance"))["total"] or 0
    )
    mobcash_balance_total = (
        MobCashApp.objects.aggregate(total=Sum("balance"))["total"] or 0
    )
    total_balance = api_balance_total + mobcash_balance_total

    # Formatage des montants en FCFA
    api_balance_str = (
        number_format(api_balance_total, decimal_pos=0, use_l10n=True) + " FCFA"
    )
    mobcash_balance_str = (
        number_format(mobcash_balance_total, decimal_pos=0, use_l10n=True) + " FCFA"
    )
    total_balance_str = (
        number_format(total_balance, decimal_pos=0, use_l10n=True) + " FCFA"
    )

    # Frais Mobcash sur les transactions
    deposit_fee = (
        recent_transactions.filter(type="depot").aggregate(total=Sum("mobcash_fee"))[
            "total"
        ]
        or 0
    )
    retrait_fee = (
        recent_transactions.filter(type="retrait").aggregate(total=Sum("mobcash_fee"))[
            "total"
        ]
        or 0
    )

    deposit_fee_str = number_format(deposit_fee, decimal_pos=0, use_l10n=True) + " FCFA"
    retrait_fee_str = number_format(retrait_fee, decimal_pos=0, use_l10n=True) + " FCFA"

    # Message final
    message = (
        f"📊 *Résumé des dernières 12 heures*\n\n"
        f"✅ Total des Dépôts : {depot_count}\n"+
        f"❌ Total des Retraits : {retrait_count}\n\n"
        f"💸 *Commission Genere*\n"
        f"• Sur dépôts : {deposit_fee_str}\n"
        f"• Sur retraits : {retrait_fee_str}\n\n"
        f"💼 *Solde actuel*\n"
        f"• Soldes (API) : {api_balance_str}\n"
        f"• Solde des APPs : {mobcash_balance_str}\n"
        f"🔢 Solde total : {total_balance_str}\n\n"
    )

    return send_telegram_message("", message)


@shared_task
def update_balance_api():
    get_api_balance()
    get_mobcash_balance()
