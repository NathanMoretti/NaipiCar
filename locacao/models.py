from django.conf import settings
from django.db import models


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
  nome = models.CharField(
      max_length=50, unique=True
  )  # Ex: SUV, Hatch, Sedan, Pickup
  descricao = models.TextField(blank=True, null=True)

  def __str__(self):
    return self.nome


class ClasseCarro(models.Model):
  nome = models.CharField(
      max_length=20, unique=True
  )  # Ex: Classe A, Classe B, Classe C

  def __str__(self):
    return self.nome


# Tabela Categoria x Classe (Seguindo rigorosamente o documento da sua imagem)
class CategoriaClasse(models.Model):
  categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
  classe = models.ForeignKey(ClasseCarro, on_delete=models.CASCADE)
  daily_rate = models.DecimalField(
      max_digits=10, decimal_places=2
  )  # Valor da diária para a combinação

  class Meta:
    unique_together = ("categoria", "classe")

  def __str__(self):
    return f"{self.categoria.nome} - {self.classe.nome} (R$ {self.daily_rate})"


class Veiculo(models.Model):
  class Motorizacao(models.TextChoices):
        COMBUSTAO = "combustao", "Combustão"
        HIBRIDO = "hibrido", "Híbrido"
        ELETRICO = "eletrico", "Elétrico"

  modelo = models.ForeignKey(ModeloCarro, on_delete=models.PROTECT)
  categoria_classe = models.ForeignKey(
      CategoriaClasse, on_delete=models.PROTECT, null=True, blank=True
  )
  ano = models.IntegerField()
  motorizacao = models.CharField(
      max_length=20,
      choices=Motorizacao.choices,
      default=Motorizacao.COMBUSTAO,
  )
  disponivel = models.BooleanField(default=True)

  placa = models.CharField(max_length=10, unique=True, null=True, blank=True)
  quilometragem = models.IntegerField(default=0)
  imagem = models.ImageField(upload_to="veiculos/", blank=True, null=True)

  @property
  def diaria(self):
    # Retorna o valor da diária cadastrado na tabela Categoria x Classe
    if self.categoria_classe:
      return self.categoria_classe.daily_rate
    return 0.00

  def __str__(self):
    cc_str = str(self.categoria_classe) if self.categoria_classe else "Sem Categoria/Classe"
    return f"{self.modelo} ({cc_str}) - Placa: {self.placa or 'N/D'}"


class Reserva(models.Model):
  STATUS_CHOICES = [
      ("Pendente", "Pendente de Pagamento do Sinal"),
      ("Confirmada", "Confirmada"),
      ("Concluída", "Concluída"),
      ("Cancelada", "Cancelada"),
  ]

  cliente = models.ForeignKey(
      settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True
  )
  nome_cliente = models.CharField(max_length=150, blank=True, null=True)
  email_cliente = models.EmailField(blank=True, null=True)

  veiculo = models.ForeignKey(Veiculo, on_delete=models.CASCADE)
  data_retirada = models.DateField()
  data_devolucao = models.DateField()
  valor_total = models.DecimalField(max_digits=10, decimal_places=2)
  status = models.CharField(
      max_length=20, choices=STATUS_CHOICES, default="Pendente"
  )
  data_criacao = models.DateTimeField(auto_now_add=True)

  def __str__(self):
    cliente_nome = self.cliente.full_name if self.cliente else self.nome_cliente
    return f"Reserva #{self.id} - {cliente_nome} ({self.veiculo})"