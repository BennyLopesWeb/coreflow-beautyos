# 📚 Documentação Completa - TrançaPro

## 🎯 Visão Geral

Sistema SaaS completo para gestão de salão de tranças com catálogo público, reservas online, controle financeiro e integrações.

---

## 🏗️ Arquitetura Implementada

### Backend (FastAPI + PostgreSQL)

#### Estrutura de Domínios
```
app/
├── domain/
│   ├── auth/              # Autenticação JWT
│   ├── clientes/          # CRM de clientes
│   ├── servicos/          # Cadastro de serviços
│   ├── agendamentos/      # Agendamentos e reservas
│   ├── financeiro/        # Controle financeiro
│   ├── mensagens/         # Mensagens automáticas (WhatsApp simulado)
│   └── catalogo/          # Catálogo público de tranças
├── shared/                # Código compartilhado
│   ├── exceptions.py      # Exceções customizadas
│   └── repository.py      # Base repository pattern
└── main.py                # Aplicação FastAPI
```

#### Padrões Implementados
- **Repository Pattern**: BaseRepository genérico + repositórios específicos
- **Service Layer**: Lógica de negócio separada dos controllers
- **DTOs com Pydantic**: Validação e serialização
- **Migrations Alembic**: Controle de versão do banco
- **Tratamento de Erros**: Exceções customizadas consistentes

---

## 📊 Modelos de Dados

### 1. Autenticação
- **User**: Usuários do sistema (email, senha hasheada, permissões)

### 2. CRM
- **Cliente**: Dados dos clientes (nome, telefone, email, endereço, observações)

### 3. Serviços
- **Servico**: Serviços oferecidos (nome, descrição, duração, valor total, valor sinal, ativo)

### 4. Agendamentos
- **Agendamento**: Agendamentos/reservas
  - Status: agendado, confirmado, em_atendimento, concluido, cancelado, falta
  - Status Pagamento: pendente, pago_parcial, pago, cancelado
  - Integração Pix (QR Code, transaction_id)
  - Integração Google Calendar (event_id)
- **FilaVirtual**: Fila por serviço/dia com posição

### 5. Financeiro
- **MovimentoFinanceiro**: Entradas e saídas
  - Tipo: entrada (automática de agendamentos) ou saída (manual)
  - Vinculado a agendamento (quando aplicável)
  - Dashboard com métricas (total entradas, saídas, lucro)

### 6. Catálogo Público
- **BraidStyle**: Estilos de trança no catálogo
  - Mesmos campos de Servico + ordem_exibicao, ativo
- **BraidStyleImage**: Imagens dos estilos
  - url_imagem, descricao, ordem, is_principal

---

## 🔌 Endpoints da API

### Públicos (sem autenticação)
- `GET /api/public/catalogo` - Lista estilos disponíveis
- `GET /api/public/catalogo/{id}` - Detalhes de um estilo
- `POST /api/public/catalogo/consultar-horarios` - Horários disponíveis
- `POST /api/public/reservas` - Criar reserva
- `GET /api/public/reservas/{id}/status` - Status da reserva

### Autenticados
- `POST /api/auth/register` - Registrar usuário
- `POST /api/auth/login` - Login (retorna JWT)
- `GET /api/auth/me` - Dados do usuário atual

### CRM
- `POST /api/clientes` - Criar cliente
- `GET /api/clientes` - Listar clientes
- `GET /api/clientes/{id}` - Buscar cliente
- `PUT /api/clientes/{id}` - Atualizar cliente
- `DELETE /api/clientes/{id}` - Remover cliente

### Serviços
- `POST /api/servicos` - Criar serviço
- `GET /api/servicos` - Listar serviços
- `GET /api/servicos/{id}` - Buscar serviço
- `PUT /api/servicos/{id}` - Atualizar serviço
- `DELETE /api/servicos/{id}` - Remover serviço

### Agendamentos
- `POST /api/agendamentos` - Criar agendamento
- `GET /api/agendamentos` - Listar agendamentos
- `GET /api/agendamentos/{id}` - Buscar agendamento
- `PUT /api/agendamentos/{id}` - Atualizar agendamento
- `POST /api/agendamentos/{id}/confirmar-sinal` - Confirmar pagamento sinal
- `POST /api/agendamentos/{id}/confirmar-pagamento` - Confirmar pagamento final
- `POST /api/agendamentos/{id}/cancelar` - Cancelar agendamento
- `GET /api/agendamentos/fila/{servico_id}` - Fila virtual

