---
name: Security Review
description: Revisión de seguridad del código de AutoStory Builder
---

# Skill: Security Review

## Contexto
Checklist de seguridad para AutoStory Builder.

## Checklist obligatorio

### 🔴 Multitenancy
- [ ] Todo query a DB incluye `.eq("org_id", org_id)`
- [ ] `org_id` siempre del JWT verificado, nunca del request body
- [ ] RLS activado en todas las tablas con datos de usuario
- [ ] Tests de aislamiento RLS pasando

### 🔴 Autenticación
- [ ] Todos los endpoints protegidos requieren JWT válido
- [ ] JWT verificado con `python-jose` y secret del servidor
- [ ] Tokens con expiración configurada
- [ ] No hardcodear JWT_SECRET en el código

### 🔴 Créditos
- [ ] Flujo: verificar → deducir → LLM → reembolsar
- [ ] Nunca llamar LLM antes de deducir
- [ ] Ledger inmutable — sin UPDATE ni DELETE

### 🟡 Input Validation
- [ ] URLs del scraper sanitizadas contra SSRF
- [ ] Solo HTTPS permitido para scraping
- [ ] Pydantic valida todos los inputs de API
- [ ] SQL parametrizado — sin f-strings

### 🟡 Secretos
- [ ] Sin API keys en el código
- [ ] `.env` en `.gitignore`
- [ ] `.env.example` sin valores reales
