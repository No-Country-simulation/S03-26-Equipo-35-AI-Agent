# Spec: Sistema de Créditos

> Fuente de verdad para el sistema de créditos.

## Costos por operación

| Operación | Créditos |
|---|---|
| Solo texto | 1 |
| Texto + imagen | 3 |
| Audio (Fase 2) | 5 |

## Flujo crítico

```
1. VERIFICAR balance >= costo
2. DEDUCIR créditos (registrar en ledger)
3. Llamar al LLM
4. Si LLM falla → REEMBOLSAR créditos
```

> ⚠️ NUNCA invertir el orden. NUNCA llamar al LLM antes de deducir.

## Arquitectura

- **Ledger inmutable**: No se modifican ni eliminan entradas
- **Balance**: Calculado como `SUM(amount)` del ledger por org_id
- **Tipos de operación**: purchase, deduction, refund, bonus, adjustment

## TODO

- [ ] Definir límites de plan (free: 50 créditos/mes, pro: 500)
- [ ] Implementar vista materializada para performance
- [ ] Definir alertas de balance bajo
