# Padrões Backend CoreFlow

## Estrutura de módulo (obrigatória)

```
modules/{name}/
  domain/           # entities, events, policies
  application/      # use cases, ports, handlers
  infrastructure/   # adapters (ORM, HTTP, messaging)
  api/              # FastAPI routers
  tests/
```

## Regras

1. **Domain** não importa FastAPI, SQLAlchemy, HTTP  
2. **Application** depende de **ports** (Protocol), não de adapters  
3. **Infrastructure** implementa ports  
4. Comunicação entre módulos preferencialmente via **eventos**  
5. Todo plugin declara manifest YAML  

## Naming

- Eventos: `coreflow.{domain}.{action}` ou `{domain}.{action}` (transição)  
- Ports: `{Name}Port` ou `{Name}RepositoryPort`  
- Adapters: `{Tech}{Name}Adapter`  

## Testes

```bash
make test
```

Fixtures em `tests/conftest.py`. Todo módulo novo deve ter testes em `tests/test_modules/`.
