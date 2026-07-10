# ✅ Comando Correto para Iniciar o Frontend

## ❌ Erro Identificado

Você está executando o comando no diretório **raiz** do projeto, mas o `package.json` está dentro da pasta `frontend`.

**Erro:**
```
ConfigError: The expected package.json path: 
/Users/zeuser/Documents/ProjetosPessoas/projeto-mercado/Atendente Salao trancista/package.json 
does not exist
```

## ✅ Solução

### Você precisa entrar no diretório `frontend` primeiro!

### Opção 1: Comando Completo (Recomendado)
```bash
cd "/Users/zeuser/Documents/ProjetosPessoas/projeto-mercado/Atendente Salao trancista/frontend"
npx expo start --clear
```

### Opção 2: Comando em Uma Linha
```bash
cd frontend && npx expo start --clear
```

### Opção 3: Usando npm (se estiver no diretório frontend)
```bash
cd frontend
npm start
```

## 📁 Estrutura do Projeto

```
Atendente Salao trancista/          ← Você estava aqui (ERRADO)
├── backend/
│   └── ...
└── frontend/                        ← Precisa estar AQUI
    ├── package.json                 ← package.json está aqui
    ├── app.json
    ├── app/
    └── src/
```

## 🚀 Passo a Passo Correto

### 1. Navegar para o diretório frontend:
```bash
cd frontend
```

### 2. Verificar que está no lugar certo:
```bash
pwd
# Deve mostrar: .../Atendente Salao trancista/frontend

ls package.json
# Deve mostrar: package.json
```

### 3. Iniciar o Expo:
```bash
npx expo start --clear
```

## ⚠️ Importante

- ✅ **Sempre execute** comandos do Expo dentro da pasta `frontend`
- ✅ **Verifique** que está no diretório correto com `pwd`
- ✅ **Use** `cd frontend` antes de qualquer comando do Expo

## 🔍 Verificação Rápida

Antes de executar, verifique:

```bash
# Deve mostrar "frontend" no caminho
pwd | grep frontend

# Deve encontrar o arquivo
test -f package.json && echo "✅ Correto!" || echo "❌ Errado! Entre em frontend/"
```

## 📋 Comandos Completos

### Para iniciar o frontend:
```bash
cd "/Users/zeuser/Documents/ProjetosPessoas/projeto-mercado/Atendente Salao trancista/frontend"
npx expo start --clear
```

### Para iniciar no web diretamente:
```bash
cd frontend
npm run web
```

### Para verificar se está no lugar certo:
```bash
cd frontend
pwd
ls package.json
```

---

**Resumo**: Sempre execute comandos do Expo dentro da pasta `frontend`!

**Comando correto:**
```bash
cd frontend && npx expo start --clear
```

