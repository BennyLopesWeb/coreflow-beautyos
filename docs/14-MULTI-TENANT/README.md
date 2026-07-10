# 14 — Multi Tenant

```
Tenant → Company → Branch → Department → Worker → Role → Permissions
```

| Nível | Status |
|-------|--------|
| Company + RBAC | ✅ |
| Branch / Department | 🔜 |
| White Label | 🔜 doc 20 |

Código: `Company`, `UserCompany`, `TenantContext`, JWT `company_id`
