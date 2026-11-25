from django.test import Client, TestCase
from django.urls import reverse

from contas.models import User

from .fabrica import SENHA, criar_admin, criar_cliente, criar_reserva, criar_veiculo, dia
from .forms import VeiculoForm
from .models import Categoria, CategoriaClasse, ClasseCarro, Marca, ModeloCarro, Reserva, Veiculo

ABAS = ["marcas", "modelos", "categorias", "classes", "diarias"]


def urls_do_painel():
    return (
        [reverse(nome) for nome in ["painel_dashboard", "painel_veiculos", "painel_reservas", "painel_usuarios"]]
        + [reverse("painel_cadastros", args=[aba]) for aba in ABAS]
    )


class AcessoAoPainelTests(TestCase):
    def setUp(self):
        self.admin = criar_admin()
        self.cliente = criar_cliente()
        # Dados variados para as telas renderizarem listas, radar e gráficos
        veiculo = criar_veiculo()
        criar_reserva(veiculo, self.cliente, dia(-5), dia(-1), status="Confirmada")  # atrasada
        criar_reserva(veiculo, self.cliente, dia(0), dia(2), status="Pendente")
        criar_reserva(veiculo, self.cliente, dia(10), dia(12), status="Cancelada")

    def test_visitante_vai_para_o_login(self):
        for url in urls_do_painel():
            with self.subTest(url=url):
                resposta = self.client.get(url)
                self.assertEqual(resposta.status_code, 302)
                self.assertIn("/login/", resposta.url)

    def test_cliente_volta_para_o_site_sem_entrar_em_loop(self):
        self.client.force_login(self.cliente)
        for url in urls_do_painel():
            with self.subTest(url=url):
                resposta = self.client.get(url)
                self.assertRedirects(resposta, reverse("index"), fetch_redirect_response=False)
        # Seguindo os redirecionamentos, termina em uma página normal
        self.assertEqual(self.client.get(urls_do_painel()[0], follow=True).status_code, 200)

    def test_admin_abre_todas_as_telas(self):
        self.client.force_login(self.admin)
        for url in urls_do_painel():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_aba_de_cadastro_inexistente_da_404(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("painel_cadastros", args=["xpto"])).status_code, 404)

    def test_dashboard_conta_atrasos_e_mostra_no_radar(self):
        self.client.force_login(self.admin)
        resposta = self.client.get(reverse("painel_dashboard"))
        self.assertEqual(resposta.context["atrasos"], 1)
        acoes = [linha["acao"] for linha in resposta.context["radar"]]
        self.assertIn("Atrasado", acoes)


class VeiculosPainelTests(TestCase):
    def setUp(self):
        self.admin = criar_admin()
        self.cliente = criar_cliente()
        self.veiculo = criar_veiculo(placa="AAA1A11")
        self.client.force_login(self.admin)

    def dados(self, **extra):
        dados = {
            "modelo": self.veiculo.modelo_id,
            "categoria_classe": self.veiculo.categoria_classe_id,
            "placa": "XYZ9A87",
            "ano": 2024,
            "quilometragem": 0,
            "disponivel": "True",
        }
        if "motorizacao" in VeiculoForm.base_fields:
            escolhas = VeiculoForm.base_fields["motorizacao"].choices
            dados["motorizacao"] = next(valor for valor, _ in escolhas if valor)
        dados.update(extra)
        return dados

    def test_cadastra_com_placa_normalizada(self):
        resposta = self.client.post(reverse("painel_veiculos"), self.dados(placa="xyz-9a87"))
        self.assertRedirects(resposta, reverse("painel_veiculos"), fetch_redirect_response=False)
        self.assertTrue(Veiculo.objects.filter(placa="XYZ9A87").exists())

    def test_placa_invalida_nao_cadastra_e_mostra_o_erro(self):
        resposta = self.client.post(reverse("painel_veiculos"), self.dados(placa="AB-12"))
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("placa", resposta.context["form"].errors)
        self.assertEqual(Veiculo.objects.count(), 1)

    def test_placa_repetida_nao_cadastra(self):
        self.client.post(reverse("painel_veiculos"), self.dados(placa="aaa1a11"))
        self.assertEqual(Veiculo.objects.count(), 1)

    def test_edita_um_veiculo(self):
        url = reverse("painel_veiculo_editar", args=[self.veiculo.id])
        self.client.post(url, self.dados(placa="AAA1A11", ano=2021))
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.ano, 2021)

    def test_nao_exclui_veiculo_com_reserva(self):
        criar_reserva(self.veiculo, self.cliente, dia(1), dia(3))
        self.client.post(reverse("painel_veiculo_excluir", args=[self.veiculo.id]))
        self.assertTrue(Veiculo.objects.filter(id=self.veiculo.id).exists())
        self.assertEqual(Reserva.objects.count(), 1)

    def test_exclui_veiculo_sem_reserva(self):
        self.client.post(reverse("painel_veiculo_excluir", args=[self.veiculo.id]))
        self.assertFalse(Veiculo.objects.filter(id=self.veiculo.id).exists())

    def test_avisa_ao_tornar_indisponivel_com_reserva_em_aberto(self):
        criar_reserva(self.veiculo, self.cliente, dia(1), dia(3), status="Confirmada")
        url = reverse("painel_veiculo_editar", args=[self.veiculo.id])
        resposta = self.client.post(url, self.dados(placa="AAA1A11", disponivel="False"), follow=True)
        mensagens = [str(m).lower() for m in resposta.context["messages"]]
        self.assertTrue(any("indispon" in m and "reserva" in m for m in mensagens), mensagens)

    def test_cliente_nao_cadastra_nem_exclui(self):
        self.client.force_login(self.cliente)
        self.client.post(reverse("painel_veiculos"), self.dados(placa="XYZ9A87"))
        self.client.post(reverse("painel_veiculo_excluir", args=[self.veiculo.id]))
        self.assertEqual(Veiculo.objects.count(), 1)


