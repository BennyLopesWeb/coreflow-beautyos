# 📱 Telas do Frontend - TrançaPro

## ✅ Status Atual

- ✅ **Backend**: Rodando em http://localhost:8000
- ✅ **Frontend**: Rodando em http://localhost:8081
- ✅ **Pronto para testar!**

## 🚀 Como Acessar

### Opção 1: Web (Navegador)
Abra no navegador: **http://localhost:8081**

### Opção 2: Mobile (Expo Go)
1. Instale o app **Expo Go** no celular
2. Escaneie o QR Code que aparece no terminal
3. A app abrirá no seu celular

### Opção 3: Terminal
No terminal onde o Expo está rodando, pressione:
- `w` - Abrir no navegador
- `a` - Abrir no Android
- `i` - Abrir no iOS

---

## 📋 Telas Disponíveis

### 🔐 1. Tela de Login (`/login`)

**Acesso**: Primeira tela ao abrir o app

**Elementos**:
- Logo/Título "TrançaPro"
- Campo de **E-mail**
- Campo de **Senha**
- Botão "Entrar"
- Link "Não tem conta? Registre-se"

**Credenciais para Teste**:
- Email: `benny4@gmail.com`
- Senha: `senha123`

**Fluxo**: Após login bem-sucedido → Redireciona para Dashboard

---

### 📝 2. Tela de Registro (`/register`)

**Acesso**: Link na tela de login

**Elementos**:
- Campo de **Nome**
- Campo de **E-mail**
- Campo de **Telefone**
- Campo de **Senha**
- Botão "Criar conta"
- Link "Já tem conta? Faça login"

**Fluxo**: Após registro → Redireciona para Login

---

### 📊 3. Dashboard (`/dashboard`)

**Acesso**: Após login bem-sucedido

**Elementos**:
- **Bem-vindo** com nome do usuário
- **Resumo do Mês**:
  - Total de agendamentos
  - Receita do mês
  - Próximos agendamentos (lista)
- **Navegação por abas** na parte inferior:
  - Dashboard (ativo)
  - Catálogo
  - Agendamentos
  - Clientes
  - Financeiro

**Funcionalidades**:
- Carrega dados do mês atual
- Mostra últimos 5 agendamentos
- Exibe resumo financeiro

---

### 📚 4. Catálogo (`/catalogo`)

**Acesso**: Aba "Catálogo" na navegação inferior

**Elementos**:
- **Título**: "Catálogo de Tranças"
- **Lista de tranças** em cards:
  - Imagem da trança
  - Nome da trança
  - Preço
  - Duração
  - Botão "Ver detalhes"
- **Pull to refresh** (puxar para atualizar)

**Funcionalidades**:
- Lista todas as tranças ativas
- Navegação para detalhes ao tocar no card
- Atualização manual (pull to refresh)

---

### 🔍 5. Detalhe da Trança (`/detalhe/[id]`)

**Acesso**: Tocar em uma trança no catálogo

**Elementos**:
- **Imagem** da trança (grande)
- **Nome** da trança
- **Descrição**
- **Preço**: R$ XX,XX
- **Duração**: X horas
- **Valor do sinal**: R$ XX,XX
- Botão **"Agendar"**

**Funcionalidades**:
- Mostra informações completas
- Botão para agendar esta trança

---

### 📅 6. Agendar (`/agendar/[id]`)

**Acesso**: Botão "Agendar" na tela de detalhe da trança

**Elementos**:
- **Informações da trança** (resumo)
- **Seleção de data** (calendário)
- **Seleção de horário** (slots disponíveis)
- **Dados do cliente**:
  - Nome
  - Telefone
  - Email
- Botão **"Confirmar Agendamento"**

**Funcionalidades**:
- Mostra apenas horários disponíveis
- Validação de campos obrigatórios
- Cria agendamento após confirmação

---

### 📋 7. Lista de Agendamentos (`/agendamentos`)

**Acesso**: Aba "Agendamentos" na navegação inferior

**Elementos**:
- **Título**: "Meus Agendamentos"
- **Lista de agendamentos**:
  - Data e horário
  - Nome do cliente
  - Nome da trança
  - Status (Confirmado, Pendente, Cancelado)
  - Ações (editar, cancelar)
- **Pull to refresh**

**Funcionalidades**:
- Lista todos os agendamentos
- Filtros por status (opcional)
- Ações de edição e cancelamento

---

### 👥 8. Lista de Clientes (`/clientes`)

**Acesso**: Aba "Clientes" na navegação inferior

**Elementos**:
- **Título**: "Clientes"
- **Botão "Adicionar Cliente"** (flutuante)
- **Lista de clientes**:
  - Nome
  - Telefone
  - Email
  - Ações (editar, deletar)
- **Busca** (opcional)

**Funcionalidades**:
- Lista todos os clientes
- Adicionar novo cliente
- Editar cliente existente
- Deletar cliente (soft delete)

---

### 💰 9. Financeiro (`/financeiro`)

**Acesso**: Aba "Financeiro" na navegação inferior

**Elementos**:
- **Título**: "Resumo Financeiro"
- **Período** (filtro):
  - Mês atual
  - Mês anterior
  - Personalizado
