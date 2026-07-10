# 🎯 Onde Usar o Token Após Login

## 📋 Resposta do Login

Quando você faz login, recebe esta resposta:

```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZW1haWwiOiJiZW5ueTRAZ21haWwuY29tIiwiZXhwIjoxNzY2ODQwNTcwLCJ0eXBlIjoiYWNjZXNzIn0.ErLtkDynW72v-KhTZ99RqKk2IS-5-5DmvgFGBk4JlkE",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZW1haWwiOiJiZW5ueTRAZ21haWwuY29tIiwiZXhwIjoxNzY3NDQzNTcwLCJ0eXBlIjoicmVmcmVzaCJ9.lJQsus_F5SF5UYJ_a8-xRtfTVi7L98-if3QIVJoA8ds",
    "token_type": "bearer",
    "expires_in": 1800
}
```

**🎯 COPIE APENAS O `access_token`** (o texto longo que começa com `eyJ...`)

## 🔑 O Que Fazer com o Token

### ✅ Use o `access_token` para:
- Acessar endpoints protegidos da API
- Fazer requisições autenticadas
- Identificar-se como usuário logado

### 💾 Guarde o `refresh_token` para:
- Renovar o `access_token` quando expirar (após 30 minutos)
- Não precisa usar em todas as requisições

---

## 🚀 Como Usar o Token

### 1. No Swagger UI (Mais Fácil) 🌐

#### Passo 1: Copiar o Token
Da resposta do login, copie **apenas o valor** de `access_token`:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZW1haWwiOiJiZW5ueTRAZ21haWwuY29tIiwiZXhwIjoxNzY2ODQwNTcwLCJ0eXBlIjoiYWNjZXNzIn0.ErLtkDynW72v-KhTZ99RqKk2IS-5-5DmvgFGBk4JlkE
```

#### Passo 2: Autorizar no Swagger
1. No topo da página do Swagger (http://localhost:8000/docs)
2. Clique no botão **"Authorize"** 🔒
3. No campo **"Value"**, cole o token (sem "Bearer")
4. Clique em **"Authorize"**
5. Clique em **"Close"**

#### Passo 3: Testar
Agora você pode testar qualquer endpoint protegido:
- `GET /auth/me` - Ver seu perfil
- `GET /clientes` - Listar clientes
- `POST /trancas` - Criar trança
- `GET /agenda/agendamentos` - Listar agendamentos
- E outros...

**✅ Pronto!** Todas as requisições no Swagger agora incluirão o token automaticamente!

---

### 2. Em Requisições HTTP (cURL, Postman, etc.) 🔧

#### Formato do Header

Adicione este header em todas as requisições protegidas:

```
Authorization: Bearer <seu_access_token>
```

#### Exemplo com cURL

```bash
# 1. Fazer login e salvar token
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"benny4@gmail.com","password":"senha123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 2. Usar o token em uma requisição
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer $TOKEN"
```

#### Exemplo Manual

```bash
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZW1haWwiOiJiZW5ueTRAZ21haWwuY29tIiwiZXhwIjoxNzY2ODQwNTcwLCJ0eXBlIjoiYWNjZXNzIn0.ErLtkDynW72v-KhTZ99RqKk2IS-5-5DmvgFGBk4JlkE"
```

---

### 3. No Frontend (JavaScript/React) 💻

#### Exemplo com Fetch

```javascript
// 1. Fazer login
const loginResponse = await fetch('http://localhost:8000/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'benny4@gmail.com',
    password: 'senha123'
  })
});

const { access_token } = await loginResponse.json();

// 2. Usar o token em requisições
const meResponse = await fetch('http://localhost:8000/auth/me', {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});

const userData = await meResponse.json();
console.log(userData);
```

#### Exemplo com Axios

```javascript
import axios from 'axios';

// 1. Fazer login
const loginResponse = await axios.post('http://localhost:8000/auth/login', {
  email: 'benny4@gmail.com',
  password: 'senha123'
});

const { access_token } = loginResponse.data;

// 2. Configurar token para todas as requisições
axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

