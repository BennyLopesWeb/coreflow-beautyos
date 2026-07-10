# Plugin Beauty — BeautyOS

**plugin_id:** `beauty`  
**Produto:** BeautyOS  
**Manifest:** `backend/plugins/beauty/manifest.yaml`

## Segmentos

Trancista, barbearia, salão, manicure, lash, estética, maquiagem, tatuagem.

## Terminologia (exemplo trancista)

| Metamodelo | Rótulo UI |
|------------|-----------|
| catalog | Categoria |
| offering | Modelo |
| booking | Reserva |
| worker | Profissional |
| resource | Cadeira |

## Features

- Pagamento de sinal (deposit_payment)  
- Fila de espera (waitlist)  
- Fila operacional (operational_queue)  
- Galeria de modelos (service_gallery)  
- Fluxo de aprovação admin (approval_workflow)  
- IA Vision — roadmap (ai_vision)  

## API de configuração

```
GET /v1/plugins/config/by-company/{slug}
```

Retorna terminologia e features para o frontend renderizar dinamicamente.

## Código legado mapeado

Ver ADR-001 e `metamodel_mappings` no manifest.