- **Cards de resumo**:
  - Total de entradas
  - Total de saídas
  - Saldo
- **Gráfico** (opcional):
  - Entradas vs Saídas
- **Lista de transações**:
  - Data
  - Descrição
  - Valor
  - Tipo (Entrada/Saída)

**Funcionalidades**:
- Filtro por período
- Cálculo automático de saldo
- Visualização de transações

---

## 🎨 Design e UX

### Cores Principais
- **Primária**: Azul/Verde (definir no tema)
- **Secundária**: Cinza claro
- **Texto**: Preto/Cinza escuro
- **Erro**: Vermelho
- **Sucesso**: Verde

### Componentes Reutilizáveis
- ✅ `ButtonPrimary` - Botão principal
- ✅ `Loader` - Indicador de carregamento
- ✅ `CardTranca` - Card de trança
- ✅ `CalendarPicker` - Seletor de data
- ✅ `TimeSlot` - Slot de horário
- ✅ `ModalConfirm` - Modal de confirmação

### Navegação
- **Stack Navigation**: Para telas de autenticação
- **Tab Navigation**: Para telas principais (Dashboard, Catálogo, etc.)
- **Deep Linking**: Suporte a rotas diretas

---

## 🧪 Fluxo de Teste Completo

### 1. Primeiro Acesso
1. Abra o app → Vai para `/login`
2. Veja a tela de login
3. Clique em "Não tem conta? Registre-se"
4. Veja a tela de registro
5. Volte para login

### 2. Login
1. Preencha email: `benny4@gmail.com`
2. Preencha senha: `senha123`
3. Clique em "Entrar"
4. Aguarde carregamento
5. → Redireciona para Dashboard

### 3. Explorar Dashboard
1. Veja o resumo do mês
2. Veja os próximos agendamentos
3. Navegue pelas abas inferiores

### 4. Explorar Catálogo
1. Clique na aba "Catálogo"
2. Veja a lista de tranças
3. Clique em uma trança
4. Veja os detalhes
5. Clique em "Agendar"

### 5. Criar Agendamento
1. Selecione uma data
2. Selecione um horário
3. Preencha dados do cliente
4. Confirme o agendamento
5. → Volta para lista de agendamentos

### 6. Ver Clientes
1. Clique na aba "Clientes"
2. Veja a lista de clientes
3. Adicione um novo cliente
4. Edite um cliente existente

### 7. Ver Financeiro
1. Clique na aba "Financeiro"
2. Veja o resumo financeiro
3. Filtre por período
4. Veja as transações

---

## 🔧 Configurações Importantes

### URL da API
Arquivo: `frontend/src/config/api.ts`
```typescript
export const API_BASE_URL = 'http://192.168.0.6:8000';
```

**⚠️ Importante**: Se o backend estiver em outro IP, atualize este valor!

### Autenticação
- Tokens são salvos automaticamente no AsyncStorage
- Refresh automático quando o token expira
- Logout limpa todos os dados

---

## 🐛 Problemas Comuns

### Tela em branco
- ✅ Verifique se o backend está rodando
- ✅ Verifique a URL da API
- ✅ Limpe o cache: `npx expo start --clear`

### Erro de conexão
- ✅ Backend e frontend na mesma rede
- ✅ IP correto na configuração da API
- ✅ Backend acessível: `curl http://localhost:8000/health`

### Token expirado
- ✅ Faça logout e login novamente
- ✅ Token expira em 30 minutos

### Dados não carregam
- ✅ Verifique os logs do console
- ✅ Verifique se há dados no backend
- ✅ Teste a API diretamente: `curl http://localhost:8000/trancas`

---

## 📸 Screenshots Esperados

### Login
```
┌─────────────────────┐
│    TrançaPro        │
│                     │
│  Faça login para    │
│  continuar          │
│                     │
│  [E-mail        ]   │
│  [Senha         ]   │
│                     │
│  [   Entrar    ]    │
│                     │
│  Não tem conta?     │
│  Registre-se        │
└─────────────────────┘
```

### Dashboard
```
┌─────────────────────┐
│  Bem-vindo, Nome!   │
│                     │
│  Resumo do Mês      │
│  ┌───────────────┐ │
│  │ Agendamentos  │ │
│  │     5         │ │
│  └───────────────┘ │
│  ┌───────────────┐ │
│  │ Receita       │ │
│  │ R$ 1.500,00   │ │
│  └───────────────┘ │
│                     │
│  Próximos           │
│  ─────────────────  │
│  • Cliente 1        │
│  • Cliente 2        │
│                     │
│ [Dashboard][Catálogo│
│ [Agend][Clientes]   │
└─────────────────────┘
```

---

## ✅ Checklist de Teste

- [ ] Tela de login carrega
- [ ] Login funciona
- [ ] Dashboard aparece após login
- [ ] Navegação entre abas funciona
- [ ] Catálogo lista tranças
- [ ] Detalhe da trança mostra informações
- [ ] Agendamento pode ser criado
- [ ] Lista de agendamentos funciona
- [ ] Clientes lista corretamente
- [ ] Financeiro mostra dados

---

**Pronto para testar!** 🚀

Acesse: **http://localhost:8081** no navegador ou escaneie o QR Code no celular!

