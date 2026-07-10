# ✅ Solução: ERR_CONNECTION_REFUSED no Frontend

## 🔍 Problema Identificado

Ao acessar `http://localhost:19006`, você recebe:
```
ERR_CONNECTION_REFUSED
Não é possível acessar esse site
A conexão com localhost foi recusada.
```

**Causa**: O servidor Expo não está rodando na porta 19006 (ou em nenhuma porta).

## ✅ Soluções

### Solução 1: Verificar se o Servidor Está Rodando

```bash
# Verificar processos do Expo
ps aux | grep expo

# Verificar portas em uso
lsof -i :8081
lsof -i :19006
```

### Solução 2: Iniciar o Frontend Corretamente

#### Opção A: Iniciar com Web (Recomendado)
```bash
cd frontend
npx expo start --web
```

Isso iniciará o servidor e abrirá automaticamente no navegador.

#### Opção B: Iniciar Normal e Usar Mobile
```bash
cd frontend
npx expo start
```

Depois:
- Escaneie o QR Code com Expo Go (mobile)
- Ou pressione `w` no terminal para abrir no navegador

### Solução 3: Usar Porta Específica

```bash
cd frontend
npx expo start --web --port 8081
```

Acesse: http://localhost:8081

## 🚀 Passo a Passo Completo

### 1. Parar Todos os Processos Expo
```bash
pkill -f expo
# ou
pkill -f "expo start"
```

### 2. Limpar Cache
```bash
cd frontend
rm -rf .expo
rm -rf node_modules/.cache
```

### 3. Reiniciar o Frontend
```bash
cd frontend
npx expo start --clear --web
```

### 4. Aguardar e Acessar
- Aguarde 30-60 segundos para o servidor compilar
- O Expo abrirá automaticamente no navegador
- Ou acesse: http://localhost:8081

## 📱 Alternativa: Usar Mobile (Melhor Experiência)

Se tiver problemas com web, use o **Expo Go no celular**:

1. **Instale o Expo Go** no celular (iOS/Android)
2. **Inicie o servidor**:
   ```bash
   cd frontend
   npx expo start
   ```
3. **Escaneie o QR Code** que aparece no terminal
4. A aplicação abrirá no celular

## 🔍 Verificar Status

### Verificar se o servidor está rodando:
```bash
# Ver processos
ps aux | grep expo

# Ver portas
lsof -i :8081
lsof -i :19006

# Testar conexão
curl http://localhost:8081
```

### Ver logs do servidor:
Verifique o terminal onde você executou `npx expo start`

## ⚠️ Problemas Comuns

### Porta já em uso
```bash
# Ver qual processo está usando a porta
lsof -i :8081

# Matar o processo
kill -9 <PID>
```

### Servidor não inicia
```bash
# Verificar se há erros
cd frontend
npx expo start --web

# Verificar dependências
npm install
```

### Cache corrompido
```bash
cd frontend
rm -rf .expo
rm -rf node_modules/.cache
npx expo start --clear --web
```

## 🎯 URLs Corretas

### Durante o desenvolvimento:
- **Metro Bundler**: http://localhost:8081
- **Web (se configurado)**: http://localhost:19006
- **Ou use o QR Code** para mobile

### Após iniciar o Expo:
O terminal mostrará algo como:
```
Metro waiting on exp://192.168.0.6:8081
```

Para web, pressione `w` no terminal ou acesse a URL que aparece.

## 📋 Checklist

- [ ] Processos Expo anteriores parados
- [ ] Cache limpo
- [ ] Frontend iniciado com `npx expo start --web`
- [ ] Aguardado 30-60 segundos para compilar
- [ ] Acessado a URL correta (http://localhost:8081)
- [ ] Ou usado mobile (Expo Go)

## 🚀 Comando Rápido

```bash
# Parar tudo
pkill -f expo

# Limpar e reiniciar
cd frontend
rm -rf .expo
npx expo start --clear --web
```

## 💡 Dica

**Para melhor experiência, use o Expo Go no celular:**
- Melhor performance
- Funcionalidades nativas
- Sem problemas de porta/web

---

**Status**: Frontend sendo reiniciado... ⏳

**Aguarde alguns segundos e tente:**
- http://localhost:8081
- Ou escaneie o QR Code para mobile

