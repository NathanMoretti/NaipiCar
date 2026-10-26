import csv
from django.core.management.base import BaseCommand
from locacao.models import Marca, ModeloCarro

class Command(BaseCommand):
    help = 'Importa marcas e modelos de carros a partir de arquivos CSV'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando importação de marcas...")

        marca_map = {}

        # 1. Importar Marcas
        with open('marcas-carros.csv', mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            # Limpa espaços e caracteres invisíveis dos nomes das colunas
            reader.fieldnames = [col.strip() for col in reader.fieldnames]
            
            for row in reader:
                id_original = row['ID']
                nome_marca = row['NOME'].strip().title()
                
                marca_obj, created = Marca.objects.get_or_create(nome=nome_marca)
                marca_map[id_original] = marca_obj

        self.stdout.write(self.style.SUCCESS("Marcas importadas com sucesso!"))

        self.stdout.write("Iniciando importação de modelos...")

        # 2. Importar Modelos
        with open('modelos-carro.csv', mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            reader.fieldnames = [col.strip() for col in reader.fieldnames]
            
            for row in reader:
                id_marca_original = row['IDMARCA']
                nome_modelo = row['NOME'].strip().title()

                if id_marca_original in marca_map:
                    marca_obj = marca_map[id_marca_original]
                    ModeloCarro.objects.get_or_create(marca=marca_obj, nome=nome_modelo)

        self.stdout.write(self.style.SUCCESS("Modelos importados com sucesso! O NaipiCar está abastecido!"))