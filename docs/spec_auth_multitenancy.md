# Spec: Autenticación y Multitenancy

> Fuente de verdad para el sistema de autenticación y aislamiento por organización.

## Autenticación

- **Provider**: Supabase Auth
- **Tokens**: JWT con `org_id` en el payload
- **Verificación**: `python-jose` en el backend

## Multitenancy

### Regla de oro

```
org_id SIEMPRE del JWT verificado — NUNCA del request body
```

### RLS (Row Level Security)

Todas las tablas con datos de usuario tienen RLS activado:
- `organizations`
- `documents`
- `embeddings`
- `stories`
- `credit_ledger`
- `approval_history`

### Patrón en repositorios

```python
# ✅ Correcto — org_id del JWT
client.table("stories").select("id, title").eq("org_id", org_id).execute()

# ❌ Prohibido — org_id del body
client.table("stories").select("id, title").eq("org_id", request.org_id).execute()
```

## TODO

- [ ] Implementar refresh tokens
- [ ] Definir expiración de JWT (30 min? 1 hora?)
- [ ] Implementar invite flow para agregar usuarios a una org
