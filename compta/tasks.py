import os
from datetime import timedelta
from django.utils import timezone
from compta.models import Transaction, APITransaction, MobCashApp
import requests
from django.db.models import Sum
from django.utils.formats import number_format
from compta.view_2 import send_stats_to_user, send_telegram_message
from celery import shared_task

from compta.views import get_api_balance, get_mobcash_balance, update_mobcash_balance


@shared_task
def send_compta_summary():
    now = timezone.now()
    twelve_hours_ago = now - timedelta(hours=12)

    # Transactions récentes
    recent_transactions = Transaction.objects.filter(created_at__gte=twelve_hours_ago)

    total_transactions = recent_transactions.count()
    depot_transactions = recent_transactions.filter(type="depot")
    retrait_transactions = recent_transactions.filter(type="retrait")

    # Montants totaux
    montant_depot = depot_transactions.aggregate(total=Sum("amount"))["total"] or 0
    montant_retrait = retrait_transactions.aggregate(total=Sum("amount"))["total"] or 0
    montant_total = montant_depot + montant_retrait

    # Commissions
    commission_depot = (
        depot_transactions.aggregate(total=Sum("mobcash_fee"))["total"] or 0
    )
    commission_retrait = (
        retrait_transactions.aggregate(total=Sum("mobcash_fee"))["total"] or 0
    )
    commission_totale = commission_depot + commission_retrait

    # Soldes API individuels
    api_qs = APITransaction.objects.all()
    solde_api_details = "\n".join(
        [
            f"   • **{api.name} :** `{number_format(api.balance, decimal_pos=0, use_l10n=True)} FCFA`"
            for api in api_qs
        ]
    )
    solde_api_total = sum(api.balance for api in api_qs)

    # Soldes MobCashApp individuels
    mobcash_qs = MobCashApp.objects.all()
    solde_mobcash_details = "\n".join(
        [
            f"   • **{app.name} :** `{number_format(app.balance, decimal_pos=0, use_l10n=True)} FCFA`"
            for app in mobcash_qs
        ]
    )
    solde_mobcash_total = sum(app.balance for app in mobcash_qs)

    # Formatage général
    montant_depot_str = (
        number_format(montant_depot, decimal_pos=0, use_l10n=True) + " FCFA"
    )
    montant_retrait_str = (
        number_format(montant_retrait, decimal_pos=0, use_l10n=True) + " FCFA"
    )
    montant_total_str = (
        number_format(montant_total, decimal_pos=0, use_l10n=True) + " FCFA"
    )

    commission_depot_str = (
        number_format(commission_depot, decimal_pos=0, use_l10n=True) + " FCFA"
    )
    commission_retrait_str = (
        number_format(commission_retrait, decimal_pos=0, use_l10n=True) + " FCFA"
    )
    commission_totale_str = (
        number_format(commission_totale, decimal_pos=0, use_l10n=True) + " FCFA"
    )

    solde_api_total_str = (
        number_format(solde_api_total, decimal_pos=0, use_l10n=True) + " FCFA"
    )
    solde_mobcash_total_str = (
        number_format(solde_mobcash_total, decimal_pos=0, use_l10n=True) + " FCFA"
    )

    date_du_jour = now.strftime("%d/%m/%Y")
    heure_update = now.strftime("%H:%M")

    # Message Telegram
    message = f"""
        📊 *Rapport de Comptabilité — {date_du_jour}*

        💰 *Transactions Totales:* `{total_transactions}`

        🔺 *Dépôts*
        • **Montant :** `{montant_depot_str}`
        • **Commission :** `{commission_depot_str}`

        🔻 *Retraits*
        • **Montant :** `{montant_retrait_str}`
        • **Commission :** `{commission_retrait_str}`

        📈 *Résumé général*
        • **Total montants :** `{montant_total_str}`
        • **Total commissions :** `{commission_totale_str}`

        🏦 *Soldes API de Transactions*
        {solde_api_details}
        ➤ **Total API :** `{solde_api_total_str}`

        💼 *Soldes Apps Mobcash*
        {solde_mobcash_details}
        ➤ **Total Mobcash :** `{solde_mobcash_total_str}`

        🕓 *Dernière mise à jour :* `{heure_update}`
        """

    return send_telegram_message(content=message, chat_id="6605816009")


@shared_task
def update_balance_api():
    get_api_balance()
    get_mobcash_balance()
    send_stats_to_user()


@shared_task
def update_all_balance_process(transaction_id):
    get_api_balance()
    update_mobcash_balance(transaction=Transaction.objects.get(id=transaction_id))
    send_stats_to_user()
