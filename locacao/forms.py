import re
from datetime import date

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

from .models import CategoriaClasse, ModeloCarro, Veiculo

TAMANHO_MAXIMO_FOTO = 5 * 1024 * 1024  # 5 MB
FORMATOS_FOTO = ("JPEG", "PNG")
ANO_MINIMO = 1990

# Aceita a placa antiga (ABC1234) e a Mercosul (ABC1D23)
PADRAO_PLACA = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")


class VeiculoForm(forms.ModelForm):
    class Meta:
        model = Veiculo
        fields = [
            "imagem",
            "modelo",
            "placa",
            "categoria_classe",
            "ano",
            "quilometragem",
            "motorizacao",
            "disponivel",
        ]
        labels = {
            "modelo": "Nome do Veículo",
            "placa": "Placa",
            "categoria_classe": "Categoria",
            "ano": "Ano",
            "quilometragem": "Quilometragem (km)",
            "motorizacao": "Motorização",
            "disponivel": "Status do Veículo",
        }
        widgets = {
            "imagem": forms.FileInput(attrs={"accept": "image/png,image/jpeg"}),
            "placa": forms.TextInput(
                attrs={
                    "placeholder": "Ex: ABC1B23",
                    "maxlength": 10,
                    "autocomplete": "off",
                    "style": "text-transform: uppercase;",
                }
            ),
            "ano": forms.NumberInput(attrs={"placeholder": "Ex: 2023", "min": ANO_MINIMO}),
            "quilometragem": forms.NumberInput(attrs={"min": 0}),
            "disponivel": forms.Select(choices=[(True, "Disponível"), (False, "Indisponível")]),
        }
        # Mensagens curtas e claras, no lugar do "Este campo é obrigatório."
        error_messages = {
            "modelo": {"required": "Escolha o modelo do veículo."},
            "placa": {
                "required": "Informe a placa do veículo.",
                "unique": "Já existe um veículo com essa placa.",
            },
            "categoria_classe": {"required": "Escolha a categoria."},
            "ano": {"required": "Informe o ano.", "invalid": "Informe um ano válido."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["modelo"].queryset = ModeloCarro.objects.select_related("marca").order_by(
            "marca__nome", "nome"
        )
        self.fields["modelo"].empty_label = "Selecione o modelo"
        self.fields["categoria_classe"].queryset = CategoriaClasse.objects.select_related(
            "categoria", "classe"
        ).order_by("categoria__nome", "classe__nome")
        self.fields["categoria_classe"].empty_label = "Selecione a categoria"
        # Sem categoria/classe não existe diária, e um carro de locadora precisa de placa
        self.fields["categoria_classe"].required = True
        self.fields["placa"].required = True

    def clean_placa(self):
        # Aceita "abc-1234", "ABC 1D23" etc. e guarda sempre maiúscula e sem hífen
        placa = re.sub(r"[\s-]", "", self.cleaned_data.get("placa") or "").upper()
        if not PADRAO_PLACA.match(placa):
            raise ValidationError("Placa inválida. Use o formato ABC1D23 ou ABC-1234.")
        if Veiculo.objects.filter(placa__iexact=placa).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Já existe um veículo com essa placa.")
        return placa

    def clean_ano(self):
        ano = self.cleaned_data.get("ano")
        limite = date.today().year + 1  # permite o modelo do ano seguinte
        if ano is not None and not (ANO_MINIMO <= ano <= limite):
            raise ValidationError(f"Informe um ano entre {ANO_MINIMO} e {limite}.")
        return ano

    def clean_quilometragem(self):
        km = self.cleaned_data.get("quilometragem")
        if km is not None and km < 0:
            raise ValidationError("A quilometragem não pode ser negativa.")
        return km

    def clean_imagem(self):
        imagem = self.cleaned_data.get("imagem")
        if isinstance(imagem, UploadedFile):  # só valida quando uma foto nova foi enviada
            if imagem.size > TAMANHO_MAXIMO_FOTO:
                raise ValidationError("A foto deve ter no máximo 5MB.")
            formato = getattr(getattr(imagem, "image", None), "format", None)
            if formato not in FORMATOS_FOTO:
                raise ValidationError("Envie a foto em PNG ou JPG.")
        return imagem