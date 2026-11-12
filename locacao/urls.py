from django.contrib.auth import views as auth_views
from django.urls import path
from contas import views as contas_views
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("veiculos/", views.veiculos, name="veiculos"),
    path(
        "veiculo/<int:veiculo_id>/reservar/",
        views.reservar_veiculo,
        name="reservar_veiculo",
    ),
    path("minhas-reservas/", views.minhas_reservas, name="minhas_reservas"),
    path(
        "minhas-reservas/<int:reserva_id>/cancelar/",
        views.cancelar_reserva,
        name="cancelar_reserva",
    ),
    path("cadastro/", contas_views.cadastro, name="cadastro"),
    path("termos/", contas_views.termos, name="termos"),
    path("login/", contas_views.NaipiLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="index"), name="logout"),
]