# 🔐 Como Usar Autorização (JWT Token)

## ⚡ GUIA RÁPIDO - ONDE PEGAR O TOKEN

### 🎯 Em 3 Passos Simples:

1. **Fazer Login no Swagger**
   - Acesse: http://localhost:8000/docs
   - Vá em `POST /auth/login` → "Try it out" → Preencha email/senha → "Execute"

2. **ONDE ESTÁ O TOKEN?**
   - Na resposta, procure por: `"access_token": "eyJhbGciOiJIUzI1NiIs..."`
   - **COPIE** todo o texto entre as aspas (sem as aspas)
   - Exemplo: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTcwMzQ1Njc4MH0.abc123...`

3. **Usar no Swagger**
   - Clique em **"Authorize"** 🔒 (topo da página)
   - Cole o token no campo "Value"
   - Clique em **"Authorize"** e **"Close"**

**✅ Pronto! Agora você pode usar todos os endpoints protegidos!**

---

## 📋 Formato do Token

O sistema usa **JWT Bearer Token**. O formato correto é:

```
Bearer <seu_token_aqui>
```

**⚠️ IMPORTANTE**: Inclua a palavra "Bearer" seguida de um espaço antes do token!

## 🚀 Passo a Passo no Swagger UI

### 1. Obter o Token (Fazer Login) - ONDE PEGAR O TOKEN

#### Passo 1: Acessar o Swagger
1. Abra seu navegador
2. Acesse: **http://localhost:8000/docs**
3. Você verá a documentação da API

#### Passo 2: Encontrar o Endpoint de Login
1. Procure pela seção **"Autenticação"** (ou "Auth")
2. Expanda o endpoint: **`POST /auth/login`**
3. Você verá os detalhes do endpoint

#### Passo 3: Executar o Login
1. Clique no botão **"Try it out"** (no canto direito do endpoint)
2. O formulário ficará editável
3. Preencha os dados no campo **"Request body"**:
   ```json
   {
     "email": "seu_email@example.com",
     "password": "sua_senha"
   }
   ```
   **💡 Dica**: Se ainda não tem usuário, primeiro crie um em `POST /auth/register`

#### Passo 4: Executar e Ver a Resposta
1. Clique no botão **"Execute"** (botão azul)
2. Aguarde alguns segundos
3. A página rolará automaticamente para mostrar a **"Responses"**

#### Passo 5: ONDE ESTÁ O TOKEN? 🎯
Na seção **"Responses"**, você verá algo assim:

```
Responses
├─ 200 (Success)
│  Response body:
│  {
│    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTcwMzQ1Njc4MH0.abc123xyz...",
│    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6InJlZnJlc2giLCJleHAiOjE3MDQwNjIzODB9.def456...",
│    "token_type": "bearer",
│    "expires_in": 1800
│  }
```

**🔍 ONDE ESTÁ O TOKEN?**
- Procure pela linha: `"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."`
- O token é aquele texto longo que começa com `eyJ` e vai até o final
- **COPIE TODO O TEXTO** entre as aspas (incluindo o `eyJ...` até o final)

**Exemplo visual:**
```
✅ CORRETO - Copie tudo isso:
"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTcwMzQ1Njc4MH0.abc123xyz789"

❌ ERRADO - Não copie as aspas:
"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  ← Não copie as aspas!
```

**📋 Resumo do que copiar:**
- ✅ Copie: O valor completo de `access_token` (sem as aspas)
- ✅ É um texto longo que parece: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTcwMzQ1Njc4MH0.abc123...`
- ❌ NÃO copie: `refresh_token` (esse é diferente)
- ❌ NÃO copie: As aspas ao redor do token
- ❌ NÃO copie: A palavra "Bearer" antes do token

**💡 Dica Rápida:**
- O token geralmente tem 3 partes separadas por pontos (`.`)
- Exemplo: `parte1.parte2.parte3`
- Copie todas as 3 partes!

### 2. Usar o Token no Swagger - COMO COLAR O TOKEN

#### Passo 1: Encontrar o Botão Authorize
1. **Role até o topo** da página do Swagger
2. No canto superior direito, você verá um botão: **"Authorize"** 🔒
3. Clique nele

