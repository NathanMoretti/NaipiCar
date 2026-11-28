from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .fabrica import criar_cliente, criar_reserva, criar_veiculo, dia
from .models import Reserva

Status = Reserva.Status


class ReservarVeiculoTests(TestCase):
    def setUp(self):
        self.cliente = criar_cliente()
        self.veiculo = criar_veiculo()  # diária de R$ 150,00
        self.url = reverse("reservar_veiculo", args=[self.veiculo.id])

    def reservar(self, retirada, devolucao):
        return self.client.post(self.url, {
            "data_retirada": retirada.isoformat(),
            "data_devolucao": devolucao.isoformat(),
        })

    def test_exige_login(self):
        resposta = self.reservar(dia(1), dia(3))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/login/", resposta.url)
        self.assertEqual(Reserva.objects.count(), 0)

    def test_so_aceita_post(self):
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_cria_reserva_com_os_dados_da_conta(self):
        self.client.force_login(self.cliente)
        resposta = self.reservar(dia(1), dia(4))  # 3 diárias

        self.assertRedirects(resposta, reverse("minhas_reservas"))
        reserva = Reserva.objects.get()
        self.assertEqual(reserva.cliente, self.cliente)
        self.assertEqual(reserva.nome_cliente, "Maria Silva")
        self.assertEqual(reserva.email_cliente, "cliente@teste.com")
        self.assertEqual(reserva.valor_total, Decimal("450.00"))
        self.assertEqual(reserva.status, Status.PENDENTE)

    def test_recusa_periodo_ja_ocupado(self):
        self.client.force_login(self.cliente)
        self.reservar(dia(1), dia(4))
        self.reservar(dia(2), dia(5))  # sobrepõe a primeira
        self.assertEqual(Reserva.objects.count(), 1)

    def test_mesmo_dia_da_devolucao_conta_como_ocupado(self):
        # Comportamento atual: quem retira no dia em que outro devolve ainda é barrado
        self.client.force_login(self.cliente)
        self.reservar(dia(1), dia(4))
        self.reservar(dia(4), dia(6))
        self.assertEqual(Reserva.objects.count(), 1)

    def test_reserva_cancelada_libera_o_periodo(self):
        outro = criar_cliente(email="outro@teste.com", cpf="11144477735")
        criar_reserva(self.veiculo, outro, dia(1), dia(4), status=Status.CANCELADA)
        self.client.force_login(self.cliente)
        self.reservar(dia(2), dia(5))
        self.assertEqual(Reserva.objects.exclude(status=Status.CANCELADA).count(), 1)

    def test_recusa_retirada_no_passado(self):
        self.client.force_login(self.cliente)
        self.reservar(dia(-1), dia(2))
        self.assertEqual(Reserva.objects.count(), 0)

    def test_recusa_devolucao_igual_ou_anterior_a_retirada(self):
        self.client.force_login(self.cliente)
        self.reservar(dia(3), dia(3))
        self.reservar(dia(5), dia(3))
        self.assertEqual(Reserva.objects.count(), 0)

    def test_recusa_veiculo_indisponivel(self):
        self.veiculo.disponivel = False
        self.veiculo.save()
        self.client.force_login(self.cliente)
        self.reservar(dia(1), dia(3))
        self.assertEqual(Reserva.objects.count(), 0)

    def test_recusa_datas_invalidas(self):
        self.client.force_login(self.cliente)
        self.client.post(self.url, {"data_retirada": "abc", "data_devolucao": ""})
        self.assertEqual(Reserva.objects.count(), 0)


class CancelarReservaTests(TestCase):
    def setUp(self):
        self.cliente = criar_cliente()
        self.veiculo = criar_veiculo()
        self.client.force_login(self.cliente)

    def cancelar(self, reserva):
        return self.client.post(reverse("cancelar_reserva", args=[reserva.id]))

    def test_dono_cancela_reserva_futura(self):
        reserva = criar_reserva(self.veiculo, self.cliente, dia(2), dia(4), status=Status.PENDENTE)
        self.cancelar(reserva)
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, Status.CANCELADA)

    def test_nao_cancela_reserva_de_outra_pessoa(self):
        outro = criar_cliente(email="outro@teste.com", cpf="11144477735")
        reserva = criar_reserva(self.veiculo, outro, dia(2), dia(4), status=Status.CONFIRMADA)
        self.assertEqual(self.cancelar(reserva).status_code, 404)
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, Status.CONFIRMADA)

    def test_nao_cancela_reserva_que_ja_comecou(self):
        reserva = criar_reserva(self.veiculo, self.cliente, dia(-1), dia(2), status=Status.CONFIRMADA)
        self.cancelar(reserva)
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, Status.CONFIRMADA)

    def test_nao_cancela_reserva_concluida(self):
        reserva = criar_reserva(self.veiculo, self.cliente, dia(5), dia(7), status=Status.CONCLUIDA)
        self.cancelar(reserva)
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, Status.CONCLUIDA)

    def test_so_aceita_post(self):
        reserva = criar_reserva(self.veiculo, self.cliente, dia(2), dia(4))
        resposta = self.client.get(reverse("cancelar_reserva", args=[reserva.id]))
        self.assertEqual(resposta.status_code, 405)


class MinhasReservasTests(TestCase):
    def test_exige_login(self):
        resposta = self.client.get(reverse("minhas_reservas"))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/login/", resposta.url)

    def test_mostra_somente_as_reservas_do_usuario(self):
        veiculo = criar_veiculo()
        eu = criar_cliente()
        outro = criar_cliente(email="outro@teste.com", cpf="11144477735")
        minha = criar_reserva(veiculo, eu, dia(1), dia(2))
        criar_reserva(veiculo, outro, dia(10), dia(12))

        self.client.force_login(eu)
        resposta = self.client.get(reverse("minhas_reservas"))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual([r.id for r in resposta.context["reservas"]], [minha.id])


class ListaDeVeiculosTests(TestCase):
    def test_filtro_por_periodo_esconde_veiculos_ocupados(self):
        ocupado = criar_veiculo(placa="AAA1A11", modelo="Compass")
        livre = criar_veiculo(placa="BBB2B22", modelo="Renegade")
        cliente = criar_cliente()
        criar_reserva(ocupado, cliente, dia(2), dia(5), status=Status.CONFIRMADA)

        resposta = self.client.get(reverse("veiculos"), {
            "retirada": dia(3).isoformat(),
            "devolucao": dia(4).isoformat(),
        })
        ids = [v.id for v in resposta.context["veiculos"]]
        self.assertEqual(ids, [livre.id])

    def test_pagina_inicial_e_lista_abrem(self):
        criar_veiculo()
        self.assertEqual(self.client.get(reverse("index")).status_code, 200)
        self.assertEqual(self.client.get(reverse("veiculos")).status_code, 200)
