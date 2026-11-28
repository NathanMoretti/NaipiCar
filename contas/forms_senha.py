from django.contrib.auth.forms import PasswordResetForm

from .models import User


class RecuperarSenhaForm(PasswordResetForm):
    """Pedido de nova senha por e-mail.

    O formulário padrão do Django filtra por `is_active=True` direto no banco, mas no
    usuário da NaipiCar `is_active` é uma propriedade calculada (vem da coluna `status`).
    Por isso a busca aqui é feita pela situação da conta.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = "E-mail"
        self.fields["email"].widget.attrs.update({"placeholder": "seuemail@email.com", "autofocus": True})

    def get_users(self, email):
        # Diferente do padrão do Django, contas SEM senha também recebem o link: são as contas
        # criadas pelo administrador no painel, e é por este link que a pessoa cria a senha.
        return User.objects.filter(email__iexact=email.strip(), status=User.ACTIVE)


def enviar_link_criar_senha(request, usuario):
    """Envia para a conta nova (criada no painel) o e-mail com o link para criar a senha."""
    form = RecuperarSenhaForm({"email": usuario.email})
    form.is_valid()
    form.save(
        request=request,
        use_https=request.is_secure(),
        subject_template_name="locacao/email_criar_senha_assunto.txt",
        email_template_name="locacao/email_criar_senha.txt",
    )
