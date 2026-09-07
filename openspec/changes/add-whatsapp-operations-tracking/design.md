## Context

No existe aplicación operativa; el único historial disponible es un export de WhatsApp. Las fichas individuales contienen PII y, ocasionalmente, credenciales o URLs de acceso. Las respuestas de técnicos suelen citar la ficha, aunque puede haber citas intermedias y mensajes sin relación con una orden.

Ver `proposal.md` y sus tres specs para alcance conductual.

## Goals / Non-Goals

**Goals:**
- Aceptar webhooks rápidamente, tolerar reintentos y procesar mensajes fuera de la solicitud HTTP.
- Conservar evidencia suficiente para auditoría, con estado actual derivado de eventos.
- Reducir coste y exposición de datos usando expresiones regulares antes de OpenRouter.
- Permitir un único despliegue sencillo con API, worker y PostgreSQL.

**Non-Goals:**
- Bot conversacional, panel web completo, OCR, transcripción de audios, migración automática del historial, ni alertas inmediatas.
- Decidir pagos, activar servicios, ni ejecutar acciones sobre redes o sistemas de clientes.

## Decisions

### FastAPI, PostgreSQL y worker basado en tabla de trabajos

La API y PostgreSQL se ejecutarán localmente con Docker Compose para desarrollo. Producción se desplegará desde GitHub en EasyPanel, donde API, worker y PostgreSQL usarán un dominio HTTPS estable y un volumen persistente. La API recibirá `messages.upsert` desde la instancia cloud existente de Evolution API a través de una URL HTTPS temporal de ngrok en pruebas locales, o mediante el dominio EasyPanel en producción; verificará el secreto del webhook, filtrará el JID grupal, persistirá el mensaje y encolará un trabajo en la misma transacción. Un proceso worker reclamará trabajos con bloqueo de fila, reintentos limitados y registro de error. PostgreSQL guardará mensajes, órdenes, eventos, correcciones y ejecuciones de reporte.

Se evita Redis, Celery y Kafka: un volumen diario de chat no justifica infraestructura adicional. Si varios workers o cargas altas vuelven insuficiente el patrón, migrar la tabla de trabajos a una cola dedicada sin cambiar contratos API.

### Correlación por IDs de WhatsApp, no por texto

Cada ficha crea una orden con `source_message_id`. El worker resuelve `contextInfo.stanzaId`; si cita un mensaje intermedio, recorre su cadena de mensajes citados hasta la ficha. El JID de autor se conserva, pero la creación de órdenes se restringe a una lista configurable de JIDs autorizados.

La alternativa de asociar por población, cliente o similitud textual se descarta: el historial contiene múltiples operaciones en una misma población y nombres inconsistentes.

### Eventos inmutables y estado derivado

`operation_events` retiene texto normalizado, clasificación, confianza, motivo y autor. `orders.current_status` es una proyección actualizable; una corrección humana añade un evento administrativo, nunca reemplaza extracción previa. La fecha programada de la orden permanece separada del momento de reporte.

Estados: `completada`, `pendiente`, `fallida`, `cancelada`, `en_progreso`; `sin_reporte` solo etiqueta una fila del resumen diario. Motivos usan catálogo, con texto breve redaccionado.

### Pipeline de extracción por capas

El parser normaliza texto y detecta datos estructurados mediante regex: tipo de operación, cliente, documento, IP, localidad, teléfono, dirección, URL y términos de resultado. Reglas de alta certeza clasifican expresiones como `listo`, `no hay nadie`, `no hay luz`, `no es posible`.

Mensajes citados sin regla concluyente se envían a OpenRouter con esquema JSON estricto, lista cerrada de estados/motivos y una explicación específica, no sensible, del motivo. PII, tokens, URLs, contraseñas, teléfonos, documentos, direcciones e IPs se eliminan antes de esa llamada. Resultado inválido, baja confianza o error de proveedor crea evento `requiere_revision`, sin modificar estado.

La alternativa de enviar todo el chat al modelo se descarta: aumenta coste, fuga de datos y errores de correlación.

