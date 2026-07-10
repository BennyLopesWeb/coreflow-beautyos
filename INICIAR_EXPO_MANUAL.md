# 🚀 Como Iniciar o Expo Manualmente

## ⚠️ Problema

O servidor Expo não está rodando, por isso o bundle falha ao carregar.

## ✅ Solução: Iniciar Manualmente

### Passo 1: Abrir Terminal
Abra um **novo terminal** na pasta do projeto.

### Passo 2: Navegar para Frontend
```bash
cd "/Users/zeuser/Documents/ProjetosPessoas/projeto-mercado/Atendente Salao trancista/frontend"
```

### Passo 3: Limpar Cache (Opcional)
```bash
rm -rf .expo
rm -rf node_modules/.cache
```

### Passo 4: Iniciar o Servidor
```bash
npx expo start --web
```

### Passo 5: Aguardar
Aguarde 30-60 segundos. Você verá no terminal:
```
Metro waiting on exp://...
```

### Passo 6: Acessar
- O navegador abrirá automaticamente
- Ou acesse: http://localhost:8081
- Ou pressione `w` no terminal

## 📱 Alternativa: Mobile (Recomendado)

Se tiver problemas no web, use o **Expo Go no celular**:

```bash
cd frontend
npx expo start  # sem --web
```

Depois escaneie o QR Code com Expo Go.

## 🔍 Verificar se Está Rodando

```bash
# Ver processos
ps aux | grep expo

# Testar conexão
curl http://localhost:8081
```

## ⚠️ Se Não Iniciar

### Verificar Erros
No terminal, veja se há mensagens de erro.

### Verificar Node
```bash
node --version  # Deve ser 18+
npm --version
```

### Reinstalar Dependências
```bash
cd frontend
rm -rf node_modules
npm install
npx expo start --web
```

---

**Execute manualmente no terminal:**
```bash
cd frontend
npx expo start --web
```

**Aguarde 30-60 segundos e acesse http://localhost:8081**

