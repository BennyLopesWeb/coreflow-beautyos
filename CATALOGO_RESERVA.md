# 📋 Incremento - Catálogo e Reserva

## ✅ Funcionalidades Implementadas

### 1. Catálogo Público de Tranças

- **Listagem de estilos** com fotos, preço total, valor do sinal e duração
- **Página pública** (sem autenticação) em `/catalogo`
- **Visualização detalhada** de cada estilo

### 2. Fluxo de Reserva

1. Cliente escolhe estilo no catálogo
2. Consulta horários disponíveis (considerando duração e conflitos)
3. Cliente seleciona horário
4. Sistema gera pagamento Pix do sinal
5. Reserva só é confirmada após pagamento

### 3. Modelagem

#### Entidades Criadas:

- **`braid_styles`**: Estilos de trança do catálogo
  - nome, descricao, duracao_minutos
  - valor_total, valor_sinal
  - ativo, ordem_exibicao

- **`braid_style_images`**: Imagens dos estilos
  - url_imagem, descricao
  - ordem, is_principal
  - Relacionamento com braid_styles

### 4. Regras Implementadas

✅ **Sem pagamento → reserva cancelada**: Reservas ficam pendentes até confirmação do pagamento

✅ **Horários reais**: Sistema calcula horários disponíveis considerando:
- Duração do serviço
- Conflitos com agendamentos existentes
- Slots de 30 minutos
- Não permite agendamentos no passado

✅ **Google Calendar**: Evento criado automaticamente após confirmação do pagamento do sinal

✅ **Entrada automática no fluxo de caixa**: Registrada quando o pagamento do sinal é confirmado

## 🔌 Endpoints da API

### Públicos (sem autenticação)

- `GET /api/public/catalogo` - Lista estilos disponíveis
- `GET /api/public/catalogo/{style_id}` - Detalhes de um estilo
- `POST /api/public/catalogo/consultar-horarios` - Consulta horários disponíveis
- `POST /api/public/reservas` - Cria reserva
- `GET /api/public/reservas/{reserva_id}/status` - Consulta status da reserva

### Administrativos (com autenticação)

- `POST /api/admin/catalogo` - Cria estilo
- `GET /api/admin/catalogo` - Lista todos os estilos
- `GET /api/admin/catalogo/{style_id}` - Obtém estilo
- `PUT /api/admin/catalogo/{style_id}` - Atualiza estilo
- `DELETE /api/admin/catalogo/{style_id}` - Remove estilo
- `POST /api/admin/catalogo/{style_id}/imagens` - Adiciona imagem
- `DELETE /api/admin/catalogo/imagens/{image_id}` - Remove imagem

## 🎨 Frontend

### Páginas Criadas

1. **`/catalogo`** - Catálogo público
   - Grid responsivo de estilos
   - Cards com imagem, nome, preço e duração
   - Botão "Reservar Agora"

2. **`/reservar/:estiloId`** - Página de reserva
   - Preview do estilo selecionado
   - Formulário de dados do cliente
   - Seletor de data
   - Grid de horários disponíveis
   - Confirmação com QR Code Pix

### Fluxo do Usuário

```
Catálogo → Selecionar Estilo → Preencher Dados → 
Selecionar Data/Horário → Confirmar Reserva → 
Visualizar QR Code Pix → Realizar Pagamento → 
Reserva Confirmada (após confirmação do pagamento)
```

## 🔄 Integração com Módulos Existentes

### Agendamentos
- Reservas são criadas como agendamentos
- Integração completa com fila virtual
- Status de pagamento controlado

### Clientes
- Cliente é criado automaticamente se não existir
- Dados do formulário de reserva são salvos

### Serviços
- Serviço é criado automaticamente a partir do estilo
- Sincronização de valores e duração

### Financeiro
- Entrada automática registrada ao confirmar pagamento do sinal
- Entrada final registrada ao confirmar pagamento completo

### Google Calendar
- Evento criado após confirmação do pagamento do sinal
- Inclui dados do cliente e serviço

## 📊 Lógica de Horários Disponíveis

O sistema calcula horários disponíveis considerando:

1. **Slots de 30 minutos**: Horários são divididos em slots de 30 minutos
2. **Duração do serviço**: Verifica se há espaço suficiente para a duração completa
3. **Conflitos**: Verifica agendamentos existentes no período
4. **Passado**: Não permite agendamentos em datas/horários passados
5. **Período**: Horários são calculados para o dia selecionado

## 🚀 Como Usar

### 1. Criar Estilos no Catálogo (Admin)

```bash
POST /api/admin/catalogo
{
  "nome": "Trança Box Braids",
  "descricao": "Tranças box braids clássicas",
  "duracao_minutos": 180,
  "valor_total": 150.00,
  "valor_sinal": 50.00,
  "ativo": true,
  "ordem_exibicao": 1,
  "imagens": [
    {
      "url_imagem": "https://exemplo.com/imagem.jpg",
      "is_principal": true
    }
  ]
}
```

### 2. Cliente Acessa Catálogo

Acessa `/catalogo` e visualiza estilos disponíveis

### 3. Cliente Faz Reserva

1. Clica em "Reservar Agora"
2. Preenche dados pessoais
3. Seleciona data e horário
4. Confirma reserva
5. Recebe QR Code Pix

### 4. Confirmar Pagamento (Admin)

```bash
POST /api/agendamentos/{agendamento_id}/confirmar-sinal
```

Isso irá:
- Confirmar pagamento do sinal
- Criar evento no Google Calendar
- Registrar entrada no fluxo de caixa
- Enviar mensagem de confirmação

## 📝 Migration

Execute a migration para criar as tabelas:

```bash
alembic upgrade head
```

A migration `002_add_catalogo.py` cria:
- `braid_styles`
- `braid_style_images`

## 🎯 Próximos Passos (Opcional)

- [ ] Upload de imagens (atualmente apenas URLs)
- [ ] Webhook para confirmação automática de pagamento Pix
- [ ] Notificações push para confirmação de reserva
- [ ] Sistema de avaliações de estilos
- [ ] Filtros e busca no catálogo
- [ ] Galeria de fotos expandida

## 📌 Observações

- **Imagens**: Atualmente aceita apenas URLs. Para upload de arquivos, implementar storage (S3, Cloudinary, etc.)
- **Pix**: Integração simulada. Para produção, integrar com gateway real (Asaas, Mercado Pago, etc.)
- **Cancelamento**: Reservas sem pagamento podem ser canceladas automaticamente após X horas
- **Horários**: Configurável - atualmente slots de 30 minutos