class ReservasPainelTests(TestCase):
    def setUp(self):
        self.admin = criar_admin()
        self.cliente = criar_cliente()
        self.veiculo = criar_veiculo()
        self.client.force_login(self.admin)

    def mudar(self, reserva, novo_status):
        url = reverse("painel_reserva_situacao", args=[reserva.id])
        self.client.post(url, {"status": novo_status})
        reserva.refresh_from_db()
        return reserva.status

    def test_segue_o_fluxo_normal(self):
        reserva = criar_reserva(self.veiculo, self.cliente, dia(1), dia(3), status="Pendente")
        self.assertEqual(self.mudar(reserva, "Confirmada"), "Confirmada")
        self.assertEqual(self.mudar(reserva, "Concluída"), "Concluída")

    def test_nao_volta_atras_depois_de_finalizada(self):
        concluida = criar_reserva(self.veiculo, self.cliente, dia(-5), dia(-3), status="Concluída")
        self.assertEqual(self.mudar(concluida, "Pendente"), "Concluída")
        cancelada = criar_reserva(self.veiculo, self.cliente, dia(20), dia(22), status="Cancelada")
        self.assertEqual(self.mudar(cancelada, "Confirmada"), "Cancelada")

    def test_nao_pula_de_pendente_para_concluida(self):
        reserva = criar_reserva(self.veiculo, self.cliente, dia(1), dia(3), status="Pendente")
        self.assertEqual(self.mudar(reserva, "Concluída"), "Pendente")

    def test_recusa_situacao_inexistente(self):
        reserva = criar_reserva(self.veiculo, self.cliente, dia(1), dia(3), status="Pendente")
        self.assertEqual(self.mudar(reserva, "Atrasado"), "Pendente")

    def test_cliente_nao_altera_situacao(self):
        reserva = criar_reserva(self.veiculo, self.cliente, dia(1), dia(3), status="Pendente")
        self.client.force_login(self.cliente)
        self.assertEqual(self.mudar(reserva, "Confirmada"), "Pendente")

    def test_busca_pelo_codigo_da_reserva(self):
        reserva = criar_reserva(self.veiculo, self.cliente, dia(1), dia(3))
        criar_reserva(self.veiculo, self.cliente, dia(10), dia(12))
        resposta = self.client.get(reverse("painel_reservas"), {"q": f"RES-{reserva.id:04d}"})
        self.assertEqual([r.id for r in resposta.context["reservas"]], [reserva.id])

    def test_filtro_atrasado_considera_so_confirmadas_vencidas(self):
        atrasada = criar_reserva(self.veiculo, self.cliente, dia(-5), dia(-1), status="Confirmada")
        criar_reserva(self.veiculo, self.cliente, dia(-9), dia(-7), status="Concluída")
        resposta = self.client.get(reverse("painel_reservas"), {"situacao": "atrasado"})
        self.assertEqual([r.id for r in resposta.context["reservas"]], [atrasada.id])


