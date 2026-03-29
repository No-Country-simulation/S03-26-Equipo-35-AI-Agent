# Spec: Flujo de Aprobación

> Fuente de verdad para la máquina de estados de aprobación.

## Estados

```
BORRADOR → EN_REVISION → APROBADO → PUBLICADO
               ↓
           RECHAZADO → BORRADOR
```

## Roles y permisos

| Transición | editor | revisor | admin |
|---|---|---|---|
| borrador → en_revision | ✅ | ❌ | ✅ |
| en_revision → aprobado | ❌ | ✅ | ✅ |
| en_revision → rechazado | ❌ | ✅ | ✅ |
| aprobado → publicado | ❌ | ❌ | ✅ |
| rechazado → borrador | ✅ | ❌ | ✅ |

## Reglas

- **Publicado** es estado terminal — no hay vuelta atrás
- Ningún rol puede saltar estados
- Cada transición se registra en `approval_history`
- El historial es inmutable

## Implementación

`core/approvals/state_machine.py` — **completamente implementado**

## TODO

- [ ] Agregar notificaciones por email al cambiar de estado
- [ ] Agregar campo de comentario obligatorio al rechazar
