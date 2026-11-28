# NaipiCar

**Plataforma web de consulta e reserva de veículos para pequenas e médias locadoras de Foz do Iguaçu.**

O cliente consulta o catálogo, escolhe o período e reserva online. O administrador gerencia a frota, as reservas, os usuários e os preços em um painel próprio. Projeto Integrador do curso de Tecnologia em Análise e Desenvolvimento de Sistemas do **IFPR – Campus Foz do Iguaçu**.

> **Status:** em desenvolvimento. A tabela de funcionalidades abaixo mostra o que já está pronto.

---

## Sobre o projeto

Muitas locadoras pequenas e médias ainda controlam reservas por balcão, telefone e aplicativos de mensagem. Isso gera demora no atendimento, informações repetidas e dificuldade para saber quais veículos estão livres em cada período.

O NaipiCar propõe um ambiente digital para:

- **Clientes:** cadastrar-se, consultar o catálogo com filtros, ver a disponibilidade por período, reservar, acompanhar e cancelar as próprias reservas, editar o perfil e recuperar a senha por e-mail.
- **Administradores:** acompanhar o dia a dia no dashboard, gerenciar veículos, reservas, usuários e os cadastros de marcas, modelos, categorias, classes e diárias.

## Funcionalidades

| Requisito | Funcionalidade | Situação |
|---|---|---|
| RF01 | Cadastro de cliente (nome, CPF, e-mail, telefone, endereço, senha forte e aceite dos termos) | Pronto |
| RF02 | Login com e-mail e senha; administrador vai para o painel e cliente para o catálogo | Pronto |
| RF03 | Catálogo de veículos com foto, modelo, ano, categoria, assentos, malas, motorização e diária | Pronto |
| RF04 | Busca por período livre, categoria, marca, motorização, assentos, malas, diária máxima e texto, com ordenação e paginação | Pronto |
| RF05 | Cadastro, edição e exclusão de veículos no painel, com validação de placa | Pronto |
| RF06 | Dashboard com período e categoria à escolha: receita, reservas, ticket médio, ocupação e cancelamentos (com comparação com o período anterior), gráficos, desempenho por categoria, rankings, radar do dia e agenda dos próximos 7 dias. O administrador escolhe quais blocos aparecer | Pronto |
| RF07 / RF08 | Gestão de reservas pelo administrador (busca, filtros e alteração de situação) | Pronto |
| RF09 | "Minhas reservas" do cliente, com histórico, valor e situação | Pronto |
| RF10 | Cancelamento da reserva pelo cliente (antes da retirada) | Pronto |
| RF11 | Edição de perfil (foto, dados, endereço e troca de senha com a senha atual) | Pronto |
| — | Recuperação de senha por e-mail | Pronto |
| — | Usuários no painel (busca, situação e perfil da conta) | Pronto |
| — | Cadastros no painel (marcas, modelos, categorias, classes e diárias) | Pronto |
| — | Reservas criadas pelo administrador (cliente no balcão, telefone ou WhatsApp), com as mesmas regras do site e prévia do valor | Pronto |
| — | Usuários cadastrados pelo administrador: a conta nasce sem senha e a pessoa recebe um link por e-mail para criar a própria | Pronto |

O valor total da reserva é calculado automaticamente (número de diárias × diária da categoria/classe do veículo).

Na página inicial, cada categoria aparece sozinha assim que tem pelo menos um veículo **disponível** cadastrado (com a foto do carro mais recente que tiver imagem).

## Tecnologias

