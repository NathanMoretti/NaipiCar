from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from contas.models import Address
from contas.validators import SenhaNaipiCarValidator, validar_cpf
from django.core.exceptions import ValidationError
from locacao.models import Reserva

User = get_user_model()

DADOS_VALIDOS = {
    'full_name': 'Lucas Almeida Souza',
    'cpf': '529.982.247-25',
    'email': 'Lucas@Email.com',
    'phone': '(45) 99999-9999',
    'zip_code': '85851000',
    'street': 'Av. das Cataratas',
    'number': '4790',
    'complement': '',
    'neighborhood': 'Vila Yolanda',
    'city': 'Foz do Iguaçu',
    'state': 'PR',
    'password1': 'Senha@123',
    'password2': 'Senha@123',
    'accept_terms': 'on',
}


class CadastroTests(TestCase):
    def cadastrar(self, **mudancas):
        dados = {**DADOS_VALIDOS, **mudancas}
        return self.client.post(reverse('cadastro'), dados)

    def test_pagina_de_cadastro_abre(self):
        r = self.client.get(reverse('cadastro'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Nome completo')

    def test_cadastro_valido_cria_usuario_e_endereco(self):
        r = self.cadastrar()
        self.assertRedirects(r, reverse('login'))
        u = User.objects.get(email='lucas@email.com')
        self.assertEqual((u.first_name, u.last_name), ('Lucas', 'Almeida Souza'))
        self.assertEqual(u.cpf, '529.982.247-25')
        self.assertEqual(u.address.zip_code, '85851-000')
        self.assertEqual(u.address.city, 'Foz do Iguaçu')
        self.assertEqual(u.profile_type, User.USER)
        self.assertEqual(u.status, 'ACTIVE')

    def test_senha_fica_criptografada(self):
        self.cadastrar()
        u = User.objects.get(email='lucas@email.com')
        self.assertNotIn('Senha@123', u.password)
        self.assertTrue(u.password.startswith('pbkdf2_'))
        self.assertTrue(u.check_password('Senha@123'))

    def test_senha_fraca_e_recusada(self):
        for senha in ['senha123', 'senha@123', 'Senha@abc', 'Senha123', 'Se@1']:
            r = self.cadastrar(password1=senha, password2=senha)
            self.assertEqual(r.status_code, 200, senha)
            self.assertFalse(User.objects.filter(email='lucas@email.com').exists(), senha)

    def test_senhas_diferentes(self):
        r = self.cadastrar(password2='Outra@123')
        self.assertContains(r, 'As senhas não conferem.')

    def test_cpf_invalido_e_duplicado(self):
        r = self.cadastrar(cpf='123.456.789-10')
        self.assertContains(r, 'Informe um CPF válido.')
        self.cadastrar()
        r = self.cadastrar(email='outro@email.com')
        self.assertContains(r, 'Já existe um cadastro com este CPF.')

    def test_email_duplicado(self):
        self.cadastrar()
        r = self.cadastrar(cpf='111.444.777-35')
        self.assertContains(r, 'Já existe um cadastro com este e-mail.')

    def test_termos_sao_obrigatorios(self):
        dados = {k: v for k, v in DADOS_VALIDOS.items() if k != 'accept_terms'}
        r = self.client.post(reverse('cadastro'), dados)
        self.assertContains(r, 'Aceite os termos de uso')
        self.assertEqual(User.objects.count(), 0)

    def test_exige_nome_e_sobrenome(self):
        r = self.cadastrar(full_name='Lucas')
        self.assertContains(r, 'Informe o nome e o sobrenome.')

    def test_campos_de_endereco_obrigatorios_mas_complemento_opcional(self):
        r = self.cadastrar(street='', complement='')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.exists())
        self.assertEqual(Address.objects.count(), 0)  # nada fica pela metade

    def test_telefone_e_cep_invalidos(self):
        self.assertContains(self.cadastrar(phone='123'), 'Informe o telefone com DDD')
        self.assertContains(self.cadastrar(zip_code='123'), 'Informe um CEP com 8 números.')


class LoginTests(TestCase):
    def setUp(self):
        self.client.post(reverse('cadastro'), DADOS_VALIDOS)

    def test_login_por_email(self):
        r = self.client.post(reverse('login'), {'username': 'Lucas@Email.com', 'password': 'Senha@123'})
        self.assertRedirects(r, reverse('index'))
        self.assertContains(self.client.get(reverse('index')), 'Olá, <strong>Lucas</strong>')

    def test_senha_errada(self):
        r = self.client.post(reverse('login'), {'username': 'lucas@email.com', 'password': 'errada'})
        self.assertContains(r, 'E-mail ou senha incorretos.')

    def test_conta_bloqueada_nao_entra(self):
        User.objects.filter(email='lucas@email.com').update(status='BLOCKED')
        r = self.client.post(reverse('login'), {'username': 'lucas@email.com', 'password': 'Senha@123'})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_admin_vai_para_o_painel(self):
        User.objects.create_superuser(
            'admin@naipicar.com', 'Admin@123', first_name='Admin', last_name='Geral',
            cpf='11144477735', phone='(45) 99999-0000')
        r = self.client.post(reverse('login'), {'username': 'admin@naipicar.com', 'password': 'Admin@123'})
        self.assertRedirects(r, '/admin/', fetch_redirect_response=False)
        self.assertEqual(self.client.get('/admin/').status_code, 200)

    def test_cliente_comum_nao_entra_no_admin(self):
        self.client.post(reverse('login'), {'username': 'lucas@email.com', 'password': 'Senha@123'})
        self.assertEqual(self.client.get('/admin/').status_code, 302)  # manda para o login do admin


class RegrasTests(TestCase):
    def test_validador_de_senha(self):
        v = SenhaNaipiCarValidator()
        v.validate('Senha@123')
        with self.assertRaises(ValidationError):
            v.validate('semsimbolo1A')

    def test_validador_de_cpf(self):
        validar_cpf('529.982.247-25')
        validar_cpf('11144477735')
        for ruim in ['111.111.111-11', '123.456.789-10', '123', '']:
            with self.assertRaises(ValidationError):
                validar_cpf(ruim)

    def test_paginas_existentes_continuam_abrindo(self):
        self.assertEqual(self.client.get(reverse('index')).status_code, 200)
        self.assertEqual(self.client.get(reverse('login')).status_code, 200)
        self.assertEqual(self.client.get(reverse('termos')).status_code, 200)
        self.assertEqual(self.client.get(reverse('minhas_reservas')).status_code, 302)

    def test_texto_da_reserva_usa_nome_completo(self):
        from locacao.models import Categoria, CategoriaClasse, ClasseCarro, Marca, ModeloCarro, Veiculo
        u = User.objects.create_user('a@a.com', 'Senha@123', first_name='Ana', last_name='Lima',
                                     cpf='52998224725', phone='(45) 99999-9999')
        cc = CategoriaClasse.objects.create(
            categoria=Categoria.objects.create(nome='SUV'), classe=ClasseCarro.objects.create(nome='A'),
            daily_rate=100)
        v = Veiculo.objects.create(
            modelo=ModeloCarro.objects.create(marca=Marca.objects.create(nome='Fiat'), nome='Argo'),
            categoria_classe=cc, ano=2024, placa='ABC1D23')
        r = Reserva.objects.create(cliente=u, veiculo=v, data_retirada='2026-12-01',
                                   data_devolucao='2026-12-03', valor_total=200)
        self.assertIn('Ana Lima', str(r))
