# NaipiCar

**Plataforma web de consulta e reserva de veículos para pequenas e médias locadoras de Foz do Iguaçu.**

O cliente consulta o catálogo, escolhe o período e reserva online. O administrador gerencia a frota e acompanha as reservas. Projeto Integrador do curso de Tecnologia em Análise e Desenvolvimento de Sistemas do **IFPR – Campus Foz do Iguaçu**.

> **Status:** em desenvolvimento. Veja a tabela de funcionalidades abaixo para saber o que já está pronto.

---

## Sobre o projeto

Muitas locadoras pequenas e médias ainda controlam reservas por balcão, telefone e aplicativos de mensagem. Isso gera demora no atendimento, informações repetidas e dificuldade para saber quais veículos estão livres em cada período.

O NaipiCar propõe um ambiente digital para:

- **Clientes:** cadastrar-se, consultar o catálogo de veículos, verificar a disponibilidade por período, reservar e acompanhar as próprias reservas.
- **Administradores:** gerenciar a frota, as categorias e diárias, e acompanhar e atualizar a situação das reservas.

## Funcionalidades

| Requisito | Funcionalidade | Situação |
|---|---|---|
| RF01 | Cadastro de cliente (nome, CPF, e-mail, telefone, endereço, senha forte e aceite dos termos) | Pronto |
| RF02 | Login com e-mail e senha; administrador vai para o painel e cliente para o catálogo | Pronto |
| RF03 | Catálogo de veículos com foto, modelo, ano, categoria e valor da diária | Em andamento |
| RF04 | Busca por data de retirada, data de devolução e categoria | Planejado |
| RF05 | Cadastro, edição e visualização de veículos (hoje pelo `/admin/` do Django) | Em andamento |
| RF06 | Dashboard gerencial (ocupação, atrasos, receita estimada, categorias mais demandadas) | Planejado |
| RF07 / RF08 | Gestão de reservas pelo administrador (busca, filtros e alteração de situação) | Em andamento |
| RF09 | "Minhas reservas" do cliente, com histórico, valor e situação | Pronto |
| RF10 | Solicitação de cancelamento pelo cliente | Planejado |
| RF11 | Edição de perfil | Planejado |

O valor total da reserva é calculado automaticamente (número de diárias × diária da categoria/classe do veículo).

## Tecnologias

- **Python 3.12+**
- **Django 6.1** (autenticação, ORM, painel administrativo)
- **Bootstrap 5** (interface responsiva)
- **SQLite** no desenvolvimento. O **MySQL** é o banco previsto no projeto (requisito RNF04) e a migração está planejada.
- **Pillow** (upload de imagens dos veículos)

## Como executar

### Pré-requisitos

