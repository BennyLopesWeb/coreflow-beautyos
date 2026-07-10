# 📦 Instalação e Verificação do npm

## ✅ Status Atual

### Verificações Realizadas:
- ✅ **Node.js**: v22.13.1 instalado
- ✅ **npm**: v10.9.2 instalado
- ✅ **node_modules**: Existe
- ✅ **Dependências**: Instaladas

## 📋 Informações do Sistema

### Node.js e npm
```
Node.js: v22.13.1
npm: v10.9.2
Localização: /usr/local/bin/
```

### Dependências do Frontend
- ✅ Todas as dependências instaladas
- ✅ Expo CLI disponível
- ✅ node_modules completo

## 🔧 Se Precisar Reinstalar

### Opção 1: Reinstalar Dependências
```bash
cd frontend
npm install
```

### Opção 2: Limpar e Reinstalar (se houver problemas)
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Opção 3: Instalar npm Globalmente (se não estiver instalado)

#### macOS (com Homebrew):
```bash
brew install node
```

#### macOS (sem Homebrew):
```bash
# Baixar do site oficial
# https://nodejs.org/
```

#### Linux:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nodejs npm

# Ou usando nvm (recomendado)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install --lts
nvm use --lts
```

#### Windows:
```bash
# Baixar instalador do site oficial
# https://nodejs.org/
# Ou usar Chocolatey
choco install nodejs
```

## ✅ Verificação Rápida

Execute estes comandos para verificar:

```bash
# Verificar Node.js
node --version

# Verificar npm
npm --version

# Verificar se está no PATH
which node
which npm
```

## 📦 Dependências do Projeto

### Principais Dependências Instaladas:
- ✅ expo ~50.0.0
- ✅ react 18.2.0
- ✅ react-native 0.73.0
- ✅ expo-router ~3.4.0
- ✅ axios ^1.6.2
- ✅ @react-native-async-storage/async-storage
- ✅ @expo/vector-icons
- ✅ E mais 1200+ packages

## 🚀 Próximos Passos

Agora que tudo está instalado, você pode:

1. **Iniciar o frontend:**
   ```bash
   cd frontend
   npm start
   ```

2. **Ou iniciar diretamente no web:**
   ```bash
   cd frontend
   npm run web
   ```

## ⚠️ Troubleshooting

### Problema: "npm: command not found"

**Solução:**
1. Verifique se Node.js está instalado: `node --version`
2. Se Node.js estiver instalado mas npm não:
   ```bash
   # Reinstalar Node.js (npm vem junto)
   brew reinstall node  # macOS
   # ou baixar do site oficial
   ```

### Problema: "Permission denied"

**Solução:**
```bash
# Não use sudo com npm (pode causar problemas)
# Em vez disso, configure npm para usar um diretório local
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.zshrc
source ~/.zshrc
```

### Problema: Versão antiga do npm

**Solução:**
```bash
# Atualizar npm
npm install -g npm@latest

# Verificar versão
npm --version
```

## 📊 Status Final

| Componente | Status | Versão |
|------------|--------|--------|
| **Node.js** | ✅ Instalado | v22.13.1 |
| **npm** | ✅ Instalado | v10.9.2 |
| **Dependências** | ✅ Instaladas | 1217 packages |
| **Expo CLI** | ✅ Disponível | - |

---

**Status**: ✅ Tudo instalado e pronto!

**Comando para iniciar:**
```bash
cd frontend && npm start
```