### API administrativa mínima y autenticada

El servicio expondrá endpoints autenticados para consultar órdenes por fecha/estado/localidad, consultar detalle y eventos, corregir estado o motivo, generar un reporte y solicitar su envío. Los endpoints de webhook permanecen separados. Respuestas administrativas omitirán secretos y credenciales.

El panel web y bot quedan fuera del núcleo: ambos serán consumidores futuros de estos contratos.

Un panel HTML/CSS/JavaScript servido por FastAPI cubre el único operador administrativo del MVP. Guardará el token existente únicamente en `sessionStorage`, consumirá los endpoints administrativos y no introduce usuarios, roles, sesiones de servidor ni un framework frontend.

### Reporte diario programado

Una tarea planificada a las 19:00 `America/Bogota` calculará el resumen para la fecha local, persistirá una ejecución idempotente y lo enviará mediante Evolution API al JID individual de `REPORT_RECIPIENT_JID`. Reejecuciones regeneran datos sin reenvío automático; el envío adicional requiere acción autenticada explícita.

### Entornos locales y producción

Docker Compose definirá API, worker y PostgreSQL para desarrollo local, con secretos en `.env` no versionado. Las pruebas unitarias e integración local no requieren WhatsApp; las pruebas de webhook real usarán ngrok contra la API local. GitHub almacenará código y manifiestos sin secretos. EasyPanel construirá desde la rama de despliegue, proporcionará variables protegidas, ejecutará migraciones de base de datos y conservará PostgreSQL en un volumen persistente. El webhook de Evolution API apuntará exclusivamente al dominio HTTPS estable de EasyPanel en producción.

Se descarta usar ngrok en producción: su URL gratuita cambia y el proceso local no ofrece disponibilidad suficiente para el cierre diario.

## Risks / Trade-offs

- [Evolution API reintenta o entrega fuera de orden] → índices únicos por mensaje, transacciones y eventos ordenados por hora de origen.
- [Cita a mensaje no almacenado] → conservar mensaje como no correlacionado y permitir reprocesamiento cuando llegue su origen.
- [Clasificación incorrecta] → reglas conservadoras, umbral de confianza, revisión humana y eventos inmutables.
- [PII y secretos en chat] → cifrado en reposo para payload bruto, redacción antes de log/LLM/reporte, secretos solo en configuración protegida.
- [Fallo a las 19:00] → registrar ejecución, reintentar entrega y permitir regeneración/envío manual.
- [Audios e imágenes contienen el cierre real] → V1 registra metadatos; añadir transcripción/OCR solo tras medir omisiones.

## Migration Plan

1. Levantar PostgreSQL, API y worker locales con Docker Compose, sin activar webhook.
2. Configurar grupo, JIDs de autores, secreto Evolution, OpenRouter y destinatario privado.
3. Exponer FastAPI con `ngrok http 8000` y registrar su URL HTTPS temporal en la instancia cloud de Evolution API.
4. Validar mensajes reales en modo de revisión sin envío de reportes.
5. Verificar correlación, correcciones y formato del resumen con una jornada.
6. Subir el repositorio sin secretos a GitHub y configurar el despliegue de API, worker y PostgreSQL persistente en EasyPanel.
7. Configurar dominio HTTPS estable y variables protegidas en EasyPanel, actualizar el webhook de Evolution API hacia ese dominio y verificar la entrega.
8. Activar tarea de 19:00 y entrega al número privado.

Rollback: revertir el despliegue de EasyPanel o retirar/actualizar su URL de webhook en Evolution API; en desarrollo, retirar la URL ngrok. Desactivar worker y scheduler si es necesario; los mensajes y eventos persistidos permanecen disponibles para auditoría. No hay migración de datos existente.

## Open Questions

- El mecanismo exacto de firma/autenticación saliente y entrante depende de la versión configurada de Evolution API; se resolverá contra su documentación durante integración sin alterar contratos.
- La rama, dominio y mecanismo exacto de despliegue de EasyPanel se definirán al configurar la plataforma; no alteran los contratos de la aplicación.
