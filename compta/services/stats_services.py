from typing import Dict, List, Tuple
from collections import OrderedDict
from django.db.models import Sum, QuerySet
from compta.models import (
    APITransaction,
    MobCashApp,
    API_CHOICES,
    NETWORK_CHOICES,
    SOURCE_CHOICES,
    TYPE_CHOICES,
)
from compta.serializers import MobCashAppSerializer


class StatsService:
    """Service pour calculer les statistiques des transactions"""

    @staticmethod
    def get_all_stats(transactions: QuerySet) -> Dict[str, any]:
        """
        Récupère toutes les statistiques pour un ensemble de transactions
        """
        return {
            "mobcash_stats": StatsService.get_mobcash_stats(transactions),
            "api_stats": StatsService.get_api_stats(transactions),
            "network_stats": StatsService.get_generic_stats(
                transactions, "network", NETWORK_CHOICES
            ),
            "source_stats": StatsService.get_generic_stats(
                transactions, "source", SOURCE_CHOICES
            ),
            "type_stats": StatsService.get_generic_stats(
                transactions, "type", TYPE_CHOICES
            ),
        }

    @staticmethod
    def get_mobcash_stats(transactions: QuerySet) -> OrderedDict:
        """
        Calcule les statistiques détaillées par MobCash
        """
        mobcash_apps = MobCashApp.objects.all()
        data = {}

        for mobcash in mobcash_apps:
            name = mobcash.name
            txs = transactions.filter(mobcash=name)

            # Statistiques détaillées
            deposit_txs = txs.filter(type="depot")
            retrait_txs = txs.filter(type="retrait")

            data[name] = {
                "total": txs.count(),
                "total_amount": txs.aggregate(total=Sum("amount"))["total"] or 0,
                "fee": txs.aggregate(total=Sum("mobcash_fee"))["total"] or 0,
                "image": mobcash.image,
                "balance": mobcash.balance,
                "id": mobcash.id,
                "name": mobcash.name.upper(),
                "total_commission_amount": txs.aggregate(total=Sum("mobcash_fee"))[
                    "total"
                ]
                or 0,
                "total_operations_amount": txs.aggregate(total=Sum("amount"))["total"]
                or 0,
                "withdrawal_commission": retrait_txs.aggregate(
                    total=Sum("mobcash_fee")
                )["total"]
                or 0,
                "deposit_commission": deposit_txs.aggregate(total=Sum("mobcash_fee"))[
                    "total"
                ]
                or 0,
                "total_withdrawal_amount": retrait_txs.aggregate(total=Sum("amount"))[
                    "total"
                ]
                or 0,
                "total_deposit_amount": deposit_txs.aggregate(total=Sum("amount"))[
                    "total"
                ]
                or 0,
                "total_withdrawals": retrait_txs.count(),
                "total_deposit": deposit_txs.count(),
                "mobcash_setting": MobCashAppSerializer(mobcash).data,
            }

        # Trier par balance décroissante
        sorted_data = OrderedDict(
            sorted(data.items(), key=lambda item: item[1]["balance"], reverse=True)
        )

        return sorted_data

    @staticmethod
    def get_api_stats(transactions: QuerySet) -> OrderedDict:
        """
        Calcule les statistiques détaillées par API
        """
        api_transactions = APITransaction.objects.all()
        data = {}
        total_transactions = transactions.count()

        for api_transaction in api_transactions:
            api = api_transaction.name.lower()
            txs = transactions.filter(api=api)
            total = txs.count()
            total_amount = txs.aggregate(total=Sum("amount"))["total"] or 0
            fee = txs.aggregate(total=Sum("mobcash_fee"))["total"] or 0

            # Pourcentage d'utilisation
            percent = (
                (total / total_transactions * 100) if total_transactions > 0 else 0
            )

            # Stats par réseau
            raw_network_stat = {
                "mtn": txs.filter(network="mtn").count(),
                "moov": txs.filter(network="moov").count(),
                "orange": txs.filter(network="orange").count(),
                "wave": txs.filter(network="wave").count(),
            }

            # Tri décroissant des réseaux
            sorted_network_stat = OrderedDict(
                sorted(raw_network_stat.items(), key=lambda item: item[1], reverse=True)
            )

            data[api] = {
                "label": api,
                "total": total,
                "total_amount": total_amount,
                "fee": fee,
                "balance": api_transaction.balance,
                "percent": round(percent, 2),
                "total_withdrawal_amount": txs.filter(type="retrait").aggregate(
                    total=Sum("amount")
                )["total"]
                or 0,
                "total_deposit_amount": txs.filter(type="depot").aggregate(
                    total=Sum("amount")
                )["total"]
                or 0,
                "total_withdrawals": txs.filter(type="retrait").count(),
                "total_deposit": txs.filter(type="depot").count(),
                "network_stat": sorted_network_stat,
                "id": api_transaction.id,
            }

        # Trier par pourcentage décroissant
        sorted_data = OrderedDict(
            sorted(data.items(), key=lambda item: item[1]["percent"], reverse=True)
        )

        return sorted_data

    @staticmethod
    def get_generic_stats(
        transactions: QuerySet, field: str, choices: List[Tuple[str, str]]
    ) -> Dict[str, any]:
        """
        Fonction générique pour calculer les stats
        Fonctionne pour source, network, type, etc.
        """
        data = {}

        for value, label in choices:
            txs = transactions.filter(**{field: value})
            data[value] = {
                "label": label,
                "total": txs.count(),
                "total_amount": txs.aggregate(total=Sum("amount"))["total"] or 0,
                "fee": txs.aggregate(total=Sum("mobcash_fee"))["total"] or 0,
            }

        return data
