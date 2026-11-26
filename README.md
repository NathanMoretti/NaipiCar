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
| — | Reservas e usuários criados pelo administrador | Planejado |

O valor total da reserva é calculado automaticamente (número de diárias × diária da categoria/classe do veículo).

Na página inicial, cada categoria aparece sozinha assim que tem pelo menos um veículo **disponível** cadastrado (com a foto do carro mais recente que tiver imagem).

## Tecnologias

- **Python 3.12+**
- **Django 6.1** (autenticação, ORM, painel de administração do Django)
- **Bootstrap 5** no site e CSS próprio no painel administrativo
- **SQLite** por padrão e **MySQL** como opção (veja [Banco de dados](#banco-de-dados))
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

O script cria o ambiente virtual, instala as dependências, cria o banco e importa as marcas e modelos de carros.

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

O script instala o [uv](https://docs.astral.sh/uv/) se preciso, cria o ambiente virtual com o Python 3.12, instala as dependências, cria o banco e importa as marcas e modelos.

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

**`ensurepip is not available` ao criar o ambiente virtual (Ubuntu/Debian):** falta o pacote `python3-venv`. Sem `sudo`, use o `setup.sh`. Com `sudo`: `sudo apt install python3-venv`.

**Versão do Python menor que 3.12:** o Django 6 exige Python 3.12 ou superior. O `setup.sh` resolve baixando o Python correto via `uv`. Manualmente:

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

Por padrão o projeto usa **SQLite**: não precisa instalar nem configurar nada. Para usar **MySQL**, siga os passos abaixo.

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

   Se o `mysqlclient` não instalar na sua máquina, edite o `requirements-mysql.txt` para usar o `PyMySQL` e coloque `DB_DRIVER=pymysql` no `.env`.

3. **Configure o `.env`** (copie do `.env.example`):

   ```
   DB_ENGINE=mysql
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

Os testes cobrem as regras de reserva (período ocupado, datas, cancelamento), os filtros do catálogo, as categorias da página inicial, os cálculos do dashboard, a validação de placa, as permissões do painel, os bloqueios de exclusão, a recuperação de senha e a edição de perfil. Eles usam um banco temporário e não alteram os seus dados.

## Estrutura do projeto

```
NaipiCar/
├── manage.py
├── requirements.txt           # dependências do projeto
├── requirements-mysql.txt     # driver opcional do MySQL
├── .env.example               # modelo do arquivo de configuração (.env)
├── setup.sh                   # instalação automática (Linux / macOS)
├── setup.bat                  # instalação automática (Windows)
├── naipicar/                  # configurações do projeto (settings, urls)
├── contas/                    # usuários e endereços
│   ├── models.py              # User e Address
│   ├── forms.py               # cadastro
│   ├── forms_perfil.py        # edição de perfil
│   ├── forms_senha.py         # recuperação de senha
│   └── views.py, views_perfil.py, validators.py
├── locacao/                   # frota, reservas e painel
│   ├── models.py              # Marca, Modelo, Categoria, Classe, Veículo, Reserva
│   ├── views.py               # site do cliente
│   ├── painel_views.py        # painel administrativo
│   ├── forms.py               # formulários do painel
│   ├── fabrica.py, test_*.py  # testes automatizados
│   ├── templates/locacao/     # site, login, cadastro e recuperação de senha
│   ├── templates/locacao/painel/   # telas do painel
│   └── management/commands/importar_carros.py
├── marcas-carros.csv          # dados para importação
├── modelos-carro.csv
└── media/                     # fotos enviadas (não vai para o GitHub)
```

## Modelagem do banco de dados

O banco segue o dicionário de dados do projeto:

- **Usuário** e **Endereço**: clientes e administradores. O usuário tem perfil (cliente ou administrador) e situação (ativo, inativo, pendente ou bloqueado).
- **Marca**, **Modelo**, **Categoria**, **Classe** e **Categoria × Classe**: classificação dos veículos. A diária é definida pela combinação de categoria e classe.
- **Veículo**: unidade física disponível para locação.
- **Reserva**: liga o usuário ao veículo, com período, valor total e situação (pendente, confirmada, concluída ou cancelada). "Atrasada" é calculada: reserva confirmada cuja devolução já passou.

## Segurança

- Senhas guardadas apenas como hash, nunca em texto. Regra de senha: mínimo de 8 caracteres, com letra maiúscula, número e símbolo.
- Troca de senha no perfil exige a senha atual. O CPF não pode ser alterado depois do cadastro.
- Recuperação de senha por link de uso único, com validade de 1 hora, e resposta igual para e-mails que existem ou não.
- O painel só abre para administradores ativos. Contas inativas ou bloqueadas não conseguem entrar.
- Proteção CSRF nos formulários e uso do ORM do Django (consultas parametrizadas).
- Segredos (chave do Django, senha do banco) ficam no arquivo `.env`, que não vai para o GitHub.
- Tratamento de dados pessoais conforme os princípios da LGPD: CPF parcialmente oculto nas listas do painel.

## Próximos passos

- Reservas e cadastro de usuários criados pelo administrador no painel.
- Horário de retirada e devolução.
- Verificação de e-mail no cadastro.
- Envio real de e-mails (SMTP).
- Integração com meios de pagamento e notificações automáticas.

## Equipe

Projeto desenvolvido por **Bruno**, **Nathan** e **Milan**, estudantes de Tecnologia em Análise e Desenvolvimento de Sistemas do Instituto Federal do Paraná (IFPR), Campus Foz do Iguaçu.

## Licença

Projeto acadêmico. Todos os direitos reservados aos autores.