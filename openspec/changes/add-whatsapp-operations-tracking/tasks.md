## 1. Service Foundation

- [x] 1.1 Create the Python/FastAPI service, runtime configuration, health endpoint, Docker Compose service, production container configuration, and dependency lockfile; verify a local health request succeeds.
- [x] 1.2 Define PostgreSQL models and Alembic migrations for messages, work queue, orders, immutable operation events, corrections, and report executions; verify migration upgrade on an empty database.
- [ ] 1.3 Implement authenticated administrative API access and redacted API/log serialization; verify unauthenticated requests fail and secret fields never appear in a response or log fixture.

## 2. WhatsApp Ingestion

- [x] 2.1 Implement `messages.upsert` webhook authentication, group filtering, and idempotent message persistence; verify duplicate and foreign-group payload tests.
- [x] 2.2 Implement transactional work enqueueing and worker retries using the PostgreSQL work table; verify an injected processing failure retries without duplicate effects.
- [x] 2.3 Implement quoted-message chain resolution by WhatsApp message ID; verify direct, intermediate, unquoted, and missing-origin fixtures.
- [x] 2.4 Implement authorized-sender configuration and individual-record detection; verify authorized records create orders while technician records do not.

## 3. Operation Extraction And Lifecycle

- [x] 3.1 Implement normalization and regex extraction for operation type, locality, customer data, IP, and sensitive fields; verify representative chat fixtures parse expected non-sensitive fields.
- [x] 3.2 Implement deterministic status and reason classification with conservative handling for `listo`, client absence, power outage, definitive impossibility, and ambiguous text; verify table-driven classification tests.
- [x] 3.3 Add OpenRouter structured-output fallback with schema validation, confidence threshold, PII redaction, timeouts, and failure handling; verify request-redaction and invalid-provider-response tests.
- [x] 3.4 Persist immutable classified events, derive current order status, and record auditable administrative corrections; verify progress-to-completion history and correction tests.
- [x] 3.5 Implement order list, detail, event history, and correction endpoints; verify API integration tests for filters and correction audit data.
- [x] 3.6 Add a local single-operator administrative panel with session-only token entry, metrics, filters, order detail, and corrections; verify unauthenticated panel requests return to token entry.

## 4. Daily Reporting

- [ ] 4.1 Implement local-date summary generation separating completed, pending, failed/cancelled, and unreported orders; verify mixed-outcome report fixtures.
- [ ] 4.2 Implement scheduled 19:00 `America/Bogota` report execution with idempotent persistence; verify scheduler timezone and duplicate-run tests.
- [ ] 4.3 Implement private-recipient delivery through Evolution API, retry behavior, redacted reporting, and explicit manual resend; verify outbound payload and no-automatic-resend tests.

## 5. Deployment Verification

- [ ] 5.1 Document local Docker Compose, ngrok webhook testing, cloud Evolution API, OpenRouter, database, authorized-sender, group, recipient, and webhook-secret configuration; verify documented local startup from an empty environment.
- [ ] 5.2 Add GitHub repository deployment documentation and EasyPanel manifests/configuration, excluding secrets; verify EasyPanel can build the API and worker images from the selected branch.
- [ ] 5.3 Configure persistent PostgreSQL, protected runtime variables, migrations, health checks, and a stable HTTPS domain in EasyPanel; verify deployment survives a service restart with retained data.
- [ ] 5.4 Configure the stable EasyPanel webhook URL in cloud Evolution API and run the complete test suite plus a webhook-to-private-summary smoke test using non-production data; verify no duplicate orders, no PII in LLM payloads, and one report delivery.
