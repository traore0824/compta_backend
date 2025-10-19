from django.db.models import QuerySet, Sum
from compta.models import Transaction


class TransactionService:
    """Service pour la logique métier des transactions"""

    @staticmethod
    def get_all_transactions() -> QuerySet:
        """
        Récupère toutes les transactions ordonnées par date décroissante
        """
        return Transaction.objects.all().order_by("-created_at")

    @staticmethod
    def get_transaction_aggregates(transactions: QuerySet) -> dict:
        """
        Calcule les agrégats des transactions (totaux, fees, etc.)
        """
        return {
            "total": transactions.count(),
            "mobcash_fee": transactions.aggregate(total=Sum("mobcash_fee"))["total"]
            or 0,
            "blaffa_fee": transactions.aggregate(total=Sum("blaffa_fee"))["total"] or 0,
            "amount": transactions.aggregate(total=Sum("amount"))["total"] or 0,
        }