- **Python 3.10+**
- **Django 5.2** (autenticação, ORM, painel de administração do Django)
- **Bootstrap 5** no site e CSS próprio no painel administrativo
- **SQLite** por padrão e **MySQL / MariaDB** como opção, com o driver **PyMySQL** (veja [Banco de dados](#banco-de-dados))
- **Pillow** (upload de imagens) e **python-dotenv** (configuração por arquivo `.env`)

---

## Como executar

### Pré-requisitos

- [Git](https://git-scm.com/)
- [Python 3.12 ou superior](https://www.python.org/downloads/). No Windows, marque **Add python.exe to PATH** na instalação.
  No Linux sem permissão de administrador, o `setup.sh` baixa o Python necessário sozinho.

Primeiro, em qualquer sistema, baixe o projeto:

```bash
git clone https://github.com/NathanMoretti/NaipiCar.git
cd NaipiCar
```

### Windows

**Opção 1: instalação automática.** Dê dois cliques em `setup.bat` ou rode no terminal:

```powershell
.\setup.bat
```

O script cria o ambiente virtual, instala as dependências, cria o `.env` (se ainda não existir), cria o banco e importa as marcas e modelos de carros.

**Opção 2: passo a passo (PowerShell).**

```powershell
# 1. Criar e ativar o ambiente virtual
python -m venv venv
venv\Scripts\Activate.ps1

# 2. Instalar as dependências
python -m pip install -r requirements.txt

# 3. Criar o arquivo de configuração
copy .env.example .env

# 4. Criar o banco de dados
python manage.py migrate

# 5. Importar marcas e modelos de carros
python manage.py importar_carros

# 6. Criar o usuário administrador
python manage.py createsuperuser

# 7. Iniciar o servidor
python manage.py runserver
```

> Se o passo 1 der erro de "execução de scripts desabilitada", rode uma vez:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
>
> No Prompt de Comando (cmd), ative com `venv\Scripts\activate.bat`.

### Linux / macOS

**Opção 1: instalação automática (não precisa de `sudo`).**

```bash
chmod +x setup.sh
./setup.sh
```

O script cria o ambiente virtual, instala as dependências, cria o `.env` (se ainda não existir), cria o banco e importa as marcas e modelos.

**Opção 2: passo a passo.**

```bash
# 1. Criar e ativar o ambiente virtual
python3 -m venv venv
source venv/bin/activate

# 2. Instalar as dependências
python -m pip install -r requirements.txt

# 3. Criar o arquivo de configuração
cp .env.example .env

# 4. Criar o banco de dados
python manage.py migrate

# 5. Importar marcas e modelos de carros
python manage.py importar_carros

# 6. Criar o usuário administrador
python manage.py createsuperuser

# 7. Iniciar o servidor
python manage.py runserver
```

### Depois da instalação automática

O script não cria o administrador, porque pede dados na tela. Rode, com o ambiente virtual ativo:

```bash
python manage.py createsuperuser
python manage.py runserver
```

(No Windows, ative com `venv\Scripts\Activate.ps1`; no Linux/macOS, com `source venv/bin/activate`.)

### Problemas comuns

**`ensurepip is not available` ao criar o ambiente virtual (Ubuntu/Debian):** falta o pacote `python3-venv`: `sudo apt install python3-venv`.

**Versão do Python menor que 3.10:** o Django 5.2 exige Python 3.10 ou superior. Sem `sudo`, dá para usar o [uv](https://docs.astral.sh/uv/) para baixar um Python novo:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.12 venv
source venv/bin/activate
uv pip install -r requirements.txt
```

### Endereços

| Página | Endereço |
|---|---|
| Início | http://127.0.0.1:8000/ |
| Veículos | http://127.0.0.1:8000/veiculos/ |
| Criar conta | http://127.0.0.1:8000/cadastro/ |
| Entrar | http://127.0.0.1:8000/login/ |
| Painel administrativo | http://127.0.0.1:8000/painel/ |
| Administração do Django | http://127.0.0.1:8000/admin/ |

### Primeiros passos no sistema

1. Entre com o administrador criado. Você cai no **Dashboard** do painel.
2. Em **Cadastros**, confira as marcas e modelos importados e cadastre as **categorias**, as **classes** e a **diária de cada combinação** (aba Diárias).
3. Em **Veículos**, cadastre os carros com foto, placa, ano e categoria.
4. Crie uma conta de cliente em `/cadastro/` e faça uma reserva pelo catálogo.
5. Volte ao painel, em **Reservas**, para confirmar a reserva.

---

## Banco de dados

Por padrão o projeto usa **SQLite**: não precisa instalar nem configurar nada. Para usar **MySQL** (8.0 ou superior) ou **MariaDB** (10.5 ou superior), siga os passos abaixo. A escolha é feita no arquivo `.env`, sem mexer no código.

1. **Tenha um servidor MySQL (ou MariaDB) rodando** e crie o banco e o usuário:

   ```sql
   CREATE DATABASE naipicar CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'naipicar'@'localhost' IDENTIFIED BY 'sua_senha_forte';
   GRANT ALL PRIVILEGES ON naipicar.* TO 'naipicar'@'localhost';
   GRANT ALL PRIVILEGES ON `test_naipicar`.* TO 'naipicar'@'localhost';
   ```

   A última linha permite que `python manage.py test` crie o banco temporário dos testes.

2. **Instale o driver** (com o ambiente virtual ativo):

   ```bash
   python -m pip install -r requirements-mysql.txt
   ```

   Isso instala o **PyMySQL**, um driver escrito só em Python que instala em qualquer sistema, sem compilador. Se preferir o `mysqlclient` (driver em C, um pouco mais rápido), descomente a linha dele no `requirements-mysql.txt`, instale de novo e coloque `DB_DRIVER=mysqlclient` no `.env`.

3. **Configure o `.env`** (copie do `.env.example`):

   ```
   DB_ENGINE=mysql
   DB_DRIVER=pymysql
   DB_NAME=naipicar
   DB_USER=naipicar
   DB_PASSWORD=sua_senha_forte
   DB_HOST=127.0.0.1
   DB_PORT=3306
   ```

4. **Crie as tabelas** e os dados iniciais:

   ```bash
   python manage.py migrate
   python manage.py importar_carros
   python manage.py createsuperuser
   ```

   Opcional: `python manage.py popular_dados` cria categorias, diárias, veículos, clientes e reservas de demonstração (senha dos clientes: `Senha@123`). Bom para apresentar o sistema.

5. **Confira** se está tudo certo rodando os testes no MySQL: `python manage.py test`.

Para voltar ao SQLite, use `DB_ENGINE=sqlite` no `.env`.

**Levando os dados do SQLite para o MySQL:** com `DB_ENGINE=sqlite`, exporte; depois troque para `mysql`, rode `migrate` e importe. As fotos ficam na pasta `media/` e não são afetadas.

```bash
python manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.permission --exclude admin.logentry --exclude sessions --indent 2 -o dados.json
# troque para DB_ENGINE=mysql no .env
python manage.py migrate
python manage.py loaddata dados.json
```

## E-mail

Em desenvolvimento, os e-mails (como o link de recuperação de senha) aparecem **no terminal** onde o servidor está rodando. Para enviar de verdade, configure um servidor SMTP e guarde a senha no `.env`.

## Testes

```bash
python manage.py test
```

Os testes cobrem as regras de reserva (período ocupado, datas, cancelamento, pedidos simultâneos), a proteção do histórico de reservas, os filtros do catálogo, as categorias da página inicial, os cálculos do dashboard, a validação de placa, as permissões do painel, os bloqueios de exclusão, a recuperação de senha, a edição de perfil e as reservas e usuários criados pelo administrador. Eles usam um banco temporário e não alteram os seus dados. O teste de pedidos simultâneos só roda com MySQL (no SQLite ele aparece como *skipped*).

## Estrutura do projeto

```
NaipiCar/
├── manage.py
├── requirements.txt           # dependências do projeto
├── requirements-mysql.txt     # driver do MySQL (PyMySQL)
├── .env.example               # modelo do arquivo de configuração (.env)
├── setup.sh                   # instalação automática (Linux / macOS)
├── setup.bat                  # instalação automática (Windows)
├── naipicar/                  # configurações do projeto (settings, urls)
├── contas/                    # usuários e endereços
│   ├── models.py              # User e Address
│   ├── forms.py               # cadastro (site e painel)
│   ├── forms_perfil.py        # edição de perfil
│   ├── forms_senha.py         # recuperação de senha e link para criar a senha
│   └── views.py, views_perfil.py, validators.py
├── locacao/                   # frota, reservas e painel
│   ├── models.py              # Marca, Modelo, Categoria, Classe, Veículo, Reserva
│   ├── regras.py              # regras da reserva (usadas pelo site e pelo painel)
│   ├── apoio.py               # paginação e "voltar" seguro, usados por várias telas
│   ├── views.py               # site do cliente
│   ├── forms.py               # formulários do painel
│   ├── painel/                # painel administrativo, um arquivo por tela
│   │   ├── comum.py           # acesso só para administradores, rótulos e formatação
│   │   ├── dashboard.py, veiculos.py, reservas.py, cadastros.py, usuarios.py
│   ├── templates/locacao/     # páginas do site (HTML)
│   ├── templates/locacao/painel/   # páginas do painel (HTML)
│   ├── static/locacao/css/    # estilos: site.css, painel.css (comuns) e um arquivo por tela
│   ├── static/locacao/js/     # scripts: painel.js (comum) e um arquivo por tela
│   ├── fabrica.py, test_*.py  # testes automatizados
│   └── management/commands/   # importar_carros e popular_dados
├── marcas-carros.csv          # dados para importação
├── modelos-carro.csv
└── media/veiculos/            # fotos dos veículos
```

Os templates só têm HTML: o CSS e o JavaScript ficam em `locacao/static/`. O que é usado por várias telas fica num arquivo comum (`painel.css` e `painel.js`), e o resto fica no arquivo da tela.

## Modelagem do banco de dados

O banco segue o dicionário de dados do projeto:

- **Usuário** e **Endereço**: clientes e administradores. O usuário tem perfil (cliente ou administrador) e situação (ativo, inativo, pendente ou bloqueado).
- **Marca**, **Modelo**, **Categoria**, **Classe** e **Categoria × Classe**: classificação dos veículos. A diária é definida pela combinação de categoria e classe.
- **Veículo**: unidade física disponível para locação.
- **Reserva**: liga o usuário ao veículo, com período, valor total e situação (pendente, confirmada, concluída ou cancelada). "Atrasada" é calculada: reserva confirmada cuja devolução já passou.

No código, as situações da reserva são usadas por `Reserva.Status` (`Status.PENDENTE`, `Status.CONFIRMADA`...) e não escritas como texto, o que evita erros de digitação.

Algumas regras são garantidas pelo **próprio banco** (`CheckConstraint`), e não só pelas telas: a devolução precisa ser depois da retirada, e valor, diária e quilometragem não podem ser negativos. Assim, nem uma gravação feita por fora das telas (pelo `/admin/` do Django, por exemplo) consegue deixar dados inválidos.

Alguns nomes do banco estão em inglês (as tabelas `user` e `address` e campos como `first_name` e `daily_rate`) porque seguem o dicionário de dados do projeto; o restante do código está em português.

## Segurança

- Senhas guardadas apenas como hash, nunca em texto. Regra de senha: mínimo de 8 caracteres, com letra maiúscula, número e símbolo.
- Troca de senha no perfil exige a senha atual. O CPF não pode ser alterado depois do cadastro.
- Contas criadas pelo administrador nascem sem senha: a pessoa cria a própria senha pelo link enviado por e-mail, e o administrador nunca fica sabendo qual é.
- Recuperação de senha por link de uso único, com validade de 1 hora, e resposta igual para e-mails que existem ou não.
- O painel só abre para administradores ativos. Contas inativas ou bloqueadas não conseguem entrar.
- Duas pessoas não conseguem reservar o mesmo carro no mesmo período, mesmo clicando ao mesmo tempo: a verificação e a gravação da reserva acontecem numa transação que trava o veículo (`select_for_update`).
- O histórico de reservas não pode ser apagado: veículos e clientes com reservas não podem ser excluídos (`on_delete=PROTECT`), nem pelo `/admin/` do Django.
- O banco de dados (`db.sqlite3`) não vai para o GitHub, para não expor dados pessoais.
- Proteção CSRF nos formulários e uso do ORM do Django (consultas parametrizadas).
- Segredos (chave do Django, senha do banco) ficam no arquivo `.env`, que não vai para o GitHub.
- Tratamento de dados pessoais conforme os princípios da LGPD: CPF parcialmente oculto nas listas do painel.

## Publicando o sistema

O projeto já está preparado para ir para a internet (por exemplo, no PythonAnywhere, que tem plano gratuito com MySQL). No servidor:

1. Configure o `.env` de produção:

   ```
   DEBUG=False
   SECRET_KEY=uma-chave-longa-e-secreta
   ALLOWED_HOSTS=naipicar.pythonanywhere.com
   CSRF_TRUSTED_ORIGINS=https://naipicar.pythonanywhere.com
   USAR_HTTPS=True
   DB_ENGINE=mysql
   ```

   Com `DEBUG=False` o sistema **não inicia** sem uma `SECRET_KEY` própria. Para gerar uma: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`.

2. Junte os arquivos estáticos numa pasta só: `python manage.py collectstatic` (cria a pasta `staticfiles/`).
3. No painel do servidor, aponte o endereço `/static/` para a pasta `staticfiles/` e `/media/` para a pasta `media/`. Com `DEBUG=False`, o Django não entrega esses arquivos sozinho.
4. Confira com `python manage.py check --deploy`: não deve aparecer nenhum aviso.

## Próximos passos

- Horário de retirada e devolução.
- Verificação de e-mail no cadastro.
- Envio real de e-mails (SMTP).
- Integração com meios de pagamento e notificações automáticas.

## Equipe

Projeto desenvolvido por **Bruno**, **Nathan** e **Milan**, estudantes de Tecnologia em Análise e Desenvolvimento de Sistemas do Instituto Federal do Paraná (IFPR), Campus Foz do Iguaçu.

## Licença

Projeto acadêmico. Todos os direitos reservados aos autores.