### Financeiro
- `POST /api/financeiro/saida` - Registrar saída manual
- `GET /api/financeiro/movimentos` - Listar movimentos
- `GET /api/financeiro/fluxo-caixa/{mes}/{ano}` - Fluxo de caixa mensal
- `GET /api/financeiro/dashboard` - Dashboard com métricas

### Admin - Catálogo
- `POST /api/admin/catalogo` - Criar estilo
- `GET /api/admin/catalogo` - Listar estilos
- `PUT /api/admin/catalogo/{id}` - Atualizar estilo
- `DELETE /api/admin/catalogo/{id}` - Remover estilo
- `POST /api/admin/catalogo/{id}/imagens` - Adicionar imagem
- `DELETE /api/admin/catalogo/imagens/{id}` - Remover imagem

---

## 🎨 Frontend (React + TypeScript)

### Estrutura Implementada
```
src/
├── components/
│   └── reutilizaveis/
│       ├── ButtonPrimary.tsx
│       ├── CardTranca.tsx
│       ├── CalendarPicker.tsx
│       ├── TimeSlot.tsx
│       ├── ModalConfirm.tsx
│       └── Loader.tsx
├── pages/
│   ├── Catalogo.tsx
│   ├── DetalheTranca.tsx
│   ├── SelecionarData.tsx
│   ├── SelecionarHorario.tsx
│   ├── DadosCliente.tsx
│   ├── PagamentoPix.tsx
│   └── ConfirmacaoReserva.tsx
├── types/
│   └── index.ts
└── utils/
    └── api.ts
```

### Fluxo de Reserva Implementado
1. **Catalogo** → Lista CardTranca → Clique leva para DetalheTranca
2. **DetalheTranca** → Carrossel de imagens + CTA fixo "Reservar horário"
3. **SelecionarData** → Calendário com datas disponíveis
4. **SelecionarHorario** → Grid de TimeSlot com horários livres
5. **DadosCliente** → Formulário validado (nome, telefone, email, observações)
6. **PagamentoPix** → QR Code + código Pix + verificação automática de status
7. **ConfirmacaoReserva** → Resumo + feedback visual de sucesso

### Componentes Reutilizáveis
- **ButtonPrimary**: Botão primário com variantes, loading, disabled
- **CardTranca**: Card de estilo de trança com imagem, nome, preço
- **CalendarPicker**: Calendário customizado com datas disponíveis/indisponíveis
- **TimeSlot**: Slot de horário clicável com estados (disponível, selecionado, desabilitado)
- **ModalConfirm**: Modal de confirmação reutilizável
- **Loader**: Spinner de loading com mensagem opcional

### UX Implementado
- ✅ Mobile-first design
- ✅ CTA sempre visível no mobile (fixo no bottom)
- ✅ Estados de loading, erro e sucesso
- ✅ Feedback visual em todas as ações
- ✅ Validação de formulários
- ✅ Navegação fluida sem telas mortas
- ✅ Mensagens claras ao usuário

---

## 🔄 Integrações

### Google Calendar
- Criação automática de evento após confirmação do pagamento do sinal
- Atualização de evento quando agendamento é alterado
- Cancelamento de evento quando agendamento é cancelado

### Pix (Simulado)
- Geração de QR Code e código Pix
- Verificação de status (simulado - em produção integrar webhook)

### WhatsApp (Simulado)
- Mensagens automáticas:
  - Confirmação de agendamento
  - Lembrete (24h antes)
  - Cancelamento
  - Confirmação de pagamento

---

## 📋 Funcionalidades Principais

### 1. CRM de Clientes
- CRUD completo
- Busca por nome
- Validação de telefone único

### 2. Cadastro de Serviços
- Duração em minutos
- Valor total e valor do sinal
- Validação: sinal não pode ser maior que total
- Ativo/Inativo

### 3. Agendamentos
- Criação com validações
- Pagamento em duas etapas (sinal + final)
- Integração com fila virtual
- Status e controle de pagamento
- Cancelamento com limpeza de recursos

### 4. Fila Virtual
- Organização por serviço/dia
- Posição automática na fila
- Consulta de fila por serviço/data

