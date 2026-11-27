#!/bin/bash
# Instalação automática do NaipiCar (Linux / macOS)
set -e
cd "$(dirname "$0")"

echo "Criando ambiente virtual..."
python3 -m venv venv
source venv/bin/activate

echo "Instalando dependencias..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [ ! -f .env ]; then
  echo "Criando o arquivo .env a partir do .env.example..."
  cp .env.example .env
fi

# Se o .env estiver configurado para MySQL, instala o driver
if grep -qi "^DB_ENGINE=mysql" .env; then
  echo "Instalando o driver do MySQL..."
  python -m pip install -r requirements-mysql.txt
fi

echo "Criando o banco de dados..."
python manage.py migrate

echo "Importando marcas e modelos de carros..."
python manage.py importar_carros

echo
echo "Pronto! Agora rode:"
echo "  source venv/bin/activate"
echo "  python manage.py createsuperuser"
echo "  python manage.py runserver"
