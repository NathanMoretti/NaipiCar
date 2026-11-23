from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from django.views.generic import RedirectView
from contas import views as contas_views
from contas import views_perfil
from contas.forms_senha import RecuperarSenhaForm
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
    path("perfil/", views_perfil.editar_perfil, name="editar_perfil"),
    # Recuperação de senha por e-mail
    path(
        "recuperar-senha/",
        auth_views.PasswordResetView.as_view(
            template_name="locacao/recuperar_senha.html",
            form_class=RecuperarSenhaForm,
            email_template_name="locacao/email_recuperar_senha.txt",
            subject_template_name="locacao/email_recuperar_senha_assunto.txt",
            success_url=reverse_lazy("recuperar_senha_enviado"),
        ),
        name="recuperar_senha",
    ),
    path(
        "recuperar-senha/enviado/",
        auth_views.PasswordResetDoneView.as_view(template_name="locacao/recuperar_senha_enviado.html"),
        name="recuperar_senha_enviado",
    ),
    path(
        "redefinir-senha/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="locacao/redefinir_senha.html",
            success_url=reverse_lazy("redefinir_senha_concluido"),
        ),
        name="redefinir_senha",
    ),
    path(
        "redefinir-senha/concluido/",
        auth_views.PasswordResetCompleteView.as_view(template_name="locacao/redefinir_senha_concluido.html"),
        name="redefinir_senha_concluido",
    ),
    path("logout/", auth_views.LogoutView.as_view(next_page="index"), name="logout"),
    # Painel administrativo (somente is_staff)
    path("painel/", RedirectView.as_view(pattern_name="painel_dashboard"), name="painel"),
    path("painel/dashboard/", painel_views.dashboard, name="painel_dashboard"),
    path("painel/reservas/", painel_views.reservas_painel, name="painel_reservas"),
    path("painel/reservas/<int:pk>/situacao/", painel_views.reserva_situacao, name="painel_reserva_situacao"),
    path("painel/usuarios/", painel_views.usuarios_painel, name="painel_usuarios"),
    path("painel/usuarios/<int:pk>/atualizar/", painel_views.usuario_atualizar, name="painel_usuario_atualizar"),
    path("painel/cadastros/", painel_views.cadastros_inicio, name="painel_cadastros_inicio"),
    path("painel/cadastros/<str:aba>/", painel_views.cadastros, name="painel_cadastros"),
    path("painel/cadastros/<str:aba>/<int:pk>/editar/", painel_views.cadastro_editar, name="painel_cadastro_editar"),
    path("painel/cadastros/<str:aba>/<int:pk>/excluir/", painel_views.cadastro_excluir, name="painel_cadastro_excluir"),
    path("painel/veiculos/", painel_views.veiculos_painel, name="painel_veiculos"),
    path("painel/veiculos/<int:pk>/editar/", painel_views.veiculo_editar, name="painel_veiculo_editar"),
    path("painel/veiculos/<int:pk>/excluir/", painel_views.veiculo_excluir, name="painel_veiculo_excluir"),
]