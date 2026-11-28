import re

from django import forms
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone

from contas.models import User

from .models import Categoria, CategoriaClasse, ClasseCarro, Marca, ModeloCarro, Reserva, Veiculo

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
        limite = timezone.localdate().year + 1  # permite o modelo do ano seguinte
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


# ---------------------------------------------------------------------------
# Cadastros auxiliares do painel
# ---------------------------------------------------------------------------
class _NomeUnicoMixin:
    """Evita nomes repetidos sem diferenciar maiúsculas de minúsculas."""

    mensagem_duplicado = "Já existe um registro com esse nome."

    def clean_nome(self):
        nome = " ".join((self.cleaned_data.get("nome") or "").split())
        if not nome:
            raise ValidationError("Informe o nome.")
        existe = self._meta.model.objects.filter(nome__iexact=nome).exclude(pk=self.instance.pk)
        if existe.exists():
            raise ValidationError(self.mensagem_duplicado)
        return nome


class MarcaForm(_NomeUnicoMixin, forms.ModelForm):
    mensagem_duplicado = "Já existe uma marca com esse nome."

    class Meta:
        model = Marca
        fields = ["nome"]
        labels = {"nome": "Nome da marca"}
        widgets = {"nome": forms.TextInput(attrs={"placeholder": "Ex: Toyota"})}


class CategoriaForm(_NomeUnicoMixin, forms.ModelForm):
    mensagem_duplicado = "Já existe uma categoria com esse nome."

    class Meta:
        model = Categoria
        fields = ["nome", "descricao"]
        labels = {"nome": "Nome da categoria", "descricao": "Descrição (opcional)"}
        widgets = {
            "nome": forms.TextInput(attrs={"placeholder": "Ex: SUV"}),
            "descricao": forms.Textarea(attrs={"rows": 3, "placeholder": "Ex: Mais espaço e conforto para sua aventura."}),
        }


class ClasseCarroForm(_NomeUnicoMixin, forms.ModelForm):
    mensagem_duplicado = "Já existe uma classe com esse nome."

    class Meta:
        model = ClasseCarro
        fields = ["nome"]
        labels = {"nome": "Nome da classe"}
        widgets = {"nome": forms.TextInput(attrs={"placeholder": "Ex: Classe A"})}


class ModeloCarroForm(forms.ModelForm):
    class Meta:
        model = ModeloCarro
        fields = ["marca", "nome", "assentos", "malas"]
        labels = {"marca": "Marca", "nome": "Nome do modelo", "assentos": "Assentos", "malas": "Malas"}
        widgets = {
            "nome": forms.TextInput(attrs={"placeholder": "Ex: Compass"}),
            "assentos": forms.NumberInput(attrs={"min": 1, "max": 15}),
            "malas": forms.NumberInput(attrs={"min": 0, "max": 10}),
        }
        error_messages = {"marca": {"required": "Escolha a marca."}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["marca"].queryset = Marca.objects.order_by("nome")
        self.fields["marca"].empty_label = "Selecione a marca"

    def clean_nome(self):
        return " ".join((self.cleaned_data.get("nome") or "").split())

    def clean_assentos(self):
        n = self.cleaned_data.get("assentos")
        if n is not None and not 1 <= n <= 15:
            raise ValidationError("Informe entre 1 e 15 assentos.")
        return n

    def clean_malas(self):
        n = self.cleaned_data.get("malas")
        if n is not None and not 0 <= n <= 10:
            raise ValidationError("Informe entre 0 e 10 malas.")
        return n

    def clean(self):
        dados = super().clean()
        marca, nome = dados.get("marca"), dados.get("nome")
        if marca and nome:
            repetido = ModeloCarro.objects.filter(marca=marca, nome__iexact=nome).exclude(pk=self.instance.pk)
            if repetido.exists():
                self.add_error("nome", "Essa marca já tem um modelo com esse nome.")
        return dados


class CategoriaClasseForm(forms.ModelForm):
    class Meta:
        model = CategoriaClasse
        fields = ["categoria", "classe", "daily_rate"]
        labels = {"categoria": "Categoria", "classe": "Classe", "daily_rate": "Valor da diária (R$)"}
        widgets = {"daily_rate": forms.NumberInput(attrs={"min": 0, "step": "0.01", "placeholder": "Ex: 150,00"})}
        error_messages = {
            "categoria": {"required": "Escolha a categoria."},
            "classe": {"required": "Escolha a classe."},
            NON_FIELD_ERRORS: {"unique_together": "Essa combinação de categoria e classe já existe. Edite o valor dela."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].queryset = Categoria.objects.order_by("nome")
        self.fields["categoria"].empty_label = "Selecione a categoria"
        self.fields["classe"].queryset = ClasseCarro.objects.order_by("nome")
        self.fields["classe"].empty_label = "Selecione a classe"

    def clean_daily_rate(self):
        valor = self.cleaned_data.get("daily_rate")
        if valor is not None and valor <= 0:
            raise ValidationError("A diária deve ser maior que zero.")
        return valor

class ReservaPainelForm(forms.Form):
    """Reserva criada pelo administrador (cliente no balcão, telefone ou WhatsApp).

    As regras do período (datas, veículo livre) ficam em regras.criar_reserva, as mesmas do site.
    """

    SITUACOES = [
        (Reserva.Status.CONFIRMADA, "Reservado (confirmada)"),
        (Reserva.Status.PENDENTE, "Em análise (aguardando sinal)"),
    ]

    cliente = forms.ModelChoiceField(
        label="Cliente", queryset=None, empty_label="Selecione o cliente",
        error_messages={"required": "Escolha o cliente.", "invalid_choice": "Escolha um cliente ativo da lista."})
    veiculo = forms.ModelChoiceField(
        label="Veículo", queryset=None, empty_label="Selecione o veículo",
        error_messages={"required": "Escolha o veículo.", "invalid_choice": "Escolha um veículo disponível da lista."})
    data_retirada = forms.DateField(
        label="Retirada", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        error_messages={"required": "Informe a data de retirada.", "invalid": "Informe uma data válida."})
    data_devolucao = forms.DateField(
        label="Devolução", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        error_messages={"required": "Informe a data de devolução.", "invalid": "Informe uma data válida."})
    status = forms.ChoiceField(label="Situação", choices=SITUACOES, initial=Reserva.Status.CONFIRMADA)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cliente"].queryset = User.objects.filter(
            profile_type=User.USER, status=User.ACTIVE).order_by("first_name", "last_name")
        self.fields["cliente"].label_from_instance = lambda u: f"{u.full_name} · CPF {u.cpf} · {u.email}"
        self.fields["veiculo"].queryset = (
            Veiculo.objects.filter(disponivel=True, categoria_classe__isnull=False)
            .select_related("modelo__marca", "categoria_classe").order_by("modelo__marca__nome", "modelo__nome"))
        self.fields["veiculo"].label_from_instance = self._rotulo_veiculo
        self.fields["data_retirada"].widget.attrs["min"] = timezone.localdate().isoformat()
        self.fields["data_devolucao"].widget.attrs["min"] = timezone.localdate().isoformat()

    @staticmethod
    def _rotulo_veiculo(v):
        diaria = f"{v.diaria:.2f}".replace(".", ",")
        return f"{v.modelo} · {v.placa or 'sem placa'} · R$ {diaria}/dia"
