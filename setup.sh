#!/bin/bash
echo "Criando ambiente virtual..."
python3 -m venv venv

echo "Ativando ambiente virtual..."
source venv/bin/activate

echo "Atualizando pip..."
pip install --upgrade pip

echo "Instalando dependencias..."
pip install -r requirements.txt

echo "Pronto! Para rodar o projeto: python main.py"