class CadastrosPainelTests(TestCase):
    def setUp(self):
        self.admin = criar_admin()
        self.client.force_login(self.admin)

    def test_nao_exclui_marca_com_modelos(self):
        veiculo = criar_veiculo()
        marca = veiculo.modelo.marca
        self.client.post(reverse("painel_cadastro_excluir", args=["marcas", marca.pk]))
        self.assertTrue(Marca.objects.filter(pk=marca.pk).exists())
        self.assertTrue(ModeloCarro.objects.filter(marca=marca).exists())

    def test_exclui_marca_sem_modelos(self):
        marca = Marca.objects.create(nome="Fiat")
        self.client.post(reverse("painel_cadastro_excluir", args=["marcas", marca.pk]))
        self.assertFalse(Marca.objects.filter(pk=marca.pk).exists())

    def test_nao_exclui_modelo_com_veiculos(self):
        veiculo = criar_veiculo()
        self.client.post(reverse("painel_cadastro_excluir", args=["modelos", veiculo.modelo_id]))
        self.assertTrue(ModeloCarro.objects.filter(pk=veiculo.modelo_id).exists())

    def test_nao_exclui_categoria_com_diarias_nem_diaria_em_uso(self):
        veiculo = criar_veiculo()
        combinacao = veiculo.categoria_classe
        self.client.post(reverse("painel_cadastro_excluir", args=["categorias", combinacao.categoria_id]))
        self.client.post(reverse("painel_cadastro_excluir", args=["diarias", combinacao.pk]))
        self.assertTrue(Categoria.objects.filter(pk=combinacao.categoria_id).exists())
        self.assertTrue(CategoriaClasse.objects.filter(pk=combinacao.pk).exists())

    def test_marca_duplicada_sem_diferenciar_maiusculas(self):
        Marca.objects.create(nome="Toyota")
        self.client.post(reverse("painel_cadastros", args=["marcas"]), {"nome": "toyota"})
        self.assertEqual(Marca.objects.count(), 1)

    def test_cadastra_marca(self):
        self.client.post(reverse("painel_cadastros", args=["marcas"]), {"nome": "  Honda  "})
        self.assertTrue(Marca.objects.filter(nome="Honda").exists())

    def test_diaria_repetida_e_diaria_zero_sao_recusadas(self):
        veiculo = criar_veiculo()
        combinacao = veiculo.categoria_classe
        url = reverse("painel_cadastros", args=["diarias"])
        base = {"categoria": combinacao.categoria_id, "classe": combinacao.classe_id}

        self.client.post(url, {**base, "daily_rate": "300.00"})  # combinação já existe
        outra_classe = ClasseCarro.objects.create(nome="Classe B")
        self.client.post(url, {"categoria": combinacao.categoria_id, "classe": outra_classe.id, "daily_rate": "0"})
        self.assertEqual(CategoriaClasse.objects.count(), 1)

        self.client.post(url, {"categoria": combinacao.categoria_id, "classe": outra_classe.id, "daily_rate": "200.00"})
        self.assertEqual(CategoriaClasse.objects.count(), 2)


class UsuariosPainelTests(TestCase):
    def setUp(self):
        self.admin = criar_admin()
        self.cliente = criar_cliente()
        self.client.force_login(self.admin)

    def atualizar(self, alvo, status, perfil):
        url = reverse("painel_usuario_atualizar", args=[alvo.id])
        self.client.post(url, {"status": status, "perfil": perfil})
        alvo.refresh_from_db()
        return alvo

    def test_desativar_conta_impede_o_login(self):
        self.assertTrue(Client().login(email=self.cliente.email, password=SENHA))
        self.atualizar(self.cliente, User.INACTIVE, User.USER)
        self.assertEqual(self.cliente.status, User.INACTIVE)
        self.assertFalse(Client().login(email=self.cliente.email, password=SENHA))

    def test_promove_cliente_a_administrador(self):
        self.atualizar(self.cliente, User.ACTIVE, User.ADMIN)
        self.assertTrue(self.cliente.is_staff)

    def test_admin_nao_altera_a_propria_conta(self):
        self.atualizar(self.admin, User.INACTIVE, User.USER)
        self.assertEqual(self.admin.status, User.ACTIVE)
        self.assertEqual(self.admin.profile_type, User.ADMIN)

    def test_recusa_valores_invalidos(self):
        self.atualizar(self.cliente, "XPTO", User.USER)
        self.atualizar(self.cliente, User.ACTIVE, 99)
        self.assertEqual(self.cliente.status, User.ACTIVE)
        self.assertEqual(self.cliente.profile_type, User.USER)

    def test_cliente_comum_nao_altera_ninguem(self):
        outro = criar_cliente(email="outro@teste.com", cpf="39053344705")
        self.client.force_login(self.cliente)
        self.atualizar(outro, User.BLOCKED, User.ADMIN)
        self.assertEqual(outro.status, User.ACTIVE)
        self.assertEqual(outro.profile_type, User.USER)

    def test_busca_por_nome_e_filtro_de_perfil(self):
        resposta = self.client.get(reverse("painel_usuarios"), {"q": "maria", "perfil": "cliente"})
        self.assertEqual([u.id for u in resposta.context["usuarios"]], [self.cliente.id])
        resposta = self.client.get(reverse("painel_usuarios"), {"perfil": "admin"})
        self.assertEqual([u.id for u in resposta.context["usuarios"]], [self.admin.id])
