# Guia de Instalação - TrançaPro

## Pré-requisitos

- Python 3.9+
- Node.js 16+
- PostgreSQL 12+
- pip (gerenciador de pacotes Python)
- npm ou yarn (gerenciador de pacotes Node)

## Instalação do Backend

### 1. Configurar ambiente virtual Python

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar banco de dados

1. Crie um banco de dados PostgreSQL:

```sql
CREATE DATABASE trancapro;
```

2. Copie o arquivo `.env.example` para `.env`:

```bash
cp .env.example .env
```

3. Edite o arquivo `.env` e configure:

```env
DATABASE_URL=postgresql://usuario:senha@localhost:5432/trancapro
SECRET_KEY=sua-chave-secreta-aqui
```

### 4. Executar migrations

```bash
alembic upgrade head
```

### 5. Iniciar servidor

```bash
uvicorn app.main:app --reload
```

O servidor estará disponível em `http://localhost:8000`

Documentação da API: `http://localhost:8000/docs`

## Instalação do Frontend

### 1. Instalar dependências

```bash
cd frontend
npm install
```

### 2. Configurar variáveis de ambiente

Crie um arquivo `.env` na pasta `frontend`:

```env
REACT_APP_API_URL=http://localhost:8000
```

### 3. Iniciar aplicação

```bash
npm start
```

A aplicação estará disponível em `http://localhost:3000`

## Primeiro Usuário

Para criar o primeiro usuário, você pode:

1. Usar o endpoint de registro:

```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@trancapro.com",
    "nome": "Administrador",
    "password": "senha123"
  }'
```

2. Ou criar diretamente no banco de dados (senha deve ser hasheada com bcrypt)

## Configuração Google Calendar (Opcional)

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto
3. Ative a API do Google Calendar
4. Crie credenciais OAuth 2.0
5. Baixe o arquivo JSON e salve como `credentials.json` na pasta `backend`
6. Na primeira execução, o sistema solicitará autorização

## Configuração Pix (Opcional)

Para integração real com Pix, você precisará:

1. Escolher um provedor (Asaas, Mercado Pago, etc.)
2. Obter credenciais de API
3. Atualizar o arquivo `backend/app/domain/agendamentos/integrations.py`
4. Configurar variáveis no `.env`:

```env
PIX_MERCHANT_ID=seu-merchant-id
PIX_API_KEY=sua-api-key
```

## Estrutura do Projeto

```
trancapro/
├── backend/
│   ├── app/
│   │   ├── domain/          # Domínios organizados
│   │   │   ├── auth/
│   │   │   ├── clientes/
│   │   │   ├── servicos/
│   │   │   ├── agendamentos/
│   │   │   ├── financeiro/
│   │   │   └── mensagens/
│   │   ├── shared/          # Código compartilhado
│   │   ├── main.py          # Aplicação FastAPI
│   │   └── ...
│   ├── alembic/             # Migrations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # Componentes React
│   │   ├── pages/           # Páginas
│   │   ├── contexts/        # Context API
│   │   └── utils/           # Utilitários
│   └── package.json
└── README.md
```

## Troubleshooting

### Erro de conexão com banco de dados

- Verifique se o PostgreSQL está rodando
- Confirme as credenciais no `.env`
- Teste a conexão: `psql -U usuario -d trancapro`

### Erro de CORS no frontend

- Verifique se a URL da API está correta no `.env` do frontend
- Confirme que o backend está rodando

### Erro de migrations

- Verifique se o banco de dados existe
- Confirme que o usuário tem permissões
- Execute: `alembic current` para verificar estado

## Produção

Para deploy em produção:

1. Configure variáveis de ambiente adequadas
2. Use um servidor WSGI (Gunicorn, uWSGI)
3. Configure HTTPS
4. Use um banco de dados gerenciado
5. Configure CORS adequadamente
6. Use variáveis de ambiente seguras

