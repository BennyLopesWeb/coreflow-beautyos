# 🚀 Servidores Iniciando

## ✅ Status

Os servidores estão sendo iniciados em background:

### 🐍 Backend (FastAPI)
- **Porta**: 8000
- **Comando**: `uvicorn app.main:app --reload`
- **Status**: Iniciando...

### ⚛️ Frontend (Expo)
- **Porta**: 8081 (web) ou QR Code (mobile)
- **Comando**: `npx expo start --clear`
- **Status**: Iniciando...

## 📱 Acessos Disponíveis

### Backend
- **API Base**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Frontend

#### Mobile (Recomendado) 📱
1. Instale o **Expo Go** no celular
2. Escaneie o **QR Code** que aparece no terminal
3. A aplicação abrirá no celular

#### Web 🌐
- **URL**: http://localhost:8081
- ⚠️ **Nota**: Web tem limitações conhecidas com Expo Router

## ⏳ Aguarde

Os servidores levam alguns segundos para iniciar completamente. Aguarde até ver:
- ✅ Backend: Mensagem "Application startup complete"
- ✅ Frontend: QR Code no terminal ou "Metro waiting on..."

## 🛑 Parar Servidores

Para parar os servidores:
```bash
# Backend
pkill -f "uvicorn"

# Frontend
pkill -f "expo start"
```

## ✅ Verificar Status

```bash
# Verificar se backend está rodando
curl http://localhost:8000/health

# Verificar processos
ps aux | grep -E "(uvicorn|expo)"
```

---

**Status**: Iniciando... ⏳
