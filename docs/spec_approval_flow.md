# Spec: Flujo de Aprobación Documental

> Fuente de verdad para la máquina de estados de aprobación corporativa.

## Matriz de Estados Central

El universo de las historias es estricto en sus transiciones. Implementado de forma pura en `core/approvals/state_machine.py`.

```
BORRADOR → EN_REVISION → APROBADO → PUBLICADO
               ↓                ↓ (Feedback UI)
           RECHAZADO ←—←—←—←—←—←
```

## Roles y Permisos Enforcement 

| Transición | Editor UI | Revisor AI/UI | Root (Admin) |
|---|---|---|---|
| borrador → en_revision | ✅ | ❌ | ✅ |
| en_revision → aprobado | ❌ | ✅ | ✅ |
| en_revision → rechazado | ❌ | ✅ | ✅ |
| aprobado → publicado | ❌ | ❌ | ✅ |
| rechazado → borrador | ✅ | ❌ | ✅ |

## Reglas Universales del SDK Interno

- **Publicado** es estado terminal y la mutación está vetada en la base de datos si ya se exportó.
- Cada cambio graba un snapshot inviolable en `approval_history`.
- El frontend soporta versionado de texto (`frontend/pages/3_mis_historias.py`) donde el Historial es totalmente restaurable.

## Estado (V2 MVP)
✅ Completo a nivel código, endpoints y base de datos con verificación multi-tenant exhaustiva. Funciones extendidas como "Push to social media directo" contempladas en Fase 3.
