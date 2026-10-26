import re

from django.core.exceptions import ValidationError


class SenhaNaipiCarValidator:
    """RN04: mínimo de 8 caracteres, 1 letra maiúscula, 1 número e 1 símbolo."""

    def validate(self, password, user=None):
        faltando = []
        if len(password) < 8:
            faltando.append('pelo menos 8 caracteres')
        if not re.search(r'[A-Z]', password):
            faltando.append('uma letra maiúscula')
        if not re.search(r'\d', password):
            faltando.append('um número')
        if not re.search(r'[^\w\s]|_', password):
            faltando.append('um símbolo (por exemplo @, # ou !)')
        if faltando:
            raise ValidationError(
                'A senha precisa ter ' + ', '.join(faltando) + '.', code='senha_fraca')

    def get_help_text(self):
        return 'Use 8+ caracteres, letra maiúscula, número e símbolo.'


def somente_digitos(texto):
    return re.sub(r'\D', '', texto or '')


def validar_cpf(valor):
    """Confere os dígitos verificadores do CPF."""
    digitos = somente_digitos(valor)
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        raise ValidationError('Informe um CPF válido.')
    for i in (9, 10):
        soma = sum(int(digitos[n]) * (i + 1 - n) for n in range(i))
        if (soma * 10 % 11) % 10 != int(digitos[i]):
            raise ValidationError('Informe um CPF válido.')


def formatar_cpf(valor):
    d = somente_digitos(valor)
    return f'{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}' if len(d) == 11 else valor
