from django.db import models
from django.contrib.auth.models import User
SOURCE_CHOICES = [
    ("web", "Web"),
    ("mobile", "Mobile"),
    ("telegram", "Telegram"),
    ("partner", "Partner"),
]
TYPE_CHOICES = [
    ("depot", "Dépôt"),
    ("retrait", "Retrait"),
    ("other", "other"),
]

API_CHOICES = [
    ("dgs", "DGS"),
    ("pal", "PAL"),
    ("bpay", "BPay"),
    ("barkapay", "BarkaPay"),
    ("connect", "Connect"),
]

NETWORK_CHOICES = [
    ("mtn", "MTN"),
    ("moov", "Moov"),
    ("orange", "Orange"),
    ("wave", "Wave"),
]


class Transaction(models.Model):
    reference = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    mobcash_fee = models.DecimalField(max_digits=10, decimal_places=2)
    blaffa_fee = models.DecimalField(max_digits=10, decimal_places=2)
    mobcash_balance = models.DecimalField(max_digits=15, decimal_places=2)
    api_balance = models.DecimalField(max_digits=15, decimal_places=2)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    user_mobcash_id = models.CharField(max_length=100)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    api = models.CharField(max_length=20, choices=API_CHOICES)
    network = models.CharField(max_length=10, choices=NETWORK_CHOICES)
    mobcash = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.reference} - {self.type} - {self.api}"


class APITransaction(models.Model):
    minimun_balance_amount = models.DecimalField(max_digits=15, decimal_places=2)
    name = models.CharField(max_length=20, choices=API_CHOICES)
    can_send_alert = models.BooleanField(default=True)


class MobCashApp(models.Model):
    minimun_balance_amount = models.DecimalField(max_digits=15, decimal_places=2)
    name = models.CharField(max_length=20)
    can_send_alert = models.BooleanField(default=True)
    deposit_fee = models.DecimalField(max_digits=15, decimal_places=2)
    retrait_fee = models.DecimalField(max_digits=15, decimal_places=2)


class Notification(models.Model):
    reference = models.CharField(max_length=150, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    title = models.CharField(max_length=100, blank=True, null=True)

    def total_unread_notification(self, user):
        return Notification.objects.filter(user=user, is_read=False).count()

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return str(self.id)

class UserTransactionFilter(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    last = models.CharField(max_length=20, null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=20, null=True, blank=True)
    network = models.CharField(max_length=20, null=True, blank=True)
    api = models.CharField(max_length=20, null=True, blank=True)
    type = models.CharField(max_length=20, null=True, blank=True)
    mobcash = models.CharField(max_length=100, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"Filter for {self.user.username}"



# Create your models here.
