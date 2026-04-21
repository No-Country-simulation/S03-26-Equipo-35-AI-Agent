# Spec: Autenticación y Multitenancy

> Fuente de verdad para el sistema de autenticación y aislamiento por organización.
> **Auditoría V2 Completa**: Cero bypasses, cero "demo modes". Todo acceso debe estar autenticado en Supabase.

## Autenticación

- **Provider**: Supabase Auth (Estricto)
- **Tokens**: JWT protegidos, firmados por la base de datos central.
- **Verificación**: Dependencia en FastAPI `api/dependencies.py` que extrae el `org_id` y `user_id` de forma criptográficamente segura.

## Multitenancy

### Regla de oro

```
org_id SIEMPRE del JWT verificado — NUNCA del request body
```

### RLS (Row Level Security)

Todas las tablas con datos de usuario tienen políticas RLS consolidadas e inviolables a nivel de base de datos PostgreSQL:
- `organizations`
- `documents`
- `embeddings`
- `stories`
- `credit_ledger`
- `approval_history`
- `golden_examples`

### Patrón en repositorios y servicios core

La lógica de negocio reside en la capa `core/`. Los routers HTTP solo inyectan el `CurrentUser` (que empaqueta `org_id` y `user_id`) hacia adentro para garantizar el aislamiento.

```python
# ✅ Correcto — org_id inyectado por FastAPI Dependency
await mi_servicio_core(org_id=user.org_id)
```

## Estado (V2 MVP)
✅ Implementación completa y auditada. No existen endpoints espías o mocks.
