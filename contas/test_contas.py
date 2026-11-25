import re

from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from contas.models import User
from locacao.fabrica import SENHA, criar_cliente

# Os e-mails dos testes ficam na memória (mail.outbox), sem sair do computador
EMAIL_EM_MEMORIA = override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}},
)

NOVA_SENHA = "NovaSenha@456"


@EMAIL_EM_MEMORIA
class RecuperarSenhaTests(TestCase):
    def setUp(self):
        self.cliente = criar_cliente()

    def pedir(self, email):
        return self.client.post(reverse("recuperar_senha"), {"email": email})

    def link_do_email(self):
        corpo = mail.outbox[0].body
        return re.search(r"/redefinir-senha/\S+", corpo).group(0)

    def test_pagina_de_pedido_abre(self):
        self.assertEqual(self.client.get(reverse("recuperar_senha")).status_code, 200)

    def test_conta_ativa_recebe_o_link(self):
        resposta = self.pedir(self.cliente.email)
        self.assertRedirects(resposta, reverse("recuperar_senha_enviado"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.cliente.email])
        self.assertIn("/redefinir-senha/", mail.outbox[0].body)

    def test_email_desconhecido_tem_a_mesma_resposta_e_nao_envia(self):
        resposta = self.pedir("ninguem@teste.com")
        self.assertRedirects(resposta, reverse("recuperar_senha_enviado"))
        self.assertEqual(len(mail.outbox), 0)

    def test_conta_inativa_ou_bloqueada_nao_recebe(self):
        for situacao in (User.INACTIVE, User.BLOCKED, User.PENDING):
            with self.subTest(situacao=situacao):
                self.cliente.status = situacao
                self.cliente.save()
                self.pedir(self.cliente.email)
                self.assertEqual(len(mail.outbox), 0)

    def test_fluxo_completo_troca_a_senha(self):
        self.pedir(self.cliente.email)
        link = self.link_do_email()

        resposta = self.client.get(link, follow=True)
        self.assertTrue(resposta.context["validlink"])
        tela_da_senha = resposta.redirect_chain[-1][0]  # o Django troca o token por uma URL interna

        resposta = self.client.post(tela_da_senha, {"new_password1": NOVA_SENHA, "new_password2": NOVA_SENHA})
        self.assertRedirects(resposta, reverse("redefinir_senha_concluido"))

        self.assertTrue(Client().login(email=self.cliente.email, password=NOVA_SENHA))
        self.assertFalse(Client().login(email=self.cliente.email, password=SENHA))

    def test_link_nao_pode_ser_usado_duas_vezes(self):
        self.pedir(self.cliente.email)
        link = self.link_do_email()
        resposta = self.client.get(link, follow=True)
        tela_da_senha = resposta.redirect_chain[-1][0]
        self.client.post(tela_da_senha, {"new_password1": NOVA_SENHA, "new_password2": NOVA_SENHA})

        de_novo = Client().get(link, follow=True)
        self.assertFalse(de_novo.context["validlink"])

    def test_senha_fraca_e_recusada(self):
        self.pedir(self.cliente.email)
        resposta = self.client.get(self.link_do_email(), follow=True)
        tela_da_senha = resposta.redirect_chain[-1][0]

        resposta = self.client.post(tela_da_senha, {"new_password1": "fraca", "new_password2": "fraca"})
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.context["form"].errors)
        self.assertTrue(Client().login(email=self.cliente.email, password=SENHA))  # senha antiga segue valendo

    def test_link_adulterado_e_invalido(self):
        resposta = self.client.get("/redefinir-senha/MQ/token-falso/", follow=True)
        self.assertFalse(resposta.context["validlink"])


class EditarPerfilTests(TestCase):
    def setUp(self):
        self.cliente = criar_cliente()
        self.client.force_login(self.cliente)
        self.url = reverse("editar_perfil")

    def dados(self, **extra):
        dados = {
            "full_name": "Joana Souza",
            "email": "cliente@teste.com",
            "phone": "(45) 98888-7777",
            "zip_code": "85851-000",
            "street": "Av. das Cataratas",
            "number": "1240",
            "complement": "",
            "neighborhood": "Vila Yolanda",
            "city": "Foz do Iguaçu",
            "state": "PR",
        }
        dados.update(extra)
        return dados

    def test_exige_login(self):
        resposta = Client().post(self.url, self.dados())
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/login/", resposta.url)

    def test_so_aceita_post(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_atualiza_nome_telefone_e_endereco(self):
        resposta = self.client.post(self.url, self.dados())
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.json()["ok"])

        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.full_name, "Joana Souza")
        self.assertEqual(self.cliente.phone, "(45) 98888-7777")
        self.assertEqual(self.cliente.address.city, "Foz do Iguaçu")
        self.assertEqual(self.cliente.address.state, "PR")

    def test_cpf_nao_pode_ser_alterado(self):
        cpf_original = self.cliente.cpf
        self.client.post(self.url, self.dados(cpf="111.444.777-35"))
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.cpf, cpf_original)

    def test_recusa_email_de_outra_conta(self):
        criar_cliente(email="outro@teste.com", cpf="11144477735")
        resposta = self.client.post(self.url, self.dados(email="outro@teste.com"))
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("email", resposta.json()["erros"])
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.email, "cliente@teste.com")

    def test_trocar_senha_exige_a_senha_atual(self):
        resposta = self.client.post(self.url, self.dados(password1=NOVA_SENHA, password2=NOVA_SENHA))
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("senha_atual", resposta.json()["erros"])

        resposta = self.client.post(self.url, self.dados(
            senha_atual="errada", password1=NOVA_SENHA, password2=NOVA_SENHA))
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("senha_atual", resposta.json()["erros"])
        self.assertTrue(Client().login(email=self.cliente.email, password=SENHA))

    def test_troca_a_senha_e_mantem_a_sessao(self):
        resposta = self.client.post(self.url, self.dados(
            senha_atual=SENHA, password1=NOVA_SENHA, password2=NOVA_SENHA))
        self.assertEqual(resposta.status_code, 200)

        self.assertTrue(Client().login(email=self.cliente.email, password=NOVA_SENHA))
        self.assertFalse(Client().login(email=self.cliente.email, password=SENHA))
        # Continua logado depois de trocar a senha
        self.assertEqual(self.client.get(reverse("minhas_reservas")).status_code, 200)

    def test_nova_senha_fraca_e_recusada(self):
        resposta = self.client.post(self.url, self.dados(
            senha_atual=SENHA, password1="fraca", password2="fraca"))
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("password1", resposta.json()["erros"])

    def test_sem_mexer_na_senha_ela_continua_a_mesma(self):
        self.client.post(self.url, self.dados())
        self.assertTrue(Client().login(email=self.cliente.email, password=SENHA))
