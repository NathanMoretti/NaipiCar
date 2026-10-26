@echo off
echo Criando ambiente virtual...
python -m venv venv

echo Ativando ambiente virtual...
call venv\Scripts\activate

echo Atualizando pip...
python -m pip install --upgrade pip

echo Instalando dependencias...
pip install -r requirements.txt

echo.
echo Pronto! Para rodar o projeto: python main.py
pause