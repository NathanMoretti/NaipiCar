@echo off
REM Instalação automática do NaipiCar (Windows)
cd /d "%~dp0"

echo Criando ambiente virtual...
python -m venv venv || goto erro
call venv\Scripts\activate.bat

echo Instalando dependencias...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt || goto erro

if not exist .env (
  echo Criando o arquivo .env a partir do .env.example...
  copy .env.example .env >nul
)

REM Se o .env estiver configurado para MySQL, instala o driver
findstr /i /b "DB_ENGINE=mysql" .env >nul && python -m pip install -r requirements-mysql.txt

echo Criando o banco de dados...
python manage.py migrate || goto erro

echo Importando marcas e modelos de carros...
python manage.py importar_carros || goto erro

echo.
echo Pronto! Agora rode:
echo   venv\Scripts\activate
echo   python manage.py createsuperuser
echo   python manage.py runserver
pause
exit /b 0

:erro
echo.
echo Ocorreu um erro na instalacao. Veja a mensagem acima.
pause
exit /b 1
