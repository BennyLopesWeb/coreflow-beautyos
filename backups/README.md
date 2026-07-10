# Backups TrançaPro

Pasta de snapshots do projeto para consulta e recuperação antes de mudanças.

## Backup mais recente

| Arquivo | Conteúdo | Tamanho aprox. |
|---------|----------|----------------|
| `trancapro-backup-2026-07-08_2331.tar.gz` | Projeto completo (código, docs, imagens, banco) | ~6 MB |
| `trancapro-db-2026-07-08_2331.sqlite` | Cópia isolada do banco SQLite | ~228 KB |

**Data do snapshot:** 08/07/2026 23:31

### O que está incluído no `.tar.gz`

- Backend (`backend/app/`, testes, scripts)
- Frontend (`frontend/app/`, `frontend/src/`, configs)
- Documentação (`DOCUMENTACAO.md` e demais `.md` na raiz)
- Banco de dados (`backend/trancapro.db`)
- Imagens estáticas (`backend/static/`)
- Comprovantes enviados (`backend/static/comprovantes/`)

### O que foi excluído (pode ser regenerado)

- `node_modules/` (frontend)
- `frontend/dist/` (build web)
- `__pycache__/`, `.pytest_cache/`
- `frontend/.expo/`
- Arquivos `.env` (nunca versionados — recrie localmente)

---

## Restaurar projeto completo

```bash
# 1. Mover ou renomear a pasta atual (opcional)
mv "Atendente Salao trancista" "Atendente Salao trancista-old"

# 2. Extrair backup
cd "/Users/zeuser/Documents/ProjetosPessoas"
tar -xzf "Atendente Salao trancista/backups/trancapro-backup-2026-07-08_2331.tar.gz"

# 3. Reinstalar dependências
cd "Atendente Salao trancista/frontend" && npm install
cd "../backend" && pip install -r requirements.txt  # se existir

# 4. Subir servidores
uvicorn app.main:app --host 0.0.0.0 --port 8000   # backend
cd frontend && npm run build:web && npx serve -s dist -l 8081
```

## Restaurar apenas o banco de dados

```bash
cp backups/trancapro-db-2026-07-08_2331.sqlite backend/trancapro.db
```

Reinicie o backend após substituir o banco.

---

## Criar novo backup manualmente

```bash
STAMP=$(date +"%Y-%m-%d_%H%M")
cp backend/trancapro.db "backups/trancapro-db-${STAMP}.sqlite"
cd "/Users/zeuser/Documents/ProjetosPessoas"
tar -czf "Atendente Salao trancista/backups/trancapro-backup-${STAMP}.tar.gz" \
  --exclude='**/node_modules' \
  --exclude='**/__pycache__' \
  --exclude='**/.pytest_cache' \
  --exclude='frontend/dist' \
  --exclude='frontend/.expo' \
  --exclude='backups/*.tar.gz' \
  "Atendente Salao trancista"
```

---

## Estado funcional no momento do backup

- Reservas com fluxo: pagamento → aprovação admin
- Fila de espera e fila operacional
- Painel admin com badges e pendências
- Catálogo por categoria/modelo com preços individuais
- Documentação em `DOCUMENTACAO.md`
