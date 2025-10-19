from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from django.conf import settings
import re

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def log_filter_usage(user, filters: Dict[str, Any]):
    """
    Log l'utilisation des filtres pour le monitoring
    """
    logger.info(
        f"User {user.username} used filters: "
        f"start_date={filters.get('start_date')}, "
        f"end_date={filters.get('end_date')}, "
        f"last={filters.get('last')}"
    )


def format_balance(amount: float) -> str:
    """
    Formate un montant en devise locale
    """
    return f"{amount:,.2f} FCFA"


def send_mails(subject, to_email, template_name, context={}, body=None):
    try:
        user = User.objects.filter(email=to_email).first()
        context["user"] = user
        template = render_to_string(template_name, context)
        msg = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=settings.EMAIL_HOST_USER,
            to=[to_email],
        )
        msg.attach_alternative(template, "text/html")
        response = msg.send()
        return response
    except Exception as e:
        # LoggerService.e(f"Erreur lors de l'envoi de l'email: {str(e)}")
        return str(e)


def valider_password(password: str, email=None, phone=None):
    if phone and phone == password:
        return "1"
    if email and email == password:
        return "0"
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False

    if not re.search(r"[0-9]", password):
        return False
    return True
