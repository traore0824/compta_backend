from django.urls import path
from . import views

urlpatterns = [
    path("compta", views.ComptatView.as_view()),
    path("transaction", views.CreateTransaction.as_view()),
    path("mobcash-apps", views.MobCashAppListView.as_view(), name="mobcash-list"),
    path(
        "mobcash-apps/<int:pk>",
        views.MobCashAppUpdateView.as_view(),
        name="mobcash-update",
    ),
    path(
        "api-transactions",
        views.APITransactionListView.as_view(),
        name="api-transaction-list",
    ),
    path(
        "api-transactions/<int:pk>",
        views.APITransactionUpdateView.as_view(),
        name="api-transaction-update",
    ),
    path("api-balance", views.APIBalanceView.as_view()),
    path("mobcash-balance", views.MobCashBalance.as_view()),
    path(
        "user-filter/",
        views.UserTransactionFilterView.as_view(),
        name="user-transaction-filter",
    ),
]
