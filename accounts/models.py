import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from tinymce.models import HTMLField
from .manager import UserManager


class AppName(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    name = models.CharField(
        max_length=100,
        unique=True,
    )
    image = models.TextField(blank=True, null=True)
    enable = models.BooleanField(default=True)
    hash = models.CharField(blank=True, null=True, max_length=120)
    cashdeskid = models.CharField(blank=True, null=True, max_length=120)
    cashierpass = models.CharField(blank=True, null=True, max_length=120)
    deposit_tuto_link = models.URLField(blank=True, null=True)
    withdrawal_tuto_link = models.URLField(blank=True, null=True)
    why_withdrawal_fail = models.URLField(blank=True, null=True)
    order = models.PositiveSmallIntegerField(blank=True, null=True)
    city = models.CharField(max_length=120, blank=True, null=True)
    street = models.CharField(max_length=124, null=True, blank=True)
    minimun_deposit = models.PositiveIntegerField(blank=True, null=True)
    max_deposit = models.PositiveIntegerField(blank=True, null=True)
    minimun_with = models.PositiveIntegerField(blank=True, null=True)
    max_win = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "App name"
        verbose_name_plural = "App names"

class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_delete = models.BooleanField(default=False)
    first_name = models.CharField(max_length=256)
    last_name = models.CharField(max_length=256)
    email = models.CharField(
        max_length=256,
        unique=True,
    )
    phone = models.CharField(
        max_length=256,
        unique=True,
    )
    otp = models.CharField(max_length=100, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)
    is_block = models.BooleanField(default=False)
    password = models.CharField(max_length=255, null=True, blank=True)
    referrer_code = models.CharField(max_length=1000, blank=True, null=True)
    referral_code = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_supperuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["phone"]

    def __str__(self):
        return self.email

    def full_name(self):
        return f"{self.last_name} {self.first_name}"

    def has_perm(self, perm, obj=None):
        return self.is_supperuser

    def has_module_perms(self, app_label):
        return True

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
