from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from django.conf import settings
import re

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
