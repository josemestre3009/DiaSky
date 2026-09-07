## Purpose

Consolida el resultado diario de las operaciones y lo entrega una vez al día al contacto privado de coordinación configurado.

## ADDED Requirements

### Requirement: Generate a daily operational summary
The system SHALL generate a summary for the configured business date containing completed, pending, failed or cancelled, and unreported orders, with non-sensitive reasons where applicable.

#### Scenario: Mixed daily outcomes
- **WHEN** the reporting date contains completed, pending, and unreported orders
- **THEN** the summary SHALL present each outcome group separately with counts and relevant order details

### Requirement: Deliver one private daily summary
The system SHALL send one daily summary at 19:00 in the `America/Bogota` time zone to the configured individual WhatsApp recipient and SHALL not send operational alerts during the day.

#### Scenario: Scheduled delivery
- **WHEN** local time reaches 19:00 on an operational day
- **THEN** the system SHALL deliver that day's summary to the configured private recipient

#### Scenario: Report rerun
- **WHEN** a summary is regenerated after the scheduled delivery
- **THEN** the system SHALL not automatically send an additional WhatsApp message unless an authorized user explicitly requests delivery

### Requirement: Protect report recipient configuration
The system SHALL obtain the destination WhatsApp JID from protected runtime configuration and SHALL not expose it through unauthenticated endpoints or logs.

#### Scenario: Configuration inspection
- **WHEN** operational configuration is logged or returned by an API
- **THEN** the recipient JID SHALL be absent or redacted