- [Git](https://git-scm.com/)
- [Python 3.12 ou superior](https://www.python.org/downloads/) (no Windows, marque **Add python.exe to PATH** na instalação). No Linux, o script automático abaixo instala o Python necessário sozinho, sem precisar de `sudo`.

### Opção 1: instalação automática (recomendada)

```bash
git clone <URL-DO-REPOSITORIO>
cd naipicar
```

**Linux / macOS:**

```bash
chmod +x setup.sh
./setup.sh
```

**Windows:** dê dois cliques em `setup.bat` (ou rode `setup.bat` no terminal).

O script cria o ambiente virtual, instala as dependências, cria o banco de dados e importa as marcas e modelos de carros. Ao final, falta apenas criar o administrador e iniciar o servidor:

```bash
# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate

python manage.py createsuperuser   # pede e-mail, nome, sobrenome, CPF e telefone
python manage.py runserver
```

### Opção 2: passo a passo manual

```bash
# 1. Clonar o repositório
git clone <URL-DO-REPOSITORIO>
cd naipicar

# 2. Criar e ativar o ambiente virtual
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux / macOS

# 3. Instalar as dependências
python -m pip install -r requirements.txt

# 4. Criar o banco de dados
python manage.py migrate

# 5. Criar o usuário administrador (pede e-mail, nome, sobrenome, CPF e telefone)
python manage.py createsuperuser

# 6. Importar marcas e modelos de carros (arquivos CSV do projeto)
python manage.py importar_carros

# 7. Iniciar o servidor
python manage.py runserver
```

> No Windows (PowerShell), se o passo 2 der erro de "execução de scripts desabilitada", rode uma vez:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### Problemas comuns

**`ensurepip is not available` ao criar o ambiente virtual (Ubuntu/Debian):** o pacote `python3-venv` não está instalado. Se você não tem `sudo`, use o `setup.sh`, que usa o [uv](https://docs.astral.sh/uv/) e dispensa esse pacote. Se tiver `sudo`:

```bash
sudo apt update
sudo apt install python3-venv
```

**Versão do Python menor que 3.12:** o Django 6.x exige Python 3.12 ou superior. O `setup.sh` resolve isso baixando o Python correto via `uv`. Manualmente:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
uv venv --python 3.12 venv
source venv/bin/activate
uv pip install -r requirements.txt
```

### Endereços

| Página | Endereço |
|---|---|
| Catálogo | http://127.0.0.1:8000/ |
| Criar conta | http://127.0.0.1:8000/cadastro/ |
| Entrar | http://127.0.0.1:8000/login/ |
| Administração | http://127.0.0.1:8000/admin/ |

### Primeiros passos no sistema

1. Entre em `/admin/` com o administrador criado e cadastre as **categorias**, **classes** e a **diária de cada combinação** (Categoria × Classe).
2. Cadastre os **veículos** com foto, placa, ano e a categoria/classe.
3. Crie uma conta de cliente em `/cadastro/` e faça uma reserva pelo catálogo.

## Testes

```bash
python manage.py test
```

## Estrutura do projeto

```
naipicar/
├── manage.py
├── requirements.txt
├── setup.sh                   # instalação automática (Linux / macOS)
├── setup.bat                  # instalação automática (Windows)
├── .gitignore
├── naipicar/                  # configurações do projeto (settings, urls)
├── contas/                    # usuários e endereços: cadastro, login e validações
│   ├── models.py
│   ├── forms.py
│   └── templates/contas/
├── locacao/                   # frota e reservas
│   ├── models.py
│   ├── views.py
│   ├── templates/locacao/
│   └── management/commands/importar_carros.py
├── marcas-carros.csv          # dados para importação
├── modelos-carro.csv
└── media/                     # fotos enviadas
```

## Modelagem do banco de dados

O banco segue o dicionário de dados do projeto, com 9 entidades:

- **Usuário** e **Endereço**: cadastro e autenticação dos clientes e administradores.
- **Marca**, **Modelo**, **Categoria**, **Classe** e **Categoria × Classe**: classificação dos veículos. A diária é definida pela combinação de categoria e classe.
- **Veículo**: unidade física disponível para locação.
- **Reserva**: liga o usuário ao veículo, com período, valor total e situação (em análise, reservada, atrasada, concluída ou cancelada).

## Segurança

- Senhas armazenadas apenas como hash (PBKDF2), nunca em texto.
- Regra de senha: mínimo de 8 caracteres, com letra maiúscula, número e símbolo.
- Validação de CPF e unicidade de CPF e e-mail.
- Proteção CSRF nos formulários e uso do ORM do Django (consultas parametrizadas).
- Tratamento de dados pessoais conforme os princípios da LGPD.

## Próximos passos

- Impedir reservas em períodos já ocupados e exigir login para reservar.
- Filtro do catálogo por data e categoria.
- Painel administrativo com dashboard e gestão de reservas.
- Cancelamento pelo cliente e edição de perfil com foto.
- Migração para MySQL.
- Integração com meios de pagamento e notificações automáticas.

## Equipe

Projeto desenvolvido por **Bruno**, **Nathan** e **Milan**, estudantes de Tecnologia em Análise e Desenvolvimento de Sistemas do Instituto Federal do Paraná (IFPR), Campus Foz do Iguaçu.

## Licença

Projeto acadêmico. Todos os direitos reservados aos autores.

PASSO A PASSO PARA RODAR O DOCUEMENTO

1- TEM PYTHON INSTALADO 
2- INSTALAR A EXTENSÂO DO DJANGO 
3- CRIAR A PASTA VENV (python -m venv venv) 
4- ATIVAR VENV (venv\Scripts\activate) 
5- INSTALAR ISSO DAQUI (python -m pip install Pillow)  python -m pip install django
6- CRIAR O SEU USUARIO ADMIN (python manage.py createsuperseur) email e opcional, nome ele aparece o do dispositivo caso nao estaja aparecendo tem que colocar. 
7- RODAR O SERVIDOR (python manage.py runserver) 
8- CASO NO PAINEL ADMIN EM MARCAR E MODELOS NAO ESTEJA APARECENDO NADA RODAR ESSE CODIGO (python manage.py importar\_carros)

TENTA DESSE JEITO SE NAO DER CERTO PODE SER QUE EU TENHA ESQUECIDO DE ALGUMA COISA MAIS DEIXEI ABAIXO UM PASSO A PASSpO QUE A IA FEZ, É QUE EU NAO SEI MUITO BEM SE ELE JA VAI PUXAR TODAS AS INFORMAÇÔES AUTOMATICO

