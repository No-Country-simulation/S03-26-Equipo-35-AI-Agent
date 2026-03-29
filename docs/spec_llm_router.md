# Spec: LLM Router

> Fuente de verdad para el routing de proveedores LLM.

## Proveedores (orden de fallback)

| Prioridad | Proveedor | Modelo | Rol |
|---|---|---|---|
| 1° | Gemini Flash | gemini-2.0-flash | Preprocesamiento, clasificación |
| 2° | Groq | llama-3.3-70b-versatile | Composición narrativa principal |
| 3° | OpenRouter | configurable | Fallback final |

## Flujo de routing

```
Tarea → Gemini Flash (clasificar) → Groq (generar) → Respuesta
                                        ↓ (429/timeout)
                                    OpenRouter (fallback)
```

## Prompt Structure (5 ejes)

```
[ROL] [CONTEXTO DE MARCA — RAG] [TAREA] [RESTRICCIONES] [FORMATO DE SALIDA]
```

## Reglas

- Créditos se deducen ANTES de llamar al LLM
- Si LLM falla: reembolsar créditos
- Prompts del sistema en archivos .md, nunca hardcodeados

## TODO

- [ ] Definir timeout por proveedor
- [ ] Definir retry policy (¿tenacity?)
- [ ] Definir logging de latencia por provider
