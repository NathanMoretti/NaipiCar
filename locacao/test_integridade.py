"""Testes de integridade: reservas simultâneas, histórico protegido, regras no banco e configuração."""
import os
import subprocess
import sys
import threading
import time
from decimal import Decimal
from unittest import mock, skipUnless

from django.conf import settings
from django.db import IntegrityError, connection, transaction
from django.db.models import ProtectedError
from django.db.models.query import QuerySet
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from .fabrica import criar_cliente, criar_reserva, criar_veiculo, dia
from .models import CategoriaClasse, Reserva, Veiculo


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


class RegrasNoBancoTests(TestCase):
    """CheckConstraint: o próprio banco recusa dados inválidos, mesmo gravando sem passar pelas telas."""

    def setUp(self):
        self.cliente = criar_cliente()
        self.veiculo = criar_veiculo()

    def gravar_reserva(self, retirada, devolucao, valor="100.00"):
        Reserva.objects.create(veiculo=self.veiculo, cliente=self.cliente, data_retirada=retirada,
                               data_devolucao=devolucao, valor_total=Decimal(valor))

    def test_devolucao_precisa_ser_depois_da_retirada(self):
        for nome, (ret, dev) in {"mesmo dia": (dia(3), dia(3)), "antes": (dia(5), dia(3))}.items():
            with self.subTest(nome), self.assertRaises(IntegrityError), transaction.atomic():
                self.gravar_reserva(ret, dev)
        self.assertFalse(Reserva.objects.exists())

    def test_valor_total_nao_pode_ser_negativo(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.gravar_reserva(dia(1), dia(2), valor="-10.00")

    def test_quilometragem_e_diaria_nao_podem_ser_negativas(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Veiculo.objects.filter(pk=self.veiculo.pk).update(quilometragem=-1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CategoriaClasse.objects.update(daily_rate=Decimal("-1"))


class ConfiguracaoDeProducaoTests(TestCase):
    """Com DEBUG=False o sistema não pode iniciar com a chave de exemplo (seria uma chave conhecida)."""

    def checar(self, **env):
        ambiente = {**os.environ, "DB_ENGINE": "sqlite", **env}
        return subprocess.run([sys.executable, "manage.py", "check"], cwd=settings.BASE_DIR,
                              env=ambiente, capture_output=True, text=True)

    def test_debug_false_sem_secret_key_propria_nao_inicia(self):
        for chave in ("", "troque-por-uma-chave-secreta"):
            with self.subTest(chave=chave):
                resultado = self.checar(DEBUG="False", SECRET_KEY=chave)
                self.assertNotEqual(resultado.returncode, 0)
                self.assertIn("defina uma SECRET_KEY", resultado.stderr)

    def test_debug_false_com_secret_key_propria_inicia(self):
        resultado = self.checar(DEBUG="False", SECRET_KEY="x" * 60 + "uma-chave-de-teste-bem-longa")
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
