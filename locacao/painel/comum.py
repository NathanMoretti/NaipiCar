"""Peças usadas por todas as telas do painel: acesso, rótulos das situações e formatação."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect, resolve_url

from ..models import Reserva

Status = Reserva.Status


def somente_admin(view):
    """Só administradores (is_staff) entram.

    Quem não está logado vai para o login. Quem está logado como cliente volta para
    o site com um aviso (sem isso, o login devolvia o cliente ao painel, em loop).
    """

    @wraps(view)
    def interna(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), resolve_url("login"))
        if not request.user.is_staff:
            messages.error(request, "Você não tem permissão para acessar o painel.")
            return redirect("index")
        return view(request, *args, **kwargs)

    return interna


# "Atrasado" não existe no banco: é calculado (reserva Confirmada com devolução vencida).
ROTULOS_SITUACAO = {
    Status.PENDENTE: ("Em análise", "pendente"),
    Status.CONFIRMADA: ("Reservado", "confirmada"),
    Status.CONCLUIDA: ("Concluído", "concluida"),
    Status.CANCELADA: ("Cancelado", "cancelada"),
}

# Para qual situação cada reserva pode ser alterada pelo administrador
TRANSICOES = {
    Status.PENDENTE: [Status.PENDENTE, Status.CONFIRMADA, Status.CANCELADA],
    Status.CONFIRMADA: [Status.CONFIRMADA, Status.CONCLUIDA, Status.CANCELADA],
    Status.CONCLUIDA: [Status.CONCLUIDA],
    Status.CANCELADA: [Status.CANCELADA],
}


def rotulo_situacao(reserva, hoje):
    if reserva.status == Status.CONFIRMADA and reserva.data_devolucao < hoje:
        return "Atrasado", "atrasado"
    return ROTULOS_SITUACAO.get(reserva.status, (reserva.status, "concluida"))


def cpf_oculto(cpf):
    cpf = cpf or ""
    return f"{cpf[:3]}.***.***-**" if cpf else "—"


def reais(valor):
    texto = f"{valor:,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")
