from django.urls import path
from . import views

urlpatterns = [
    path("compta", views.ComptatView.as_view()),
    path("transaction", views.CreateTransaction.as_view()),
    path("mobcash-apps", views.MobCashAppListView.as_view(), name="mobcash-list"),
    path(
        "mobcash-apps/<int:pk>", views.MobCashAppUpdateView.as_view(), name="mobcash-update"
    ),
]