// 3. Agora todas as requisições incluem o token automaticamente
const meResponse = await axios.get('http://localhost:8000/auth/me');
console.log(meResponse.data);
```

---

### 4. No Backend Python (Requests) 🐍

```python
import requests

# 1. Fazer login
login_response = requests.post(
    'http://localhost:8000/auth/login',
    json={
        'email': 'benny4@gmail.com',
        'password': 'senha123'
    }
)

access_token = login_response.json()['access_token']

# 2. Usar o token em requisições
headers = {
    'Authorization': f'Bearer {access_token}'
}

me_response = requests.get(
    'http://localhost:8000/auth/me',
    headers=headers
)

print(me_response.json())
```

---

## 📍 Endpoints que Precisam do Token

Estes endpoints **requerem** autenticação (precisam do token):

### Autenticação
- ✅ `GET /auth/me` - Ver perfil do usuário logado

### Clientes
- ✅ `POST /clientes` - Criar cliente
- ✅ `GET /clientes` - Listar clientes
- ✅ `PUT /clientes/{id}` - Atualizar cliente
- ✅ `DELETE /clientes/{id}` - Deletar cliente

### Tranças
- ✅ `POST /trancas` - Criar trança
- ✅ `PUT /trancas/{id}` - Atualizar trança
- ✅ `DELETE /trancas/{id}` - Deletar trança

### Agendamentos
- ✅ `GET /agenda/agendamentos` - Listar agendamentos
- ✅ `PUT /agenda/agendamentos/{id}` - Atualizar agendamento
- ✅ `DELETE /agenda/agendamentos/{id}` - Deletar agendamento

### Financeiro
- ✅ `GET /financeiro/resumo` - Ver resumo financeiro
- ✅ `POST /financeiro/saida` - Registrar saída

### Endpoints que NÃO precisam do token:
- ✅ `POST /auth/register` - Registrar usuário
- ✅ `POST /auth/login` - Fazer login
- ✅ `GET /trancas` - Listar tranças (público)
- ✅ `GET /agenda/disponibilidade` - Ver disponibilidade (público)
- ✅ `POST /agenda/agendamentos` - Criar agendamento (público)
- ✅ `POST /pagamentos/sinal` - Pagar sinal (público)
- ✅ `POST /fila/entrar` - Entrar na fila (público)

---

## ⏰ Validade do Token

- **Access Token**: Válido por **30 minutos** (1800 segundos)
- **Refresh Token**: Válido por **7 dias**

### O Que Fazer Quando o Token Expirar?

#### Opção 1: Fazer Login Novamente
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"seu_email","password":"sua_senha"}'
```

#### Opção 2: Usar Refresh Token
```bash
curl -X POST "http://localhost:8000/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "seu_refresh_token_aqui"
  }'
```

---

## 🧪 Teste Rápido

### 1. Fazer Login
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"benny4@gmail.com","password":"senha123"}'
```

### 2. Copiar o `access_token` da resposta

### 3. Testar Endpoint Protegido
```bash
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer <cole_o_token_aqui>"
```

### 4. Resposta Esperada
```json
{
  "id": 1,
  "email": "benny4@gmail.com",
  "nome": "Benigno Lopes",
  "telefone": "(48)99904-9779",
  "ativo": true,
  "created_at": "2025-12-27T12:11:11"
}
```

---

## 🎯 Resumo Visual

```
1. LOGIN
   POST /auth/login
   ↓
   Recebe: { access_token, refresh_token }
   
2. COPIAR TOKEN
   access_token: "eyJhbGciOiJIUzI1NiIs..."
   
3. USAR TOKEN
   Swagger: Botão "Authorize" → Colar token
   HTTP: Header "Authorization: Bearer <token>"
   
4. FAZER REQUISIÇÕES
   GET /auth/me
   GET /clientes
   POST /trancas
   etc...
```

---

## ✅ Checklist

- [ ] Fiz login e recebi o `access_token`
- [ ] Copiei o token (sem as aspas)
- [ ] No Swagger: Cliquei em "Authorize" e colei o token
- [ ] Testei um endpoint protegido (ex: `GET /auth/me`)
- [ ] Funcionou! ✅

---

**Dúvidas?** Acesse http://localhost:8000/docs e teste no Swagger UI! 🚀

