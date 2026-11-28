from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Marca(models.Model):
    nome = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nome


class ModeloCarro(models.Model):
    marca = models.ForeignKey(Marca, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    assentos = models.PositiveSmallIntegerField(default=5)
    malas = models.PositiveSmallIntegerField(
        default=2,
        help_text="Quantidade de malas médias que cabem no porta-malas",
    )

    def __str__(self):
        return f"{self.marca.nome} {self.nome}"


class Categoria(models.Model):
    nome = models.CharField(max_length=50, unique=True)  # Ex: SUV, Hatch, Sedan, Pickup
    descricao = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nome


class ClasseCarro(models.Model):
    nome = models.CharField(max_length=20, unique=True)  # Ex: Classe A, Classe B, Classe C

    def __str__(self):
        return self.nome


class CategoriaClasse(models.Model):
    """Tabela Categoria x Classe do dicionário de dados: a diária depende da combinação."""

    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    classe = models.ForeignKey(ClasseCarro, on_delete=models.CASCADE)
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2)  # valor da diária para a combinação

    class Meta:
        unique_together = ("categoria", "classe")
        constraints = [
            models.CheckConstraint(condition=Q(daily_rate__gte=0), name="diaria_nao_negativa"),
        ]

    def __str__(self):
        return f"{self.categoria.nome} - {self.classe.nome} (R$ {self.daily_rate})"


class Veiculo(models.Model):
    class Motorizacao(models.TextChoices):
        COMBUSTAO = "combustao", "Combustão"
        HIBRIDO = "hibrido", "Híbrido"
        ELETRICO = "eletrico", "Elétrico"

    modelo = models.ForeignKey(ModeloCarro, on_delete=models.PROTECT)
    categoria_classe = models.ForeignKey(CategoriaClasse, on_delete=models.PROTECT, null=True, blank=True)
    ano = models.IntegerField()
    motorizacao = models.CharField(max_length=20, choices=Motorizacao.choices, default=Motorizacao.COMBUSTAO)
    disponivel = models.BooleanField(default=True)

    placa = models.CharField(max_length=10, unique=True, null=True, blank=True)
    quilometragem = models.IntegerField(default=0)
    imagem = models.ImageField(upload_to="veiculos/", blank=True, null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(quilometragem__gte=0), name="quilometragem_nao_negativa"),
        ]

    @property
    def diaria(self):
        """Valor da diária cadastrado na tabela Categoria x Classe (0 se o veículo não tem combinação)."""
        if self.categoria_classe:
            return self.categoria_classe.daily_rate
        return 0.00

    def __str__(self):
        cc_str = str(self.categoria_classe) if self.categoria_classe else "Sem Categoria/Classe"
        return f"{self.modelo} ({cc_str}) - Placa: {self.placa or 'N/D'}"


class Reserva(models.Model):
    class Status(models.TextChoices):
        """Situações gravadas no banco. Use Reserva.Status.PENDENTE etc. em vez de escrever o texto."""

        PENDENTE = "Pendente", "Pendente de Pagamento do Sinal"
        CONFIRMADA = "Confirmada", "Confirmada"
        CONCLUIDA = "Concluída", "Concluída"
        CANCELADA = "Cancelada", "Cancelada"

    # Situações em que a reserva ainda "segura" o veículo (aparecem como atuais para o cliente)
    EM_ABERTO = (Status.PENDENTE, Status.CONFIRMADA)
    # Situações finais (histórico)
    FINALIZADAS = (Status.CONCLUIDA, Status.CANCELADA)

    # PROTECT: não deixa apagar um cliente ou um veículo que tenha reservas,
    # para não perder o histórico (nem pelo /admin/ do Django). Use a situação
    # "Inativo" no cliente ou "indisponível" no veículo.
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    # Nome e e-mail copiados no momento da reserva: o histórico continua certo mesmo
    # se o cliente mudar os dados da conta depois.
    nome_cliente = models.CharField(max_length=150, blank=True, null=True)
    email_cliente = models.EmailField(blank=True, null=True)

    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT)
    data_retirada = models.DateField()
    data_devolucao = models.DateField()
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # Regras garantidas pelo próprio banco, mesmo que alguém grave sem passar pelas telas
            models.CheckConstraint(
                condition=Q(data_devolucao__gt=F("data_retirada")), name="devolucao_depois_da_retirada"),
            models.CheckConstraint(condition=Q(valor_total__gte=0), name="valor_total_nao_negativo"),
        ]

    def __str__(self):
        cliente_nome = self.cliente.full_name if self.cliente else self.nome_cliente
        return f"Reserva #{self.id} - {cliente_nome} ({self.veiculo})"
