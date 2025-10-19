from rest_framework.exceptions import ValidationError
from django.utils import timezone


class FilterValidator:
    """Validateurs pour les filtres de transactions"""

    @staticmethod
    def validate_date_range(start_date, end_date):
        """
        Valide que start_date est avant end_date
        """
        if start_date and end_date and start_date > end_date:
            raise ValidationError(
                "La date de début doit être antérieure à la date de fin"
            )

    @staticmethod
    def validate_date_not_future(date):
        """
        Valide qu'une date n'est pas dans le futur
        """
        if date and date > timezone.now():
            raise ValidationError("La date ne peut pas être dans le futur")

    @staticmethod
    def validate_choice(value, choices):
        """
        Valide qu'une valeur est dans les choix autorisés
        """
        valid_values = [choice[0] for choice in choices]
        if value and value not in valid_values:
            raise ValidationError(
                f"'{value}' n'est pas un choix valide. Choix possibles : {valid_values}"
            )