#### Passo 2: Colar o Token
1. Uma janela modal abrirá
2. Você verá um campo chamado **"Value"** ou **"Bearer"**
3. **Cole o token que você copiou** do `access_token`
4. **IMPORTANTE**: Cole apenas o token, SEM a palavra "Bearer"
   - ✅ **Correto**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTcwMzQ1Njc4MH0.abc123...`
   - ❌ **Errado**: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

#### Passo 3: Confirmar
1. Clique no botão **"Authorize"** (dentro da janela modal)
2. Você verá um ✅ indicando que está autorizado
3. Clique em **"Close"** para fechar a janela

**💡 Nota**: O Swagger adiciona automaticamente "Bearer" antes do token quando você faz requisições!

### 3. Testar Endpoints Protegidos

Agora você pode testar qualquer endpoint protegido:
- `GET /auth/me` - Ver seu perfil
- `POST /trancas` - Criar trança
- `GET /clientes` - Listar clientes
- `GET /agenda/agendamentos` - Listar agendamentos
- E outros...

## 📸 Exemplo Prático Completo

### Cenário: Você acabou de fazer login

**1. Você executou o login e recebeu esta resposta:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTcwMzQ1Njc4MH0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6InJlZnJlc2giLCJleHAiOjE3MDQwNjIzODB9.def456xyz",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**2. ONDE ESTÁ O TOKEN QUE VOCÊ PRECISA?**

```
┌─────────────────────────────────────────────────────────────┐
│ Response body:                                              │
│                                                             │
│ {                                                           │
│   "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... │ ← COPIE ESTE!
│   "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... │ ← NÃO copie
│   "token_type": "bearer",                                   │
│   "expires_in": 1800                                        │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘
```

**3. O QUE VOCÊ DEVE COPIAR?**

✅ **COPIE ISSO** (todo o texto, sem as aspas):
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTcwMzQ1Njc4MH0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

❌ **NÃO COPIE ISSO**:
- `"access_token":` (o nome do campo)
- As aspas `"` ao redor
- `Bearer` antes do token
- O `refresh_token` (é diferente!)

**4. AGORA COLE NO SWAGGER:**

1. Clique em **"Authorize"** 🔒 (topo da página)
2. No campo **"Value"**, cole o token que você copiou
3. Clique em **"Authorize"**
4. Clique em **"Close"**

**5. TESTE SE FUNCIONOU:**

1. Vá em `GET /auth/me`
2. Clique em **"Try it out"**
3. Clique em **"Execute"**
4. Se retornar seus dados, está funcionando! ✅

---

## 📝 Exemplos Práticos

### Exemplo 1: Token Completo
```
Token recebido do login:
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTcwMzQ1Njc4MH0.abc123xyz

No Swagger "Authorize", cole apenas:
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTcwMzQ1Njc4MH0.abc123xyz
```

### Exemplo 2: Usando cURL
```bash
# Fazer login e obter token
TOKEN=$(curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"teste@example.com","password":"senha123"}' \
  | jq -r '.access_token')

# Usar token em requisição
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer $TOKEN"
```

### Exemplo 3: Usando JavaScript/Fetch
```javascript
// Fazer login
const loginResponse = await fetch('http://localhost:8000/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'teste@example.com',
    password: 'senha123'
  })
});

const { access_token } = await loginResponse.json();

// Usar token
const meResponse = await fetch('http://localhost:8000/auth/me', {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});
```

## 🔍 Verificar se o Token Está Funcionando

### Teste Rápido
1. No Swagger, vá em `GET /auth/me`
2. Clique em **"Try it out"**
3. Clique em **"Execute"**
4. Se retornar seus dados do usuário, o token está funcionando! ✅

### Se Der Erro 401
- ❌ Token expirado → Faça login novamente
- ❌ Token inválido → Verifique se copiou corretamente
- ❌ Token não autorizado → Verifique se está usando o `access_token` (não o `refresh_token`)

## ⏰ Validade do Token

- **Access Token**: Válido por **30 minutos** (padrão)
- **Refresh Token**: Válido por **7 dias** (padrão)

### Renovar Token (Refresh)
Se o token expirar, use o `refresh_token`:

1. Endpoint: `POST /auth/refresh`
2. Body:
   ```json
   {
     "refresh_token": "seu_refresh_token_aqui"
   }
   ```
3. Receberá um novo `access_token`

## 🎯 Resumo Rápido - ONDE PEGAR O TOKEN

### No Swagger UI - Passo a Passo Visual:

1. ✅ **Acesse**: http://localhost:8000/docs
2. ✅ **Encontre**: Seção "Autenticação" → `POST /auth/login`
3. ✅ **Clique**: "Try it out"
4. ✅ **Preencha**: Email e senha no Request body
5. ✅ **Clique**: "Execute"
6. ✅ **OLHE A RESPOSTA**: Na seção "Responses" → "200 (Success)"
7. ✅ **COPIE**: O valor de `"access_token"` (todo o texto longo, sem as aspas)
   - Exemplo: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTcwMzQ1Njc4MH0.abc123...`
8. ✅ **Clique**: Botão "Authorize" 🔒 (no topo da página)
9. ✅ **Cole**: O token no campo "Value" (sem "Bearer")
10. ✅ **Clique**: "Authorize" e depois "Close"
11. ✅ **Pronto!** Todos os endpoints protegidos funcionarão

### 📍 ONDE ESTÁ O TOKEN NA RESPOSTA?

```
POST /auth/login → Execute → Responses:

┌─────────────────────────────────────────┐
│ 200 (Success)                           │
│                                         │
│ Response body:                          │
│ {                                       │
│   "access_token": "eyJhbGciOiJIUzI1NiIs │ ← AQUI! Copie este valor
│   InR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlw │
│   ZSI6ImFjY2VzcyIsImV4cCI6MTcwMzQ1Njc4M │
│   H0.abc123xyz..."                      │
│   "refresh_token": "...",               │ ← NÃO copie este
│   "token_type": "bearer",               │
│   "expires_in": 1800                    │
│ }                                       │
└─────────────────────────────────────────┘
```

**🎯 COPIE APENAS**: O texto entre as aspas de `"access_token"` (sem as aspas)

### Formato:
- **No Swagger**: Cole apenas o token (sem "Bearer")
- **Em requisições HTTP**: Use `Authorization: Bearer <token>`
- **No código**: Use `Bearer <token>` no header

## ⚠️ Importante

- ✅ Use sempre o `access_token` (não o `refresh_token`)
- ✅ O token expira em 30 minutos
- ✅ Se expirar, faça login novamente ou use refresh
- ✅ No Swagger, não precisa incluir "Bearer" (ele adiciona automaticamente)

---

**Dúvidas?** Teste o endpoint `GET /auth/me` após autorizar - se funcionar, está tudo certo! ✅

