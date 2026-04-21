# Spec: Sistema de Créditos Ledger Transaccional

> Fuente de verdad para las finanzas y control de uso del motor de generación.

## Costos por operación (Reglas V2)

| Operación | Costo (Créditos) |
|---|---|
| Solo texto | 1 |
| Texto e ingesta RAG simple | 1 |
| Texto + imagen / Video Scan | 3 |
| Documentos Pesados (Fase 2) | 5 |

## Arquitectura Definitiva (Capa `core/credits/`)

El modelo usa contabilidad de doble entrada inmutable y a prueba de colisiones (Race-Conditions).

```
1. ROUTER VERIFICA balance asíncrono
2. core.credits.deductor DEDUCE créditos (Commit registro atómico en `credit_ledger`)
3. EJECUCIÓN: Graph/LLM es activado.
4. Si LLM falla/Timeout crítico → CALLBACK DE REEMBOLSO (refund)
```

> ⚠️ NUNCA invertir el orden. Es preferible reembolsar crédito no usado que tener una ejecución de la IA desfinanciada.

## Consistencia de la Base de Datos

- **Ledger Inmutable**: `UPDATE` y `DELETE` prohibidos por regla RLS a nivel `credit_ledger`. Solo se toleran `INSERT`.
- **Balance Activo**: Se calcula dinámicamente mediante RPC SQL (`get_credit_balance`) o vista materializada `SUM(amount)` para performance máxima sin riesgo.

## Estado (V2 MVP)
✅ Cien por ciento validado mediante robusta integración E2E. Alertas y planes a gestionar por la capa del portal Billing a futuro.
