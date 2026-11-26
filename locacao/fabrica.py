"""Funções de apoio para os testes: criam usuários, veículos e reservas com poucos parâmetros."""
from datetime import date, timedelta
from decimal import Decimal

from contas.models import User

from .models import Categoria, CategoriaClasse, ClasseCarro, Marca, ModeloCarro, Reserva, Veiculo

SENHA = "Senha@123"  # atende à regra RN04 (8+ caracteres, maiúscula, número e símbolo)


def dia(n):
    """Data de hoje deslocada em n dias (dia(1) = amanhã, dia(-1) = ontem)."""
    return date.today() + timedelta(days=n)


def criar_cliente(email="cliente@teste.com", cpf="52998224725", **extra):
    extra.setdefault("first_name", "Maria")
    extra.setdefault("last_name", "Silva")
    extra.setdefault("phone", "(45) 99999-9999")
    return User.objects.create_user(email=email, password=SENHA, cpf=cpf, **extra)


def criar_admin(email="admin@teste.com", cpf="11144477735", **extra):
    extra.setdefault("first_name", "Admin")
    extra.setdefault("last_name", "Teste")
    return criar_cliente(email=email, cpf=cpf, profile_type=User.ADMIN, **extra)


def criar_veiculo(placa="ABC1D23", diaria="150.00", disponivel=True, marca="Jeep", modelo="Compass", ano=2023,
                  categoria="SUV", classe="Classe A"):
    marca_obj, _ = Marca.objects.get_or_create(nome=marca)
    modelo_obj, _ = ModeloCarro.objects.get_or_create(marca=marca_obj, nome=modelo)
    categoria_obj, _ = Categoria.objects.get_or_create(nome=categoria)
    classe_obj, _ = ClasseCarro.objects.get_or_create(nome=classe)
    combinacao, _ = CategoriaClasse.objects.get_or_create(
        categoria=categoria_obj, classe=classe_obj, defaults={"daily_rate": Decimal(diaria)}
    )
    return Veiculo.objects.create(
        modelo=modelo_obj, categoria_classe=combinacao, ano=ano, placa=placa, disponivel=disponivel
    )


def criar_reserva(veiculo, cliente, retirada, devolucao, status="Pendente"):
    dias = max((devolucao - retirada).days, 1)
    return Reserva.objects.create(
        veiculo=veiculo,
        cliente=cliente,
        nome_cliente=cliente.full_name,
        email_cliente=cliente.email,
        data_retirada=retirada,
        data_devolucao=devolucao,
        valor_total=dias * veiculo.diaria,
        status=status,
    )