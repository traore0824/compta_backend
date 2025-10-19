from typing import Dict, Optional
from django.utils import timezone
from decimal import Decimal
from compta.models import (
    APITransaction,
    APIBalanceUpdate,
    MobCashApp,
    MobCashAppBalanceUpdate,
)


class BalanceService:
    """Service pour calculer les balances API et MobCash"""

    @staticmethod
    def get_all_balances(start_date=None, end_date=None) -> Dict[str, any]:
        """
        Récupère toutes les balances (API + MobCash) pour une période donnée
        """
        api_balances = BalanceService.get_api_balances(start_date, end_date)
        mobcash_balances = BalanceService.get_mobcash_balances(start_date, end_date)

        total_api_balance = sum(api_balances.values())
        total_mobcash_balance = sum(mobcash_balances.values())
        total_balance = total_api_balance + total_mobcash_balance

        return {
            "api_balances": api_balances,
            "mobcash_balances": mobcash_balances,
            "total_api_balance": total_api_balance,
            "total_mobcash_balance": total_mobcash_balance,
            "total_balance": total_balance,
        }

    @staticmethod
    def get_api_balances(start_date=None, end_date=None) -> Dict[str, Decimal]:
        """
        Calcule les balances de toutes les API pour une période donnée
        """
        api_balances = {}

        for api_obj in APITransaction.objects.all():
            balance = BalanceService._get_balance_at_period(
                instance=api_obj,
                updates_queryset=APIBalanceUpdate.objects.filter(
                    api_transaction=api_obj
                ),
                start_date=start_date,
                end_date=end_date,
            )
            api_balances[api_obj.name] = balance

        return api_balances

    @staticmethod
    def get_mobcash_balances(start_date=None, end_date=None) -> Dict[str, Decimal]:
        """
        Calcule les balances de toutes les MobCashApp pour une période donnée
        """
        mobcash_balances = {}

        for mobcash_obj in MobCashApp.objects.all():
            balance = BalanceService._get_balance_at_period(
                instance=mobcash_obj,
                updates_queryset=MobCashAppBalanceUpdate.objects.filter(
                    mobcash_balance=mobcash_obj
                ),
                start_date=start_date,
                end_date=end_date,
            )
            mobcash_balances[mobcash_obj.name] = balance

        return mobcash_balances

    @staticmethod
    def _get_balance_at_period(
        instance, updates_queryset, start_date=None, end_date=None
    ) -> Decimal:
        """
        Méthode générique pour calculer la balance à une période donnée
        Logique :
        1. Si des mises à jour existent dans la période → prendre la dernière
        2. Sinon, si start_date existe → prendre la dernière mise à jour avant start_date
        3. Sinon → prendre la balance actuelle de l'instance
        """
        # Filtrer les mises à jour selon la période
        if start_date and end_date:
            updates_in_period = updates_queryset.filter(
                created_at__gte=start_date, created_at__lte=end_date
            )
        elif start_date and not end_date:
            updates_in_period = updates_queryset.filter(created_at__gte=start_date)
        else:
            updates_in_period = updates_queryset.none()

        # Si des mises à jour existent dans la période
        if updates_in_period.exists():
            last_update = updates_in_period.order_by("-created_at").first()
            return last_update.balance

        # Sinon, chercher la dernière mise à jour avant start_date
        elif start_date:
            last_update_before = (
                updates_queryset.filter(created_at__lt=start_date)
                .order_by("-created_at")
                .first()
            )
            if last_update_before:
                return last_update_before.balance
            else:
                return instance.balance

        # Par défaut, retourner la balance actuelle
        else:
            return instance.balance
