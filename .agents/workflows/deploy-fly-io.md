---
description: Deploy de AutoStory Builder a Fly.io
---

# Workflow: Deploy a Fly.io

Pasos para hacer deploy del backend FastAPI a producción.

## Pre-requisitos

- `fly` CLI instalado (`curl -L https://fly.io/install.sh | sh`)
- Cuenta de Fly.io configurada (`fly auth login`)
- Secrets configurados en Fly.io

## Pasos

// turbo
1. Verificar que el código pasa CI localmente:
```bash
ruff check .
pytest tests/unit/ -v
```

2. Configurar secrets en Fly.io:
```bash
fly secrets set GOOGLE_API_KEY=xxx GROQ_API_KEY=xxx COHERE_API_KEY=xxx \
  SUPABASE_URL=xxx SUPABASE_KEY=xxx JWT_SECRET=xxx \
  UPSTASH_REDIS_URL=xxx UPSTASH_REDIS_TOKEN=xxx \
  ENVIRONMENT=production LOG_LEVEL=INFO
```

3. Hacer deploy:
```bash
fly deploy
```

// turbo
4. Verificar health check:
```bash
fly status
curl https://autostory-builder.fly.dev/health
```

5. Verificar logs:
```bash
fly logs --app autostory-builder
```

## Rollback

```bash
# Ver releases anteriores
fly releases

# Rollback a una release específica
fly deploy --image <previous-image>
```
