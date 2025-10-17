from django.contrib import admin
from .models import (
    MobCashApp,
    APITransaction,
    APIBalanceUpdate,
    MobCashAppBalanceUpdate,
    Transaction,
)


@admin.register(MobCashApp)
class MobCashAppAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "balance",
        "minimun_balance_amount",
        "deposit_fee_percent",
        "retrait_fee_percent",
        "partner_deposit_fee_percent",
        "partner_retrait_fee_percent",
        "can_send_alert",
    )
    list_filter = ("can_send_alert",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(APITransaction)
class APITransactionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "balance",
        "minimun_balance_amount",
        "can_send_alert",
    )
    list_filter = ("can_send_alert", "name")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(APIBalanceUpdate)
class APIBalanceUpdateAdmin(admin.ModelAdmin):
    list_display = ("id", "api_transaction", "balance", "created_at")
    list_filter = ("api_transaction", "created_at")
    search_fields = ("api_transaction__name",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)


@admin.register(MobCashAppBalanceUpdate)
class MobCashAppBalanceUpdateAdmin(admin.ModelAdmin):
    list_display = ("id", "mobcash_balance", "balance", "created_at")
    list_filter = ("mobcash_balance", "created_at")
    search_fields = ("mobcash_balance__name",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "amount",
        "source",
        "type",
        "api",
        "network",
        "mobcash",
        "user_mobcash_id",
        "created_at",
        "mobcash_fee",
        "blaffa_fee",
        "mobcash_balance",
        "api_balance",
    )
    list_filter = ("api", "source", "type", "network", "created_at")
    search_fields = ("reference", "user_mobcash_id", "mobcash")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
