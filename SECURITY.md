# Política de Seguridad

Este documento describe la política de seguridad y prácticas recomendadas para contribuir a AutoStory Builder.

## Reporte de Vulnerabilidades

Por favor, no crees GitHub issues públicos para informar sobre posibles vulnerabilidades de seguridad. En su lugar, envía un reporte en privado al correo de los administradores del repositorio o a través de los canales internos designados.

Agradecemos enormemente cualquier reporte que nos ayude a mantener este proyecto seguro para nuestros usuarios.

## Manejo de Credenciales y Secretos

1. **NUNCA debes commitear el archivo `.env` o credenciales reales al repositorio.**
2. Se recomienda rotar periódicamente todas las claves de APIs (Groq, Cohere, Supabase, Redis, etc).
3. Nunca imprimas variables de entorno con URLs de infraestructura, claves privadas o Service Keys en el Logger o en Consola.
4. El archivo `.env.example` debe mantenerse genérico y sin revelar nombres de bases de datos internas, o direcciones IP específicas de la infraestructura.

## Prácticas Recomendadas de Desarrollo

- Corre `pip-audit` para validar dependencias de manera continua en Python.
- Utiliza **Pre-commit hooks** como `detect-secrets` para prevenir subidas accidentales de API Keys al código.
- Todas las URLs a las bases de datos deben validarse antes del despliegue (asegurar el uso de Anon Keys para clientes públicos y Service Keys sólo de lado del backend FastAPI con controles RLS en la base central).