### 5. Controle Financeiro
- Entradas automáticas (sinal + pagamento final)
- Saídas manuais
- Fluxo de caixa mensal
- Dashboard com métricas:
  - Total de entradas
  - Total de saídas
  - Lucro

### 6. Catálogo Público
- Listagem de estilos com imagens
- Detalhes completos
- Consulta de horários disponíveis (considera conflitos)
- Reserva integrada ao sistema de agendamentos

### 7. Reservas Online
- Fluxo completo sem autenticação
- Seleção de data e horário
- Validação de disponibilidade
- Geração de Pix
- Confirmação automática após pagamento

---

## 🗄️ Migrations

### 001_initial.py
- users
- clientes
- servicos
- agendamentos
- fila_virtual
- movimentos_financeiros

### 002_add_catalogo.py
- braid_styles
- braid_style_images

---

## 🛠️ Tecnologias Utilizadas

### Backend
- FastAPI 0.104.1
- SQLAlchemy 2.0.23
- PostgreSQL (psycopg2-binary)
- Alembic 1.12.1
- Pydantic 2.5.0
- JWT (python-jose)
- Google Calendar API
- Bcrypt (passlib)

### Frontend
- React 18.2.0
- TypeScript 5.2.2
- React Router DOM 6.20.0
- Axios 1.6.2
- date-fns 2.30.0
- react-image-gallery
- react-toastify
- PWA (Workbox)

---

## 📝 Regras de Negócio Implementadas

1. **Validação de Serviços**
   - Valor do sinal não pode ser maior que valor total
   - Duração deve ser maior que zero

2. **Agendamentos**
   - Não permite agendamentos no passado
   - Verifica conflitos de horário
   - Reserva só confirmada após pagamento do sinal

3. **Horários Disponíveis**
   - Calcula slots de 30 minutos
   - Considera duração do serviço
   - Verifica conflitos com agendamentos existentes
   - Não permite horários no passado

4. **Financeiro**
   - Entradas automáticas ao confirmar pagamentos
   - Não permite deletar movimentos automáticos de agendamentos
   - Dashboard calcula métricas do período

5. **Catálogo**
   - Apenas estilos ativos aparecem no catálogo público
   - Ordenação por ordem_exibicao

---

## 🚀 Configuração

### Variáveis de Ambiente (.env)
```
DATABASE_URL=postgresql://user:pass@localhost:5432/trancapro
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
GOOGLE_CALENDAR_CREDENTIALS_FILE=credentials.json
GOOGLE_CALENDAR_TOKEN_FILE=token.json
WHATSAPP_ENABLED=false
PIX_MERCHANT_ID=your-merchant-id
PIX_API_KEY=your-api-key
```

### Comandos
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm start
```

---

## 📌 Observações Importantes

### Simulações
- **Pix**: Implementado como simulação. Para produção, integrar com API real (Asaas, Mercado Pago, etc.)
- **WhatsApp**: Simulação com logs. Para produção, integrar com API real (Twilio, Evolution API, etc.)

### Melhorias Futuras
- Upload de imagens (atualmente apenas URLs)
- Webhook para confirmação automática de Pix
- Notificações push
- Sistema de avaliações
- Filtros e busca avançada no catálogo
- Dashboard administrativo completo
- Relatórios financeiros avançados

---

## ✅ Status da Implementação

### Backend: ✅ Completo
- Todos os domínios implementados
- Padrões Repository + Service
- Migrations configuradas
- Endpoints REST completos
- Integrações (Google Calendar, Pix, WhatsApp simulados)

### Frontend: ✅ Parcialmente Completo
- Componentes reutilizáveis criados
- Fluxo de reserva implementado
- TypeScript configurado
- UX mobile-first implementado
- Faltando: FilaVirtual/StatusFila (iniciado mas não finalizado)

---

## 🎯 Próximos Passos Sugeridos

1. Finalizar implementação de FilaVirtual/StatusFila
2. Implementar upload de imagens
3. Integrar Pix real com webhook
4. Implementar sistema de notificações
5. Criar dashboard administrativo completo
6. Adicionar testes automatizados
7. Implementar cache para performance
8. Adicionar logging estruturado
9. Configurar CI/CD
10. Documentação da API (OpenAPI/Swagger já disponível)

---

**Data da Documentação**: 2024
**Versão do Sistema**: 1.0.0

