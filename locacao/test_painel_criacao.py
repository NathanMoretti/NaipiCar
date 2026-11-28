"""Reservas e usuários criados pelo administrador no painel (atendimento no balcão)."""
import re
from decimal import Decimal

from django.core import mail
from django.test import Client, TestCase
from django.urls import reverse

from contas.models import User

from .fabrica import criar_admin, criar_cliente, criar_reserva, criar_veiculo, dia
from .models import Reserva

NOVA_SENHA = "Nova@Senha9"


class NovaReservaPeloPainelTests(TestCase):
    def setUp(self):
        self.admin = criar_admin()
        self.cliente = criar_cliente()
        self.veiculo = criar_veiculo()  # diária de R$ 150,00
        self.client.force_login(self.admin)
        self.url = reverse("painel_reserva_nova")

    def dados(self, **extra):
        dados = {
            "cliente": self.cliente.pk,
            "veiculo": self.veiculo.pk,
            "data_retirada": dia(0).isoformat(),
            "data_devolucao": dia(3).isoformat(),
            "status": "Confirmada",
        }
        dados.update(extra)
        return dados

    def test_cria_reserva_confirmada_com_valor_calculado(self):
        resposta = self.client.post(self.url, self.dados())
        self.assertRedirects(resposta, reverse("painel_reservas"))
        reserva = Reserva.objects.get()
        self.assertEqual(reserva.cliente, self.cliente)
        self.assertEqual(reserva.status, "Confirmada")
        self.assertEqual(reserva.valor_total, Decimal("450.00"))  # 3 diárias x R$ 150
        self.assertEqual(reserva.nome_cliente, self.cliente.full_name)

    def test_pode_criar_como_em_analise(self):
        self.client.post(self.url, self.dados(status="Pendente"))
        self.assertEqual(Reserva.objects.get().status, "Pendente")

    def test_situacao_invalida_e_recusada(self):
        resposta = self.client.post(self.url, self.dados(status="Concluída"))
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Reserva.objects.exists())

    def test_segue_as_mesmas_regras_do_site(self):
        criar_reserva(self.veiculo, self.cliente, dia(1), dia(2), status="Confirmada")
        casos = {
            "periodo ocupado": self.dados(),
            "retirada no passado": self.dados(data_retirada=dia(-1).isoformat()),
            "devolucao antes da retirada": self.dados(data_retirada=dia(10).isoformat(),
                                                      data_devolucao=dia(9).isoformat()),
        }
        for nome, dados in casos.items():
            with self.subTest(nome):
                resposta = self.client.post(self.url, dados)
                self.assertEqual(resposta.status_code, 200)  # volta para a tela com o pop-up aberto
                self.assertTrue(resposta.context["abrir_nova"])
                self.assertTrue(resposta.context["form_reserva"].non_field_errors())
        self.assertEqual(Reserva.objects.count(), 1)

    def test_veiculo_indisponivel_ou_cliente_inativo_nao_aparecem(self):
        parado = criar_veiculo(placa="XYZ9A87", disponivel=False)
        self.cliente.status = User.BLOCKED
        self.cliente.save()
        resposta = self.client.post(self.url, self.dados(veiculo=parado.pk))
        form = resposta.context["form_reserva"]
        self.assertIn("cliente", form.errors)
        self.assertIn("veiculo", form.errors)
        self.assertFalse(Reserva.objects.exists())

    def test_cliente_nao_pode_criar_pelo_painel(self):
        outro = Client()
        outro.force_login(self.cliente)
        resposta = outro.post(self.url, self.dados())
        self.assertRedirects(resposta, reverse("index"), fetch_redirect_response=False)
        self.assertFalse(Reserva.objects.exists())

    def test_tela_abre_o_pop_up_com_o_cliente_escolhido(self):
        resposta = self.client.get(reverse("painel_reservas"), {"nova": "1", "cliente": self.cliente.pk})
        self.assertTrue(resposta.context["abrir_nova"])
        self.assertContains(resposta, f'<option value="{self.cliente.pk}" selected>')


