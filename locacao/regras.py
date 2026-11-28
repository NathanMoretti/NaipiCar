"""Regras de negócio da reserva, usadas pelo site do cliente e pelo painel do administrador.

Ficam num lugar só para que uma reserva feita no balcão siga exatamente as mesmas regras
de uma reserva feita pelo site (período livre, datas válidas, veículo disponível).
"""
from datetime import date

from django.db import transaction

from .models import Reserva, Veiculo


class ReservaInvalida(Exception):
    """A reserva não pode ser criada; a mensagem explica o motivo para quem está usando o sistema."""


def periodo_ocupado(veiculo, retirada, devolucao):
    """True se o veículo já tem reserva (não cancelada) que encosta no período."""
    return (
        Reserva.objects.filter(veiculo=veiculo, data_retirada__lte=devolucao, data_devolucao__gte=retirada)
        .exclude(status="Cancelada")
        .exists()
    )


def criar_reserva(veiculo_id, cliente, retirada, devolucao, status="Pendente"):
    """Valida as regras e grava a reserva. Levanta ReservaInvalida se algo impedir.

    Verificar o período e gravar a reserva acontecem "de uma vez só": o select_for_update()
    trava a linha do veículo até o fim da transação. Se duas pessoas pedirem o mesmo carro
    ao mesmo tempo, a segunda espera a primeira terminar e já enxerga a reserva dela.
    """
    dias = (devolucao - retirada).days

    with transaction.atomic():
        veiculo = Veiculo.objects.select_for_update().get(id=veiculo_id)

        if not veiculo.disponivel:
            raise ReservaInvalida("Este veículo está indisponível no momento.")
        if not veiculo.diaria:
            raise ReservaInvalida("Este veículo ainda não tem diária cadastrada.")
        if retirada < date.today():
            raise ReservaInvalida("A data de retirada não pode ser no passado.")
        if dias <= 0:
            raise ReservaInvalida("A data de devolução deve ser posterior à data de retirada.")
        if periodo_ocupado(veiculo, retirada, devolucao):
            raise ReservaInvalida("Este veículo já está reservado nesse período.")

        return Reserva.objects.create(
            veiculo=veiculo,
            cliente=cliente,
            nome_cliente=cliente.full_name,
            email_cliente=cliente.email,
            data_retirada=retirada,
            data_devolucao=devolucao,
            valor_total=dias * veiculo.diaria,
            status=status,
        )
