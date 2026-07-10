# 🚀 Como Iniciar o Frontend Corretamente

## ⚠️ Problema: ERR_CONNECTION_REFUSED

Se você está recebendo `ERR_CONNECTION_REFUSED`, o servidor Expo não está rodando.

## ✅ Solução: Iniciar Manualmente

### Passo 1: Abrir Terminal
Abra um novo terminal na pasta do projeto.

### Passo 2: Navegar para Frontend
```bash
cd "/Users/zeuser/Documents/ProjetosPessoas/projeto-mercado/Atendente Salao trancista/frontend"
```

### Passo 3: Iniciar o Servidor
```bash
npx expo start --web
```

### Passo 4: Aguardar
Aguarde 30-60 segundos. Você verá no terminal:
```
Metro waiting on exp://...
```

### Passo 5: Acessar
- O navegador abrirá automaticamente
- Ou acesse: http://localhost:8081
- Ou pressione `w` no terminal

## 📱 Alternativa: Mobile (Recomendado)

### 1. Iniciar sem --web
```bash
cd frontend
npx expo start
```

### 2. Escanear QR Code
- Instale o app **Expo Go** no celular
- Escaneie o QR Code que aparece no terminal
- A aplicação abrirá no celular

## 🔍 Verificar se Está Rodando

```bash
# Ver processos
ps aux | grep expo

# Testar conexão
curl http://localhost:8081
```

## ⚠️ Se Não Funcionar

### Limpar tudo e reiniciar:
```bash
cd frontend
pkill -f expo
rm -rf .expo
rm -rf node_modules/.cache
npx expo start --clear --web
```

## 💡 Dica Importante

**O Expo funciona melhor no mobile!** Use o Expo Go para a melhor experiência:
- ✅ Melhor performance
- ✅ Funcionalidades nativas
- ✅ Sem problemas de porta/web

---

**Execute manualmente no terminal:**
```bash
cd frontend
npx expo start --web
```
