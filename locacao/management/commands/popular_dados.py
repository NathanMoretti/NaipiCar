"""Carga de dados de demonstração do NaipiCar (NÃO cria o administrador).

Uso:  python manage.py popular_dados
Pode ser executado várias vezes sem duplicar nada.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from contas.models import Address
from locacao.models import (Categoria, CategoriaClasse, ClasseCarro, Marca,
                            ModeloCarro, Reserva, Veiculo)

SENHA_PADRAO = 'Senha@123'  # cumpre a RN04: 8+ caracteres, maiúscula, número e símbolo

CATEGORIAS = {
    'Econômico': 'Ideal para o dia a dia e viagens curtas.',
    'Hatch': 'Compacto, ágil e econômico na cidade.',
    'Sedan': 'Conforto e porta-malas amplo.',
    'SUV': 'Mais espaço e altura para a aventura.',
    'Pickup': 'Capacidade de carga e robustez.',
}
CLASSES = ['A', 'B', 'C']
# (categoria, classe, diária em R$)
DIARIAS = [
    ('Econômico', 'A', '89.00'),
    ('Hatch', 'A', '109.00'), ('Hatch', 'B', '129.00'),
    ('Sedan', 'B', '159.00'), ('Sedan', 'C', '189.00'),
    ('SUV', 'B', '219.00'), ('SUV', 'C', '279.00'),
    ('Pickup', 'B', '249.00'), ('Pickup', 'C', '329.00'),
]
# (placa, marca, modelo, ano, km, categoria, classe, disponível)
VEICULOS = [
    ('FOZ1A23', 'Fiat', 'Mobi', 2024, 12400, 'Econômico', 'A', True),
    ('IGU2B34', 'Renault', 'Kwid', 2023, 31800, 'Econômico', 'A', True),
    ('CAT3C45', 'Chevrolet', 'Onix', 2024, 9800, 'Hatch', 'A', True),
    ('PRA4D56', 'Hyundai', 'HB20', 2024, 15200, 'Hatch', 'B', True),
    ('BRA5E67', 'Volkswagen', 'Polo', 2025, 4300, 'Hatch', 'B', True),
    ('ARG6F78', 'Chevrolet', 'Onix Plus', 2024, 22100, 'Sedan', 'B', True),
    ('PYC7G89', 'Toyota', 'Corolla', 2025, 6700, 'Sedan', 'C', True),
    ('NAI8H90', 'Fiat', 'Pulse', 2024, 18900, 'SUV', 'B', True),
    ('PIC9J01', 'Volkswagen', 'T-Cross', 2025, 8100, 'SUV', 'B', True),
    ('CAR1K12', 'Jeep', 'Compass', 2025, 5200, 'SUV', 'C', True),
    ('RES2L23', 'Fiat', 'Strada', 2024, 27400, 'Pickup', 'B', True),
    ('LOC3M34', 'Toyota', 'Hilux', 2024, 35600, 'Pickup', 'C', False),  # em manutenção
]

# (nome completo, e-mail, base do CPF, telefone, rua, número, bairro, CEP)
CLIENTES = [
    ('Lucas Almeida', 'lucas.almeida@email.com', '123456789', '(45) 99911-1001',
     'Avenida Brasil', '1200', 'Centro', '85851-000'),
    ('Mariana Sousa', 'mariana.sousa@email.com', '987654321', '(45) 99922-2002',
     'Rua Jorge Schimmelpfeng', '350', 'Centro', '85851-010'),
    ('Carla Mendes', 'carla.mendes@email.com', '111222333', '(45) 99933-3003',
     'Rua Almirante Barroso', '88', 'Vila Portes', '85860-000'),
    ('Rafael Costa', 'rafael.costa@email.com', '452387916', '(45) 99944-4004',
     'Avenida das Cataratas', '4790', 'Vila Yolanda', '85853-000'),
    ('Ana Ribeiro', 'ana.ribeiro@email.com', '702846193', '(45) 99955-5005',
     'Rua Rio Branco', '455', 'Jardim América', '85851-120'),
    ('João Pedro Silva', 'joao.silva@email.com', '318570264', '(45) 99966-6006',
     'Rua Edmundo de Barros', '720', 'Jardim Jupira', '85857-300'),
]

# (e-mail, placa, início em dias a partir de hoje, fim, situação)
RESERVAS = [
    ('lucas.almeida@email.com', 'PYC7G89', -60, -57, 'Concluída'),
    ('lucas.almeida@email.com', 'PYC7G89', -1, 2, 'Confirmada'),
    ('mariana.sousa@email.com', 'CAT3C45', -30, -28, 'Concluída'),
    ('mariana.sousa@email.com', 'CAR1K12', 5, 8, 'Pendente'),
    ('carla.mendes@email.com', 'CAT3C45', -20, -17, 'Concluída'),
    ('rafael.costa@email.com', 'BRA5E67', -45, -42, 'Concluída'),
    ('rafael.costa@email.com', 'BRA5E67', 3, 6, 'Cancelada'),
    ('ana.ribeiro@email.com', 'PRA4D56', -12, -10, 'Concluída'),
    ('ana.ribeiro@email.com', 'PIC9J01', 10, 15, 'Confirmada'),
    ('joao.silva@email.com', 'RES2L23', 2, 4, 'Pendente'),
]


def gerar_cpf(base9):
    """Completa um CPF válido a partir dos 9 primeiros dígitos."""
    d = [int(c) for c in base9]
    for n in (9, 10):
        soma = sum(d[i] * (n + 1 - i) for i in range(n))
        d.append((soma * 10 % 11) % 10)
    s = ''.join(map(str, d))
    return f'{s[:3]}.{s[3:6]}.{s[6:9]}-{s[9:]}'


class Command(BaseCommand):
    help = 'Cria categorias, classes, diárias, veículos, clientes e reservas de demonstração.'

    @transaction.atomic
    def handle(self, *args, **opcoes):
        User = get_user_model()

        # --- categorias, classes e diárias --------------------------------
        categorias = {n: Categoria.objects.get_or_create(nome=n, defaults={'descricao': d})[0]
                      for n, d in CATEGORIAS.items()}
        classes = {n: ClasseCarro.objects.get_or_create(nome=n)[0] for n in CLASSES}
        combos = {}
        for cat, cla, diaria in DIARIAS:
            combos[(cat, cla)] = CategoriaClasse.objects.get_or_create(
                categoria=categorias[cat], classe=classes[cla],
                defaults={'daily_rate': diaria})[0]

        # --- veículos (com as marcas/modelos necessários) -------------------
        veiculos = {}
        for placa, marca, modelo, ano, km, cat, cla, disponivel in VEICULOS:
            marca_obj = Marca.objects.get_or_create(nome=marca)[0]
            modelo_obj = ModeloCarro.objects.get_or_create(marca=marca_obj, nome=modelo)[0]
            veiculos[placa] = Veiculo.objects.get_or_create(
                placa=placa, defaults={
                    'modelo': modelo_obj, 'categoria_classe': combos[(cat, cla)],
                    'ano': ano, 'quilometragem': km, 'disponivel': disponivel})[0]

        # --- clientes (nenhum administrador é criado) -----------------------
        clientes, novos_clientes = {}, 0
        for nome, email, base_cpf, telefone, rua, numero, bairro, cep in CLIENTES:
            usuario = User.objects.filter(email=email).first()
            if not usuario:
                primeiro, _, sobrenome = nome.partition(' ')
                endereco = Address.objects.create(
                    street=rua, number=numero, neighborhood=bairro,
                    city='Foz do Iguaçu', state='PR', zip_code=cep)
                usuario = User.objects.create_user(
                    email, SENHA_PADRAO, first_name=primeiro, last_name=sobrenome,
                    cpf=gerar_cpf(base_cpf), phone=telefone, address=endereco,
                    profile_type=User.USER)
                novos_clientes += 1
            clientes[email] = usuario

        # --- reservas (só para clientes que ainda não têm nenhuma) ----------
        hoje = timezone.localdate()
        novas_reservas = 0
        for email, placa, ini, fim, situacao in RESERVAS:
            usuario, veiculo = clientes[email], veiculos[placa]
            if getattr(usuario, '_reservas_criadas', None) is None:
                usuario._reservas_criadas = Reserva.objects.filter(cliente=usuario).exists()
            if usuario._reservas_criadas:
                continue
            retirada, devolucao = hoje + timedelta(days=ini), hoje + timedelta(days=fim)
            reserva = Reserva.objects.create(
                cliente=usuario, nome_cliente=usuario.full_name, email_cliente=usuario.email,
                veiculo=veiculo, data_retirada=retirada, data_devolucao=devolucao,
                valor_total=Decimal(str(veiculo.diaria)) * (devolucao - retirada).days,
                status=situacao)
            # a data de criação fica alguns dias antes da retirada, para o histórico fazer sentido
            Reserva.objects.filter(pk=reserva.pk).update(
                data_criacao=timezone.now() + timedelta(days=ini - 3))
            novas_reservas += 1

        self.stdout.write(self.style.SUCCESS(
            f'Pronto! {novos_clientes} cliente(s) e {novas_reservas} reserva(s) criados. '
            f'No banco: {Veiculo.objects.count()} veículos, {User.objects.count()} usuários, '
            f'{Reserva.objects.count()} reservas.'))
        self.stdout.write(f'Senha de todos os clientes de demonstração: {SENHA_PADRAO}')
        for _, email, *_ in CLIENTES:
            self.stdout.write(f'  {email}')
        self.stdout.write('O administrador NÃO é criado aqui: use "python manage.py createsuperuser".')
