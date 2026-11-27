"""Testes de integridade: reservas simultâneas e proteção do histórico."""
import threading
import time
from unittest import mock, skipUnless

from django.db import connection
from django.db.models import ProtectedError
from django.db.models.query import QuerySet
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from .fabrica import criar_cliente, criar_reserva, criar_veiculo, dia
from .models import Reserva, Veiculo


class HistoricoProtegidoTests(TestCase):
    """Reserva usa on_delete=PROTECT: apagar veículo ou cliente com reservas é bloqueado no banco."""

    def setUp(self):
        self.cliente = criar_cliente()
        self.veiculo = criar_veiculo()
        criar_reserva(self.veiculo, self.cliente, dia(1), dia(3))

    def test_nao_apaga_veiculo_com_reserva(self):
        with self.assertRaises(ProtectedError):
            self.veiculo.delete()
        self.assertEqual(Reserva.objects.count(), 1)

    def test_nao_apaga_cliente_com_reserva(self):
        with self.assertRaises(ProtectedError):
            self.cliente.delete()
        self.assertEqual(Reserva.objects.count(), 1)

    def test_apaga_veiculo_sem_reserva(self):
        livre = criar_veiculo(placa="XYZ9A87")
        livre.delete()
        self.assertFalse(Veiculo.objects.filter(pk=livre.pk).exists())


@skipUnless(connection.vendor == "mysql", "Travamento de linha (SELECT ... FOR UPDATE) só existe no MySQL")
class ReservasSimultaneasTests(TransactionTestCase):
    """Vários clientes pedindo o mesmo carro, no mesmo período, ao mesmo tempo: só uma reserva pode sair."""

    def test_pedidos_simultaneos_geram_uma_unica_reserva(self):
        cliente = criar_cliente()
        veiculo = criar_veiculo()
        url = reverse("reservar_veiculo", args=[veiculo.id])
        dados = {"data_retirada": dia(5).isoformat(), "data_devolucao": dia(8).isoformat()}

        # Deixa a verificação do período mais lenta, para os pedidos se cruzarem de propósito
        exists_original = QuerySet.exists

        def exists_lento(qs, *args, **kwargs):
            resultado = exists_original(qs, *args, **kwargs)
            if qs.model is Reserva:
                time.sleep(0.3)
            return resultado

        def pedir():
            try:
                c = Client()
                c.force_login(cliente)
                c.post(url, dados)
            finally:
                connection.close()

        with mock.patch.object(QuerySet, "exists", exists_lento):
            threads = [threading.Thread(target=pedir) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        self.assertEqual(Reserva.objects.filter(veiculo=veiculo).count(), 1)
