from typing import Dict
from decimal import Decimal
from compta.models import APITransaction, MobCashApp


class BalanceService:
    """Service pour récupérer les balances actuelles API et MobCash"""

    @staticmethod
    def get_all_balances() -> Dict[str, any]:
        """
        Récupère toutes les balances actuelles (API + MobCash)
        """
        api_balances = BalanceService.get_api_balances()
        mobcash_balances = BalanceService.get_mobcash_balances()

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
    def get_api_balances() -> Dict[str, Decimal]:
        """
        Récupère les balances actuelles de toutes les API
        """
        api_balances = {}

        for api_obj in APITransaction.objects.all():
            api_balances[api_obj.name] = api_obj.balance

        return api_balances

    @staticmethod
    def get_mobcash_balances() -> Dict[str, Decimal]:
        """
        Récupère les balances actuelles de toutes les MobCashApp
        """
        mobcash_balances = {}

        for mobcash_obj in MobCashApp.objects.all():
            mobcash_balances[mobcash_obj.name] = mobcash_obj.balance

        return mobcash_balances
