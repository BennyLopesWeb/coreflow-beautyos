# PR Checklist — CoreFlow Platform

Todo Pull Request **deve** responder **Sim** a todas as perguntas abaixo.  
Se alguma resposta for **Não** e a mudança for significativa → **interromper merge** até RFC/ADR/docs/testes.

---

## Compatibilidade

- [ ] Esta alteração **não remove** funcionalidades existentes?
- [ ] APIs legadas continuam respondendo (ou têm sunset documentado)?
- [ ] Contratos `/v1/*` mantêm compatibilidade retroativa?
- [ ] Migrations são reversíveis ou têm plano de rollback?

## Governança

- [ ] Existe **RFC** aprovado (se mudança arquitetural)?
- [ ] Existe **ADR** aprovado (se decisão estrutural)?
- [ ] Fase implementada é **única** (não múltiplas fases juntas)?

## Documentação

- [ ] README / docs atualizados?
- [ ] Event Catalog atualizado (se novo evento)?
- [ ] Sprint doc ou changelog atualizado?

## Qualidade

- [ ] Testes adicionados ou atualizados?
- [ ] `pytest` passa localmente?
- [ ] Nenhuma regra de negócio duplicada no frontend?

## Arquitetura

- [ ] Código usa vocabulário **metamodelo** (Worker, Resource, Booking)?
- [ ] Lógica de domínio **não** em routers?
- [ ] Dependências apontam **para dentro** (application → domain, não o contrário)?
- [ ] Integrações externas atrás de **ports/adapters**?

## Multi-tenant & Plugins

- [ ] `company_id` / TenantContext respeitado?
- [ ] Impacto em outros plugins avaliado?
- [ ] Nenhuma referência hardcoded a beauty-only no core?

## Observabilidade & Segurança

- [ ] Logs estruturados em paths críticos?
- [ ] Endpoints admin protegidos (JWT + RBAC)?
- [ ] Secrets não commitados?

## Rollback

- [ ] Plano de rollback descrito no PR ou RFC?
- [ ] Feature flags / settings para desligar comportamento novo?

---

**Referências:** `docs/rfc/`, `docs/adr/`, `docs/ArchitectureEvolutionPlan.md`
