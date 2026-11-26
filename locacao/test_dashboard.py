from django.test import TestCase
from django.urls import reverse

from .fabrica import criar_admin, criar_cliente, criar_reserva, criar_veiculo, dia
from .painel_views import PERIODOS


class DashboardTests(TestCase):
    def setUp(self):
        self.admin = criar_admin()
        self.cliente = criar_cliente()
        self.veiculo = criar_veiculo(placa="AAA1A11")  # SUV, R$ 150 por diária
        self.client.force_login(self.admin)
        self.url = reverse("painel_dashboard")

    def abrir(self, **filtros):
        resposta = self.client.get(self.url, filtros)
        self.assertEqual(resposta.status_code, 200)
        return resposta

    def cartao(self, resposta, rotulo):
        return next(c for c in resposta.context["cartoes"] if c["rotulo"] == rotulo)

    # --- períodos ----------------------------------------------------------------
    def test_todos_os_periodos_abrem(self):
        criar_reserva(self.veiculo, self.cliente, dia(-3), dia(-1), status="Confirmada")
        for chave, _ in PERIODOS:
            with self.subTest(periodo=chave):
                self.abrir(periodo=chave)

    def test_periodo_personalizado_valido(self):
        resposta = self.abrir(periodo="personalizado", de=dia(-10).isoformat(), ate=dia(-1).isoformat())
        self.assertEqual(resposta.context["chave"], "personalizado")
        self.assertEqual(resposta.context["dias"], 10)

    def test_periodo_personalizado_invalido_volta_para_30_dias(self):
        for filtros in [
            {"de": "abc", "ate": "xyz"},
            {"de": dia(0).isoformat(), "ate": dia(-5).isoformat()},        # fim antes do início
            {"de": dia(-900).isoformat(), "ate": dia(0).isoformat()},      # período longo demais
        ]:
            with self.subTest(filtros=filtros):
                resposta = self.abrir(periodo="personalizado", **filtros)
                self.assertEqual(resposta.context["chave"], "30d")
                self.assertEqual(resposta.context["dias"], 30)

    def test_periodo_desconhecido_usa_30_dias(self):
        self.assertEqual(self.abrir(periodo="xpto").context["dias"], 30)

    # --- indicadores ---------------------------------------------------------------
    def test_receita_e_reservas_do_periodo_sem_contar_canceladas(self):
        criar_reserva(self.veiculo, self.cliente, dia(-5), dia(-2), status="Confirmada")   # 3 diárias = R$ 450
        criar_reserva(self.veiculo, self.cliente, dia(-20), dia(-18), status="Cancelada")  # não conta
        resposta = self.abrir(periodo="30d")
        self.assertEqual(self.cartao(resposta, "Receita estimada")["valor"], "R$ 450,00")
        self.assertEqual(self.cartao(resposta, "Reservas")["valor"], 1)
        self.assertEqual(self.cartao(resposta, "Ticket médio")["valor"], "R$ 450,00")
        self.assertEqual(self.cartao(resposta, "Taxa de cancelamento")["valor"], "50%")

    def test_variacao_em_relacao_ao_periodo_anterior(self):
        criar_reserva(self.veiculo, self.cliente, dia(-40), dia(-37), status="Concluída")  # anterior: R$ 450
        criar_reserva(self.veiculo, self.cliente, dia(-10), dia(-4), status="Concluída")   # atual: R$ 900
        resposta = self.abrir(periodo="30d")
        self.assertEqual(self.cartao(resposta, "Receita estimada")["var"], 100)

    def test_sem_periodo_anterior_nao_mostra_variacao(self):
        criar_reserva(self.veiculo, self.cliente, dia(-3), dia(-1), status="Concluída")
        self.assertIsNone(self.cartao(self.abrir(periodo="30d"), "Receita estimada")["var"])

    def test_taxa_de_ocupacao(self):
        # 1 veículo, 7 dias; alugado 3 deles (dia -6 até -3): 3/7 = 43%
        criar_reserva(self.veiculo, self.cliente, dia(-6), dia(-3), status="Confirmada")
        self.assertEqual(self.cartao(self.abrir(periodo="7d"), "Taxa de ocupação")["valor"], "43%")

    def test_ocupacao_nunca_passa_de_100(self):
        criar_reserva(self.veiculo, self.cliente, dia(-30), dia(30), status="Confirmada")
        self.assertEqual(self.cartao(self.abrir(periodo="7d"), "Taxa de ocupação")["valor"], "100%")

    def test_dashboard_vazio_nao_quebra(self):
        from .models import Reserva
        Reserva.objects.all().delete()
        for chave, _ in PERIODOS:
            self.abrir(periodo=chave)

    # --- filtro por categoria ---------------------------------------------------------
    def test_filtro_por_categoria(self):
        hatch = criar_veiculo(placa="BBB2B22", modelo="Mobi", categoria="Hatch", diaria="90.00")
        criar_reserva(self.veiculo, self.cliente, dia(-5), dia(-3), status="Concluída")
        criar_reserva(hatch, self.cliente, dia(-5), dia(-3), status="Concluída")

        todas = self.abrir(periodo="30d")
        self.assertEqual(self.cartao(todas, "Reservas")["valor"], 2)

        so_hatch = self.abrir(periodo="30d", categoria=hatch.categoria_classe.categoria_id)
        self.assertEqual(self.cartao(so_hatch, "Reservas")["valor"], 1)
        self.assertEqual([c["nome"] for c in so_hatch.context["categorias"]], ["Hatch"])

    def test_categoria_invalida_e_ignorada(self):
        self.assertEqual(self.abrir(categoria="abc").context["categoria_id"], "")

    # --- gráficos e listas ----------------------------------------------------------------
    def test_grafico_por_dia_e_por_mes(self):
        self.assertEqual(len(self.abrir(periodo="7d").context["serie"]), 7)
        self.assertTrue(self.abrir(periodo="7d").context["por_dia"])
        ano = self.abrir(periodo="ano")
        self.assertEqual(len(ano.context["serie"]), 12)
        self.assertFalse(ano.context["por_dia"])

    def test_reservas_por_situacao_somam_o_total(self):
        criar_reserva(self.veiculo, self.cliente, dia(-9), dia(-8), status="Pendente")
        criar_reserva(self.veiculo, self.cliente, dia(-7), dia(-6), status="Concluída")
        criar_reserva(self.veiculo, self.cliente, dia(-5), dia(-4), status="Cancelada")
        criar_reserva(self.veiculo, self.cliente, dia(-3), dia(-1), status="Confirmada")  # já venceu: atrasada
        situacoes = {s["rotulo"]: s["n"] for s in self.abrir(periodo="30d").context["situacoes"]}
        self.assertEqual(situacoes, {"Em análise": 1, "Reservado": 0, "Atrasado": 1, "Concluído": 1, "Cancelado": 1})

    def test_veiculo_mais_alugado(self):
        outro = criar_veiculo(placa="BBB2B22", modelo="Renegade")
        criar_reserva(self.veiculo, self.cliente, dia(-9), dia(-8), status="Concluída")
        criar_reserva(self.veiculo, self.cliente, dia(-6), dia(-5), status="Concluída")
        criar_reserva(outro, self.cliente, dia(-4), dia(-3), status="Concluída")
        top = self.abrir(periodo="30d").context["top_veiculos"]
        self.assertEqual((top[0]["nome"], top[0]["n"]), ("Jeep Compass", 2))
        self.assertEqual(len(top), 2)

    def test_clientes_que_mais_reservam(self):
        outro = criar_cliente(email="outro@teste.com", cpf="39053344705", first_name="Paulo")
        criar_reserva(self.veiculo, self.cliente, dia(-9), dia(-8), status="Concluída")
        criar_reserva(self.veiculo, self.cliente, dia(-6), dia(-5), status="Concluída")
        criar_reserva(self.veiculo, outro, dia(-4), dia(-3), status="Concluída")
        top = self.abrir(periodo="30d").context["top_clientes"]
        self.assertEqual((top[0]["nome"], top[0]["n"]), ("Maria Silva", 2))

    def test_agenda_dos_proximos_dias(self):
        criar_reserva(self.veiculo, self.cliente, dia(2), dia(5), status="Confirmada")
        agenda = self.abrir().context["agenda"]
        acoes = {(item["acao"], dia_agenda["data"]) for dia_agenda in agenda for item in dia_agenda["itens"]}
        self.assertEqual(acoes, {("Retirada", dia(2)), ("Devolução", dia(5))})

    def test_agenda_ignora_o_que_esta_alem_de_7_dias(self):
        criar_reserva(self.veiculo, self.cliente, dia(10), dia(12), status="Confirmada")
        self.assertEqual(self.abrir().context["agenda"], [])

    def test_alertas_de_pendentes_e_atrasos(self):
        criar_reserva(self.veiculo, self.cliente, dia(1), dia(2), status="Pendente")
        criar_reserva(self.veiculo, self.cliente, dia(-5), dia(-2), status="Confirmada")
        resposta = self.abrir()
        self.assertEqual(resposta.context["pendentes"], 1)
        self.assertEqual(resposta.context["atrasos"], 1)
