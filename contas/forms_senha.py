from django import forms
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
        usuarios = User.objects.filter(email__iexact=email.strip(), status=User.ACTIVE)
        return (u for u in usuarios if u.has_usable_password())
