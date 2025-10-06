from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AppName, User


@admin.register(User)
class UserModelAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "phone",
        "first_name",
        "last_name",
        "phone_indicative",
        "user_app_id",
        "country",
    )
    readonly_fields = ("date_joined",)
    fieldsets = (
        (
            "Personal info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "phone",
                    "otp",
                    "email",
                    "is_block",
                    "referrer_code",
                    "referral_code",
                    "user_app_id",
                    "is_delete",
                    "country",
                    "password",
                    "status",
                    "user_card",
                    "domicile",
                    "preference_notification",
                    "is_partner",
                    "secret_key",
                    "public_key",
                )
            },
        ),
        ("permissions", {"fields": ("is_active",)}),
    )
    ordering = ("id",)
    search_fields = ("email",)


@admin.register(AppName)
class AppNameAdmin(admin.ModelAdmin):
    list_display = ["id", "public_name"]
