# ✅ Solução: Erros 500 no Manifest e Favicon

## 🔍 Problema Identificado

No Network tab, você vê erros **500** para:
- `manifest.json` - Status 500
- `favicon.ico` - Status 500

**Erros no Console**:
```
GET http://localhost:8081/%PUBLIC_URL%/favicon.ico 500
GET http://localhost:8081/%PUBLIC_URL%/manifest.json 500
```

**Causa**: A pasta `public/` contém arquivos do Create React App que usam `%PUBLIC_URL%`, que não existe no Expo. O Expo gerencia esses arquivos automaticamente.

## ✅ Soluções Aplicadas

### 1. Removida Pasta `public/`
A pasta `public/` foi removida porque:
- Contém arquivos do Create React App (não Expo)
- Usa `%PUBLIC_URL%` que não funciona no Expo
- O Expo gerencia favicon e manifest via `app.json`

### 2. Corrigido `web/index.html`
Removida referência ao bundle script (o Expo injeta automaticamente).

### 3. Limpeza e Reinício
- Pasta `public/` removida
- Cache limpo
- Servidor reiniciado

## 🚀 Como Testar Agora

### 1. Aguardar Compilação
Aguarde 30-60 segundos para o servidor compilar.

### 2. Acessar
- **URL**: http://localhost:8081
- Ou pressione `w` no terminal do Expo

### 3. Verificar
- ✅ Não deve mais ter erros 500 no Network tab
- ✅ Console não deve mostrar erros de manifest/favicon
- ✅ Tela de login deve aparecer

## 📋 Arquivos Removidos/Modificados

1. ✅ `frontend/public/` - Pasta removida (não necessária no Expo)
2. ✅ `frontend/web/index.html` - Corrigido (removido script manual)

## 🔧 Configuração Correta do Expo

O Expo gerencia favicon e manifest via `app.json`:

```json
{
  "expo": {
    "web": {
      "favicon": "./assets/favicon.png"
    }
  }
}
```

Não precisa de pasta `public/` ou arquivos `manifest.json` separados.

## ⚠️ Se Ainda Tiver Problemas

### Limpar Tudo
```bash
cd frontend
pkill -f expo
rm -rf .expo
rm -rf node_modules/.cache
npx expo start --clear --web
```

### Verificar Assets
Certifique-se de que existe `assets/favicon.png`:
```bash
ls -la frontend/assets/favicon.png
```

### Usar Mobile (Recomendado)
Se ainda tiver problemas no web, use o **Expo Go no celular**:
1. Inicie: `npx expo start` (sem --web)
2. Escaneie o QR Code
3. A aplicação abrirá no celular

## 🎯 Status

- ✅ Pasta `public/` removida
- ✅ `web/index.html` corrigido
- ✅ Cache limpo
- ✅ Servidor reiniciado
- ⏳ Aguardando compilação...

---

**Aguarde alguns segundos e acesse**: http://localhost:8081

**Os erros 500 devem desaparecer!** ✅