DADOS_USUARIO = {
    "full_name": "Pedro Henrique Lima",
    "cpf": "390.533.447-05",
    "email": "Pedro@Email.com",
    "phone": "45999998888",
    "zip_code": "85851000",
    "street": "Rua Tarobá",
    "number": "100",
    "complement": "",
    "neighborhood": "Centro",
    "city": "Foz do Iguaçu",
    "state": "PR",
    "profile_type": User.USER,
    "accept_terms": "on",
}


class NovoUsuarioPeloPainelTests(TestCase):
    def setUp(self):
        self.admin = criar_admin()
        self.client.force_login(self.admin)
        self.url = reverse("painel_usuario_novo")

    def test_cria_conta_sem_senha_e_envia_o_link(self):
        resposta = self.client.post(self.url, DADOS_USUARIO)
        self.assertRedirects(resposta, reverse("painel_usuarios"))

        usuario = User.objects.get(email="pedro@email.com")
        self.assertEqual(usuario.full_name, "Pedro Henrique Lima")
        self.assertEqual(usuario.cpf, "390.533.447-05")
        self.assertEqual(usuario.phone, "(45) 99999-8888")
        self.assertEqual(usuario.address.city, "Foz do Iguaçu")
        self.assertEqual(usuario.profile_type, User.USER)
        self.assertFalse(usuario.has_usable_password())  # o admin não define a senha

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["pedro@email.com"])
        self.assertIn("/redefinir-senha/", mail.outbox[0].body)

    def test_pessoa_cria_a_senha_pelo_link_e_entra(self):
        self.client.post(self.url, DADOS_USUARIO)
        link = re.search(r"/redefinir-senha/\S+", mail.outbox[0].body).group(0)

        visitante = Client()
        resposta = visitante.get(link, follow=True)
        self.assertTrue(resposta.context["validlink"])
        tela_da_senha = resposta.redirect_chain[-1][0]
        resposta = visitante.post(tela_da_senha, {"new_password1": NOVA_SENHA, "new_password2": NOVA_SENHA})
        self.assertRedirects(resposta, reverse("redefinir_senha_concluido"))

        self.assertTrue(Client().login(email="pedro@email.com", password=NOVA_SENHA))

    def test_link_expirado_pode_ser_pedido_de_novo_em_esqueci_minha_senha(self):
        self.client.post(self.url, DADOS_USUARIO)
        mail.outbox.clear()
        Client().post(reverse("recuperar_senha"), {"email": "pedro@email.com"})
        self.assertEqual(len(mail.outbox), 1)

    def test_pode_cadastrar_administrador(self):
        self.client.post(self.url, {**DADOS_USUARIO, "profile_type": User.ADMIN})
        self.assertTrue(User.objects.get(email="pedro@email.com").is_staff)

    def test_mesmas_validacoes_do_cadastro_do_site(self):
        cliente = criar_cliente()
        casos = {
            "cpf": {**DADOS_USUARIO, "cpf": cliente.cpf},
            "email": {**DADOS_USUARIO, "email": cliente.email},
            "phone": {**DADOS_USUARIO, "phone": "123"},
            "accept_terms": {k: v for k, v in DADOS_USUARIO.items() if k != "accept_terms"},
        }
        for campo, dados in casos.items():
            with self.subTest(campo):
                resposta = self.client.post(self.url, dados)
                self.assertEqual(resposta.status_code, 200)
                self.assertTrue(resposta.context["abrir_novo"])
                self.assertIn(campo, resposta.context["form_usuario"].errors)
        self.assertFalse(User.objects.filter(email="pedro@email.com").exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_vindo_da_reserva_volta_com_o_cliente_escolhido(self):
        resposta = self.client.post(self.url, {**DADOS_USUARIO, "para_reserva": "1"})
        novo = User.objects.get(email="pedro@email.com")
        self.assertRedirects(resposta, f"{reverse('painel_reservas')}?nova=1&cliente={novo.pk}")

    def test_cliente_nao_pode_cadastrar_pelo_painel(self):
        outro = Client()
        outro.force_login(criar_cliente())
        resposta = outro.post(self.url, DADOS_USUARIO)
        self.assertRedirects(resposta, reverse("index"), fetch_redirect_response=False)
        self.assertFalse(User.objects.filter(email="pedro@email.com").exists())
