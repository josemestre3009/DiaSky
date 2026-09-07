## Purpose

Captura mensajes operativos del grupo autorizado y los relaciona de forma fiable con las fichas individuales que originan cada orden.

## ADDED Requirements

### Requirement: Receive authorized group messages idempotently
The system SHALL accept `messages.upsert` deliveries only for the configured operational WhatsApp group and SHALL record each WhatsApp message at most once by its platform message ID.

#### Scenario: Duplicate webhook delivery
- **WHEN** Evolution API redelivers a message with an already recorded platform message ID
- **THEN** the system SHALL acknowledge the delivery without creating a duplicate message, event, or order

#### Scenario: Message from another chat
- **WHEN** Evolution API delivers a message outside the configured operational group
- **THEN** the system SHALL acknowledge and ignore the message without creating an operation record

### Requirement: Create orders from authorized individual records
The system SHALL create an order only when an authorized sender posts an individual record containing sufficient operation-identifying content and SHALL retain its source WhatsApp message ID.

#### Scenario: Authorized individual installation record
- **WHEN** an authorized sender posts a record with a customer identifier and installation details
- **THEN** the system SHALL create one installation order associated with that source message

#### Scenario: Similar informal message from a technician
- **WHEN** a sender not authorized to create orders posts a message resembling an individual record
- **THEN** the system SHALL not create an order and SHALL retain the message only for audit processing

### Requirement: Correlate quoted updates to source orders
The system SHALL associate a quoted operational response with the order whose source message ID matches the quoted `stanzaId`, including responses that quote an intermediate message in the same quoted chain.

#### Scenario: Technician closes a quoted order
- **WHEN** a technician sends "listo" quoting an order record
- **THEN** the system SHALL associate the update with that order rather than another order in the same locality

#### Scenario: Unquoted status-like message
- **WHEN** a technician posts a status-like message without a resolvable quotation chain
- **THEN** the system SHALL not change an order status

### Requirement: Minimize sensitive-message exposure
The system SHALL keep customer PII, credentials, access URLs, and message payloads out of application logs, outbound reports, and language-model requests unless a field is required for the stated operation.

#### Scenario: Record contains access credentials
- **WHEN** an individual record contains credentials or a login URL
- **THEN** the system SHALL not include those values in its language-model classification input or daily report
