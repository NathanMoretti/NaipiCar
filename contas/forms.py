import re

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Address, User
from .validators import formatar_cpf, somente_digitos, validar_cpf

ESTADOS = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA',
           'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']


def aplicar_bootstrap(form):
    """Deixa os campos com a aparência do Bootstrap."""
    for campo in form.fields.values():
        w = campo.widget
        if isinstance(w, forms.CheckboxInput):
            classe = 'form-check-input'
        elif isinstance(w, forms.Select):
            classe = 'form-select'
        else:
            classe = 'form-control'
        w.attrs['class'] = (w.attrs.get('class', '') + ' ' + classe).strip()


class LoginForm(AuthenticationForm):
    """RF02: o login é feito com e-mail e senha."""
    error_messages = {
        'invalid_login': 'E-mail ou senha incorretos.',
        'inactive': 'Esta conta não está ativa. Fale com a locadora.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'E-mail'
        self.fields['username'].widget = forms.EmailInput(
            attrs={'autofocus': True, 'placeholder': 'seuemail@email.com'})
        self.fields['password'].label = 'Senha'
        aplicar_bootstrap(self)

    def clean_username(self):
        return self.cleaned_data['username'].strip().lower()


class CadastroForm(forms.Form):
    """RF01: cadastro do cliente, como no protótipo (usuário + endereço)."""
    full_name = forms.CharField(
        label='Nome completo', max_length=101,
        widget=forms.TextInput(attrs={'placeholder': 'Digite seu nome completo'}))
    cpf = forms.CharField(
        label='CPF', max_length=14, widget=forms.TextInput(attrs={'placeholder': '123.456.789-10'}))
    email = forms.EmailField(
        label='E-mail', max_length=70,
        widget=forms.EmailInput(attrs={'placeholder': 'seuemail@email.com'}))
    phone = forms.CharField(
        label='Telefone', max_length=20, widget=forms.TextInput(attrs={'placeholder': '(45) 99999-9999'}))

    zip_code = forms.CharField(
        label='CEP', max_length=9, widget=forms.TextInput(attrs={'placeholder': '85851-000'}))
    street = forms.CharField(
        label='Rua', max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Digite a rua'}))
    number = forms.CharField(label='Número', max_length=10, widget=forms.TextInput(attrs={'placeholder': '123'}))
    complement = forms.CharField(
        label='Complemento', max_length=50, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Opcional'}))
    neighborhood = forms.CharField(
        label='Bairro', max_length=60, widget=forms.TextInput(attrs={'placeholder': 'Digite o bairro'}))
    city = forms.CharField(
        label='Cidade', max_length=60, widget=forms.TextInput(attrs={'placeholder': 'Foz do Iguaçu'}))
    state = forms.ChoiceField(
        label='Estado', initial='PR', choices=[(uf, uf) for uf in ESTADOS])

    password1 = forms.CharField(
        label='Senha', widget=forms.PasswordInput,
        help_text='Use 8+ caracteres, letra maiúscula, número e símbolo.')
    password2 = forms.CharField(label='Confirmar senha', widget=forms.PasswordInput)
    accept_terms = forms.BooleanField(
        label='Li e concordo com os Termos de uso e Política de privacidade.',
        error_messages={'required': 'Aceite os termos de uso para criar a conta.'})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_bootstrap(self)

    # --- validações campo a campo ----------------------------------------
    def clean_full_name(self):
        partes = self.cleaned_data['full_name'].split()
        if len(partes) < 2:
            raise ValidationError('Informe o nome e o sobrenome.')
        if len(partes[0]) > 50 or len(' '.join(partes[1:])) > 50:
            raise ValidationError('Nome ou sobrenome muito longo.')
        return ' '.join(partes)

    def clean_cpf(self):
        valor = self.cleaned_data['cpf']
        validar_cpf(valor)
        cpf = formatar_cpf(valor)
        if User.objects.filter(cpf=cpf).exists():
            raise ValidationError('Já existe um cadastro com este CPF.')
        return cpf

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError('Já existe um cadastro com este e-mail.')
        return email

    def clean_phone(self):
        d = somente_digitos(self.cleaned_data['phone'])
        if len(d) not in (10, 11):
            raise ValidationError('Informe o telefone com DDD, por exemplo (45) 99999-9999.')
        if len(d) == 11:
            return f'({d[:2]}) {d[2:7]}-{d[7:]}'
        return f'({d[:2]}) {d[2:6]}-{d[6:]}'

    def clean_zip_code(self):
        d = somente_digitos(self.cleaned_data['zip_code'])
        if len(d) != 8:
            raise ValidationError('Informe um CEP com 8 números.')
        return f'{d[:5]}-{d[5:]}'

    def clean(self):
        dados = super().clean()
        p1, p2 = dados.get('password1'), dados.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'As senhas não conferem.')
        elif p1:
            try:
                password_validation.validate_password(p1)  # RN04
            except ValidationError as erro:
                self.add_error('password1', erro)
        return dados

    # --- gravação ----------------------------------------------------------
    @transaction.atomic
    def save(self):
        d = self.cleaned_data
        nome, _, sobrenome = d['full_name'].partition(' ')
        endereco = Address.objects.create(
            street=d['street'], number=d['number'], complement=d['complement'],
            neighborhood=d['neighborhood'], city=d['city'], state=d['state'],
            zip_code=d['zip_code'])
        return User.objects.create_user(
            d['email'], d['password1'], first_name=nome, last_name=sobrenome,
            cpf=d['cpf'], phone=d['phone'], address=endereco, profile_type=User.USER)
