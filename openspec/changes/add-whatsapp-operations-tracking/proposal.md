## Why

El seguimiento de instalaciones y soporte ocurre en conversaciones informales de WhatsApp, sin trazabilidad estructurada ni cierre fiable de cada orden. Se necesita consolidar las operaciones diarias sin depender de revisión manual del grupo.

## What Changes

- Recibir webhooks `messages.upsert` de Evolution API para un grupo operativo configurado.
- Crear órdenes desde fichas individuales enviadas por autores autorizados.
- Relacionar respuestas citadas con su ficha origen, conservar eventos y mantener el estado actual de cada orden.
- Extraer estados y motivos mediante reglas deterministas y OpenRouter solo para mensajes ambiguos.
- Exponer una API administrativa para consultar y corregir órdenes.
- Añadir un panel administrativo local de un solo operador para consultar, filtrar y corregir órdenes mediante el token existente.
- Generar y enviar un único resumen diario al número privado configurado a las 19:00 `America/Bogota`.
- Proteger PII, credenciales y enlaces de clientes frente a registros, respuestas API y solicitudes al LLM.

## Capabilities

### New Capabilities
- `whatsapp-operation-ingestion`: ingesta idempotente, filtrado y correlación de mensajes operativos de WhatsApp.
- `operation-tracking`: ciclo de vida, trazabilidad y corrección administrativa de órdenes.
- `daily-operation-reporting`: consolidación y envío privado del resumen diario.

### Modified Capabilities

- Ninguna.

## Impact

- Nuevo servicio Python/FastAPI, PostgreSQL, worker y tarea programada ejecutables localmente con Docker Compose y desplegables desde GitHub en EasyPanel.
- Integración con la instancia cloud existente de Evolution API; ngrok expondrá el webhook local solo durante pruebas y EasyPanel publicará una URL HTTPS estable en producción.
- Integración saliente con Evolution API y OpenRouter.
- Nuevas variables de entorno para secretos, grupo operativo, autores autorizados y destinatario privado.
