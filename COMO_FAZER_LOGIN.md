# 🔐 Como Fazer Login na API

## ❌ Erro Comum

Se você receber este erro:
```json
{
    "error": true,
    "message": "Erro de validação",
    "errors": [
        {
            "type": "missing",
            "loc": ["body"],
            "msg": "Field required"
        }
    ]
}
```

**Causa**: O endpoint `/auth/login` requer um **POST com body JSON**, não um GET simples.

## ✅ Forma Correta de Fazer Login

### 1. No Swagger UI (Recomendado)

1. **Acesse**: http://localhost:8000/docs
2. **Encontre**: Seção "Autenticação" → `POST /auth/login`
3. **Clique**: "Try it out"
4. **Preencha o Request body**:
   ```json
   {
     "email": "seu_email@gmail.com",
     "password": "sua_senha"
   }
   ```
5. **Clique**: "Execute"
6. **Copie o `access_token`** da resposta

### 2. Via cURL (Terminal)

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "seu_email@gmail.com",
    "password": "sua_senha"
  }'
```

### 3. Via JavaScript/Fetch

```javascript
const response = await fetch('http://localhost:8000/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    email: 'seu_email@gmail.com',
    password: 'sua_senha'
  })
});

const data = await response.json();
console.log(data.access_token); // Seu token JWT
```

### 4. Via Python/Requests

```python
import requests

response = requests.post(
    'http://localhost:8000/auth/login',
    json={
        'email': 'seu_email@gmail.com',
        'password': 'sua_senha'
    }
)

data = response.json()
access_token = data['access_token']
print(access_token)
```

## 📋 Exemplo Completo

### Requisição:
```http
POST /auth/login HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "email": "benny4@gmail.com",
  "password": "senha123"
}
```

### Resposta de Sucesso (200):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZW1haWwiOiJiZW5ueTRAZ21haWwuY29tIiwiZXhwIjoxNzY2ODQwNDYxLCJ0eXBlIjoiYWNjZXNzIn0._gsC6PymEepaI5HIfobowJPIf99ZiNcSUkkoSCQ1jA8",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZW1haWwiOiJiZW5ueTRAZ21haWwuY29tIiwiZXhwIjoxNzY3NDQzNDYxLCJ0eXBlIjoicmVmcmVzaCJ9.u4IzaaClZYFjTQ0p6ZN3vbZspDwGRmFYzxF2UVGKb3Y",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Resposta de Erro (401):
```json
{
  "error": true,
  "message": "Email ou senha incorretos",
  "path": "/auth/login"
}
```

## ⚠️ Erros Comuns

### 1. Erro: "Field required" (body)"
**Causa**: Não está enviando o body JSON ou está fazendo GET em vez de POST.

**Solução**: 
- ✅ Use **POST** (não GET)
- ✅ Inclua o header `Content-Type: application/json`
- ✅ Envie o body JSON com `email` e `password`

### 2. Erro: "Email ou senha incorretos"
**Causa**: Credenciais inválidas ou usuário não existe.

**Solução**:
- ✅ Verifique se o email está correto
- ✅ Verifique se a senha está correta
- ✅ Se não tem usuário, crie um primeiro em `POST /auth/register`

### 3. Erro: "Email inválido"
**Causa**: Formato de email inválido.

**Solução**: Use um email válido, exemplo: `usuario@exemplo.com`

## 🔑 Usando o Token Após Login

Após fazer login e obter o `access_token`, você pode:

1. **No Swagger**: Clique em "Authorize" e cole o token
2. **Em requisições HTTP**: Adicione o header:
   ```
   Authorization: Bearer <seu_token_aqui>
   ```

## 📝 Exemplo Prático Completo

### Passo 1: Fazer Login
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"benny4@gmail.com","password":"senha123"}'
```

### Passo 2: Copiar o Token
Da resposta, copie o `access_token`:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Passo 3: Usar o Token
```bash
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## 🎯 Resumo Rápido

1. ✅ Use **POST** (não GET)
2. ✅ Envie **body JSON** com `email` e `password`
3. ✅ Inclua header `Content-Type: application/json`
4. ✅ Copie o `access_token` da resposta
5. ✅ Use o token no header `Authorization: Bearer <token>`

---

**Dúvidas?** Acesse http://localhost:8000/docs e teste diretamente no Swagger UI! 🚀

