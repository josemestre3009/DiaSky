# DiaSky Operations

Seguimiento de órdenes WhatsApp mediante Evolution API.

## Local

```bash
cp .env.example .env
# Completa todos los valores de .env
docker compose up --build
curl http://localhost:8000/health
```

API administrativa: `http://localhost:8000/docs`. Envía `Authorization: Bearer <ADMIN_TOKEN>`.

Prueba Evolution cloud contra local:

```bash
ngrok http 8000
```

Configura en Evolution el evento `messages.upsert` hacia:

```text
https://<ngrok-id>.ngrok-free.app/webhooks/evolution/<WEBHOOK_PATH_TOKEN>
```

Si Evolution admite un encabezado personalizado, usa además `X-Webhook-Secret` con el valor de `WEBHOOK_SECRET`. Si no lo admite, deja `WEBHOOK_SECRET` vacío: el token aleatorio de URL protege el endpoint. Confirma el payload real antes de habilitar producción.

## Variables

`.env.example` enumera las variables requeridas: Evolution cloud, JID de grupo, creadores autorizados, destinatario, OpenRouter, PostgreSQL, token admin y secreto webhook. Nunca versionar `.env`.

## EasyPanel

Despliega desde GitHub con el `Dockerfile`. Crea servicios separados `api` y `worker` desde la misma imagen, un PostgreSQL persistente, variables protegidas idénticas a `.env`, healthcheck `GET /health`, migración `alembic upgrade head`, dominio HTTPS estable para API. Apunta Evolution a `https://<dominio>/webhooks/evolution`.

No usar ngrok en producción.
