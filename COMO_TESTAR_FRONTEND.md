# 🎨 Como Testar o Frontend

## 🚀 Iniciando o Frontend

### 1. Verificar se o Backend está Rodando
```bash
curl http://localhost:8000/health
```
Deve retornar: `{"status":"healthy"}`

### 2. Iniciar o Frontend
```bash
cd frontend
npx expo start --clear
```

### 3. Opções de Visualização

Após iniciar, você verá um QR Code e opções no terminal:

#### Opção A: Web (Navegador)
- Pressione `w` no terminal
- Abre em: http://localhost:8081

#### Opção B: Android (Emulador/Dispositivo)
- Pressione `a` no terminal
- Ou escaneie o QR Code com o app Expo Go

#### Opção C: iOS (Simulador/Dispositivo)
- Pressione `i` no terminal
- Ou escaneie o QR Code com o app Expo Go

## 📱 Telas Disponíveis

### 🔐 Autenticação
- **Login** (`/login`)
  - Email e senha
  - Botão "Entrar"
  - Link para registro

- **Registro** (`/register`)
  - Nome, email, telefone e senha
  - Botão "Criar conta"
  - Link para login

### 📊 Dashboard (Após Login)
- **Dashboard** (`/dashboard`)
  - Resumo geral
  - Estatísticas rápidas

### 📋 Catálogo
- **Catálogo** (`/catalogo`)
  - Lista de tranças disponíveis
  - Cards com imagens e informações
  - Navegação para detalhes

- **Detalhe da Trança** (`/detalhe/[id]`)
  - Informações completas da trança
  - Preço, duração, descrição
  - Botão para agendar

### 📅 Agendamentos
- **Lista de Agendamentos** (`/agendamentos`)
  - Lista de agendamentos do usuário
  - Status, data, horário
  - Ações (editar, cancelar)

- **Agendar** (`/agendar/[id]`)
  - Formulário de agendamento
  - Seleção de data e horário
  - Informações do cliente

### 👥 Clientes
- **Lista de Clientes** (`/clientes`)
  - Lista de clientes cadastrados
  - Busca e filtros
  - Ações (editar, deletar)

### 💰 Financeiro
- **Resumo Financeiro** (`/financeiro`)
  - Entradas e saídas
  - Gráficos e estatísticas
  - Filtros por período

## 🧪 Fluxo de Teste Recomendado

### 1. Tela de Login
1. Acesse a aplicação
2. Você será redirecionado para `/login`
3. Preencha:
   - Email: `benny4@gmail.com`
   - Senha: `senha123`
4. Clique em "Entrar"

### 2. Dashboard
- Após login, você verá o dashboard
- Navegue pelas abas inferiores

### 3. Catálogo
- Clique na aba "Catálogo"
- Veja as tranças disponíveis
- Clique em uma trança para ver detalhes

### 4. Agendamentos
- Clique na aba "Agendamentos"
- Veja seus agendamentos
- Clique em "Agendar" para criar novo

### 5. Clientes
- Clique na aba "Clientes"
- Veja a lista de clientes
- Adicione novos clientes

### 6. Financeiro
- Clique na aba "Financeiro"
- Veja o resumo financeiro

## 🔧 Configuração da API

O frontend está configurado para usar:
- **URL Base**: `http://192.168.0.6:8000`
- **Arquivo**: `frontend/src/config/api.ts`

Se o backend estiver em outro endereço, edite este arquivo.

## 🐛 Problemas Comuns

### Frontend não carrega
- ✅ Verifique se o backend está rodando
- ✅ Verifique a URL da API em `frontend/src/config/api.ts`
- ✅ Limpe o cache: `npx expo start --clear`

### Erro de conexão com API
- ✅ Verifique se o backend está acessível
- ✅ Teste: `curl http://localhost:8000/health`
- ✅ Verifique o IP na configuração da API

### Tela em branco
- ✅ Verifique o console do navegador (F12)
- ✅ Verifique os logs do Expo
- ✅ Reinicie o servidor Expo

### Token expirado
- ✅ Faça logout e login novamente
- ✅ O token expira em 30 minutos

## 📸 Screenshots Esperados

### Tela de Login
- Campo de email
- Campo de senha
- Botão "Entrar"
- Link "Não tem conta? Registre-se"

### Dashboard
- Cards com informações resumidas
- Navegação por abas na parte inferior

### Catálogo
- Grid de cards com tranças
- Imagem, nome, preço
- Botão para ver detalhes

## 🎯 Checklist de Teste

- [ ] Backend rodando na porta 8000
- [ ] Frontend iniciado com `npx expo start`
- [ ] Tela de login carrega corretamente
- [ ] Login funciona com credenciais válidas
- [ ] Dashboard aparece após login
- [ ] Navegação entre telas funciona
- [ ] Catálogo mostra tranças
- [ ] Agendamentos lista corretamente
- [ ] Clientes lista corretamente
- [ ] Financeiro mostra dados

## 🚀 Comandos Rápidos

```bash
# Iniciar backend
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Iniciar frontend
cd frontend
npx expo start --clear

# Verificar backend
curl http://localhost:8000/health

# Verificar frontend (web)
# Abra: http://localhost:8081
```

## 📱 Acessando no Dispositivo Móvel

1. Instale o app **Expo Go** no seu celular
2. Inicie o frontend: `npx expo start`
3. Escaneie o QR Code com o Expo Go
4. A aplicação abrirá no seu celular

**Importante**: Backend e celular devem estar na mesma rede Wi-Fi!

---

**Dúvidas?** Verifique os logs no terminal do Expo ou do backend! 🚀

