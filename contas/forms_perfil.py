from django import forms
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.db import transaction

from .forms import CadastroForm
from .models import User

TAMANHO_MAXIMO_FOTO = 5 * 1024 * 1024  # 5 MB


class PerfilForm(CadastroForm):
    """Edição do perfil do cliente.

    Reaproveita as validações do cadastro (nome, telefone, CEP, endereço), com estas diferenças:
    - o CPF não aparece, porque não pode ser alterado depois do cadastro;
    - a senha é opcional, mas para trocá-la é preciso informar a senha atual;
    - há um campo para a foto do perfil.
    """

    foto = forms.ImageField(
        required=False, widget=forms.FileInput(attrs={"accept": "image/png,image/jpeg"})
    )
    senha_atual = forms.CharField(required=False, widget=forms.PasswordInput)

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        del self.fields["cpf"]
        del self.fields["accept_terms"]
        self.fields["password1"].required = False
        self.fields["password2"].required = False
        # O modal usa o estilo próprio do site, sem as classes do Bootstrap
        for campo in self.fields.values():
            campo.widget.attrs.pop("class", None)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email=email).exclude(pk=self.user.pk).exists():
            raise ValidationError("Já existe um cadastro com este e-mail.")
        return email

    def clean_foto(self):
        foto = self.cleaned_data.get("foto")
        if foto:
            if foto.size > TAMANHO_MAXIMO_FOTO:
                raise ValidationError("A foto deve ter no máximo 5MB.")
            formato = getattr(getattr(foto, "image", None), "format", None)
            if formato not in ("JPEG", "PNG"):
                raise ValidationError("Envie a foto em PNG ou JPG.")
        return foto

    def clean(self):
        # Pula o clean() do cadastro, que exige a senha, e faz a regra própria do perfil
        dados = super(CadastroForm, self).clean()
        atual = dados.get("senha_atual")
        p1, p2 = dados.get("password1"), dados.get("password2")

        if atual or p1 or p2:  # só valida a senha se a pessoa tentou trocá-la
            if not atual:
                self.add_error("senha_atual", "Informe a senha atual para trocar a senha.")
            elif not self.user.check_password(atual):
                self.add_error("senha_atual", "A senha atual está incorreta.")

            if not p1:
                self.add_error("password1", "Informe a nova senha.")
            elif p1 != p2:
                self.add_error("password2", "As senhas não conferem.")
            else:
                try:
                    password_validation.validate_password(p1, self.user)
                except ValidationError as erro:
                    self.add_error("password1", erro)
        return dados

    @transaction.atomic
    def save(self):
        d = self.cleaned_data
        usuario = self.user

        nome, _, sobrenome = d["full_name"].partition(" ")
        usuario.first_name, usuario.last_name = nome, sobrenome
        usuario.email = d["email"]
        usuario.phone = d["phone"]
        if d.get("foto"):
            usuario.profile_photo = d["foto"]
        if d.get("password1"):
            usuario.set_password(d["password1"])
        usuario.save()

        endereco = usuario.address
        endereco.street = d["street"]
        endereco.number = d["number"]
        endereco.complement = d["complement"]
        endereco.neighborhood = d["neighborhood"]
        endereco.city = d["city"]
        endereco.state = d["state"]
        endereco.zip_code = d["zip_code"]
        endereco.save()
        return usuario
