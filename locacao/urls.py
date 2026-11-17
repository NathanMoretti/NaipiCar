from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView
from contas import views as contas_views
from . import painel_views, views

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
    path("painel/", RedirectView.as_view(pattern_name="painel_veiculos"), name="painel"),
    path("painel/veiculos/", painel_views.veiculos_painel, name="painel_veiculos"),
    path("painel/veiculos/<int:pk>/editar/", painel_views.veiculo_editar, name="painel_veiculo_editar"),
    path("painel/veiculos/<int:pk>/excluir/", painel_views.veiculo_excluir, name="painel_veiculo_excluir"),
]