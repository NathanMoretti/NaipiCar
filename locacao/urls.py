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
    # Painel administrativo (somente is_staff)
    path("painel/", RedirectView.as_view(pattern_name="painel_dashboard"), name="painel"),
    path("painel/dashboard/", painel_views.dashboard, name="painel_dashboard"),
    path("painel/reservas/", painel_views.reservas_painel, name="painel_reservas"),
    path("painel/reservas/<int:pk>/situacao/", painel_views.reserva_situacao, name="painel_reserva_situacao"),
    path("painel/cadastros/", painel_views.cadastros_inicio, name="painel_cadastros_inicio"),
    path("painel/cadastros/<str:aba>/", painel_views.cadastros, name="painel_cadastros"),
    path("painel/cadastros/<str:aba>/<int:pk>/editar/", painel_views.cadastro_editar, name="painel_cadastro_editar"),
    path("painel/cadastros/<str:aba>/<int:pk>/excluir/", painel_views.cadastro_excluir, name="painel_cadastro_excluir"),
    path("painel/veiculos/", painel_views.veiculos_painel, name="painel_veiculos"),
    path("painel/veiculos/<int:pk>/editar/", painel_views.veiculo_editar, name="painel_veiculo_editar"),
    path("painel/veiculos/<int:pk>/excluir/", painel_views.veiculo_excluir, name="painel_veiculo_excluir"),
]