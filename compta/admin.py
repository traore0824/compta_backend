from django.contrib import admin
from .models import (
    MobCashApp,
    APITransaction,
    APIBalanceUpdate,
    MobCashAppBalanceUpdate,
    Transaction,
    UserTransactionFilter,
)
from django.utils.html import format_html


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


@admin.register(UserTransactionFilter)
class UserTransactionFilterAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "last",
        "start_date",
        "end_date",
        "display_source",
        "display_network",
        "display_api",
        "display_type",
        "display_mobcash",
        "updated_at",
    )
    readonly_fields = ("updated_at",)

    def _format_json_list(self, value):
        if not value:
            return "-"
        return format_html(", ".join(str(v) for v in value))

    def display_source(self, obj):
        return self._format_json_list(obj.source)

    display_source.short_description = "Source"

    def display_network(self, obj):
        return self._format_json_list(obj.network)

    display_network.short_description = "Network"

    def display_api(self, obj):
        return self._format_json_list(obj.api)

    display_api.short_description = "API"

    def display_type(self, obj):
        return self._format_json_list(obj.type)

    display_type.short_description = "Type"

    def display_mobcash(self, obj):
        return self._format_json_list(obj.mobcash)

    display_mobcash.short_description = "MobCash"
