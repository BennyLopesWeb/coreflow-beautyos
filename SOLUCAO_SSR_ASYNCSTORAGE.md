# ✅ Solução: Erro "Cannot convert undefined or null to object" (SSR)

## 🔍 Problema Identificado

**Erro**: 
```
Static Rendering Error (Node.js)
Cannot convert undefined or null to object
```

**Causa**: O Expo Router está tentando fazer renderização estática (SSR) no servidor Node.js, mas o `AsyncStorage` não funciona no servidor. O `AsyncStorage` só funciona no cliente (navegador/mobile).

## ✅ Soluções Aplicadas

### 1. Removido `output: "static"` do app.json
Removida a configuração que força renderização estática:
```json
"web": {
  "favicon": "./assets/favicon.png",
  "bundler": "metro"
  // ❌ Removido: "output": "static"
}
```

### 2. Adicionadas Verificações de Cliente no AuthContext

**Problema**: O `AsyncStorage` estava sendo chamado durante SSR.

**Solução**: Adicionadas verificações `typeof window !== 'undefined'` antes de usar `AsyncStorage`:

```typescript
// Antes de usar AsyncStorage, verifica se está no cliente
if (typeof window !== 'undefined') {
  // Código que usa AsyncStorage
}
```

### 3. Correções Aplicadas

#### `checkAuth()`:
- ✅ Verifica `typeof window !== 'undefined'` antes de executar
- ✅ Se estiver no servidor, apenas define `loading = false`

#### `login()`:
- ✅ Verifica se está no cliente antes de usar AsyncStorage

#### `logout()`:
- ✅ Verifica se está no cliente antes de usar AsyncStorage

## 🚀 Como Testar

### 1. Aguardar Compilação
Aguarde 30-60 segundos para o servidor compilar.

### 2. Acessar
- **URL**: http://localhost:8081
- Ou pressione `w` no terminal do Expo

### 3. Verificar
- ✅ Não deve mais ter erro "Cannot convert undefined or null to object"
- ✅ Tela de login deve aparecer
- ✅ Console não deve mostrar erros de SSR

## 📋 Arquivos Modificados

1. ✅ `app.json` - Removido `output: "static"`
2. ✅ `src/contexts/AuthContext.tsx` - Adicionadas verificações de cliente

## 🔧 Explicação Técnica

### Por que o erro acontecia?

1. **SSR (Server-Side Rendering)**: O Expo Router tenta renderizar no servidor Node.js
2. **AsyncStorage**: Só funciona no cliente (navegador/mobile), não no servidor
3. **Erro**: Quando o código tenta usar `AsyncStorage` no servidor, retorna `undefined` ou `null`
4. **Object.keys()**: Algum código interno do Expo tenta fazer `Object.keys()` em algo `undefined/null`

### Solução

- **Verificação de Cliente**: `typeof window !== 'undefined'` detecta se está no cliente
- **No Servidor**: Pula código que usa AsyncStorage
- **No Cliente**: Executa normalmente

## ⚠️ Se Ainda Tiver Problemas

### Limpar Tudo
```bash
cd frontend
pkill -f expo
rm -rf .expo
rm -rf node_modules/.cache
npx expo start --clear --web
```

### Desabilitar SSR Completamente
Se ainda tiver problemas, você pode forçar renderização apenas no cliente adicionando no `app/_layout.tsx`:

```typescript
// No início do componente
if (typeof window === 'undefined') {
  return null; // Retorna null no servidor
}
```

### Usar Mobile (Recomendado)
Se ainda tiver problemas no web, use o **Expo Go no celular**:
1. Inicie: `npx expo start` (sem --web)
2. Escaneie o QR Code
3. A aplicação abrirá no celular (sem problemas de SSR)

## 🎯 Status

- ✅ `app.json` corrigido (removido output: static)
- ✅ `AuthContext.tsx` corrigido (verificações de cliente)
- ✅ Cache limpo
- ✅ Servidor reiniciado
- ⏳ Aguardando compilação...

---

**Aguarde alguns segundos e acesse**: http://localhost:8081

**O erro de SSR deve estar resolvido!** ✅

