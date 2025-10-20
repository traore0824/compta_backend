from typing import Optional, Dict, Any, List
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import timedelta
from compta.models import UserTransactionFilter
from django.contrib.auth.models import User


class FilterService:
    """Service pour gérer les filtres de transactions"""

    @staticmethod
    def parse_filters_from_request(request) -> Dict[str, Any]:
        """
        Parse les filtres depuis la requête
        Si aucun filtre n'est envoyé, charge le dernier filtre sauvegardé
        Si is_all_date = True, ignore les dates
        Si start_date est null, prend la date d'aujourd'hui
        """
        # Vérifier si des filtres sont envoyés dans la requête
        has_filters = any(
            [
                request.GET.get("start_date"),
                request.GET.get("end_date"),
                request.GET.get("last"),
                request.GET.get("is_all_date"),
                request.GET.getlist("source"),
                request.GET.getlist("network"),
                request.GET.getlist("api"),
                request.GET.getlist("type"),
                request.GET.getlist("mobcash"),
            ]
        )

        if has_filters:
            # Utiliser les filtres de la requête
            filters = {
                "start_date": request.GET.get("start_date"),
                "end_date": request.GET.get("end_date"),
                "last": request.GET.get("last"),
                "is_all_date": request.GET.get("is_all_date", "false").lower()
                == "true",
                "source": request.GET.getlist("source"),
                "network": request.GET.getlist("network"),
                "api": request.GET.getlist("api"),
                "type": request.GET.getlist("type"),
                "mobcash": request.GET.getlist("mobcash"),
            }
        else:
            # Charger le dernier filtre sauvegardé de l'utilisateur
            filters = FilterService.load_user_last_filter(request.user)

        # Traiter les dates (conversion + gestion du "last")
        filters = FilterService.process_dates(filters)

        # Si is_all_date = True, ignorer les dates (toutes les dates depuis création)
        if filters.get("is_all_date"):
            filters["start_date"] = None
            filters["end_date"] = None
        # Sinon, si start_date est toujours null après traitement, mettre aujourd'hui
        elif not filters.get("start_date"):
            filters["start_date"] = timezone.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        return filters

    @staticmethod
    def load_user_last_filter(user) -> Dict[str, Any]:
        """
        Charge le dernier filtre sauvegardé de l'utilisateur
        Si aucun filtre n'existe, retourne des valeurs par défaut
        """
        try:
            user_filter = UserTransactionFilter.objects.get(user=user)
            return {
                "start_date": user_filter.start_date,
                "end_date": user_filter.end_date,
                "last": user_filter.last,
                "is_all_date": user_filter.is_all_date,
                "source": user_filter.source or [],
                "network": user_filter.network or [],
                "api": user_filter.api or [],
                "type": user_filter.type or [],
                "mobcash": user_filter.mobcash or [],
            }
        except UserTransactionFilter.DoesNotExist:
            # Valeurs par défaut si aucun filtre sauvegardé
            return {
                "start_date": None,  # Sera remplacé par aujourd'hui plus tard
                "end_date": None,
                "last": None,
                "is_all_date": False,
                "source": [],
                "network": [],
                "api": [],
                "type": [],
                "mobcash": [],
            }

    @staticmethod
    def process_dates(filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite les dates : conversion string -> datetime + gestion du paramètre 'last'
        """
        now = timezone.now()
        last = filters.get("last")

        # Si 'last' est défini, calculer start_date et end_date
        if last:
            if last == "yesterday":
                filters["start_date"] = now - timedelta(days=1)
                filters["end_date"] = now
                filters["is_all_date"] = False
            elif last == "3_days":
                filters["start_date"] = now - timedelta(days=3)
                filters["end_date"] = None
                filters["is_all_date"] = False
            elif last == "7_days":
                filters["start_date"] = now - timedelta(days=7)
                filters["end_date"] = None
                filters["is_all_date"] = False
            elif last == "30_days":
                filters["start_date"] = now - timedelta(days=30)
                filters["end_date"] = None
                filters["is_all_date"] = False
            elif last == "1_year":
                filters["start_date"] = now - timedelta(days=365)
                filters["end_date"] = None
                filters["is_all_date"] = False
            elif last in ["always", "all"]:
                filters["start_date"] = None
                filters["end_date"] = None
                filters["is_all_date"] = True
        else:
            # Conversion des dates string en datetime
            start_date = filters.get("start_date")
            end_date = filters.get("end_date")

            if start_date and isinstance(start_date, str):
                filters["start_date"] = parse_datetime(start_date)

            if end_date and isinstance(end_date, str):
                filters["end_date"] = parse_datetime(end_date)

        return filters

    @staticmethod
    def apply_filters(queryset, filters: Dict[str, Any]):
        """
        Applique tous les filtres à un QuerySet de transactions
        """
        # Si is_all_date = True, ne pas filtrer par dates
        if not filters.get("is_all_date"):
            start_date = filters.get("start_date")
            end_date = filters.get("end_date")

            if start_date:
                queryset = queryset.filter(created_at__gte=start_date)
            if end_date:
                queryset = queryset.filter(created_at__lte=end_date)

        # Filtres sur les choix
        source_list = filters.get("source", [])
        network_list = filters.get("network", [])
        api_list = filters.get("api", [])
        type_list = filters.get("type", [])
        mobcash_list = filters.get("mobcash", [])

        if source_list:
            queryset = queryset.filter(source__in=source_list)
        if network_list:
            queryset = queryset.filter(network__in=network_list)
        if api_list:
            queryset = queryset.filter(api__in=api_list)
        if type_list:
            queryset = queryset.filter(type__in=type_list)
        if mobcash_list:
            queryset = queryset.filter(mobcash__in=mobcash_list)

        return queryset

    @staticmethod
    def save_user_filter(user, filters: Dict[str, Any]):
        """
        Sauvegarde les filtres de l'utilisateur dans la base de données
        """
        UserTransactionFilter.objects.update_or_create(
            user=user,
            defaults={
                "last": filters.get("last"),
                "start_date": filters.get("start_date"),
                "end_date": filters.get("end_date"),
                "is_all_date": filters.get("is_all_date", False),
                "source": filters.get("source", []),
                "network": filters.get("network", []),
                "api": filters.get("api", []),
                "type": filters.get("type", []),
                "mobcash": filters.get("mobcash", []),
            },
        )
