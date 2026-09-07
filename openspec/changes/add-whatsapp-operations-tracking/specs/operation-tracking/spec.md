## Purpose

Mantiene una vista estructurada y corregible de cada orden, preservando los reportes originales de técnicos y coordinadores durante su ciclo de vida.

## ADDED Requirements

### Requirement: Track an immutable order event history
The system SHALL create a timestamped event for every classified quoted update and SHALL preserve prior events when an order receives later updates.

#### Scenario: Order receives progress then completion
- **WHEN** an order first receives an in-progress update and later a completion update
- **THEN** the system SHALL retain both events and expose completion as the current status

### Requirement: Classify operational outcomes conservatively
The system SHALL classify correlated updates as `completada`, `pendiente`, `fallida`, `cancelada`, `en_progreso`, or `sin_cambio`; it SHALL retain both a structured reason category and an AI-extracted, non-sensitive explanation when an outcome is not completed.

#### Scenario: Customer absent
- **WHEN** a quoted update reports "no hay nadie" or an equivalent customer-availability problem
- **THEN** the system SHALL set the order to `pendiente` with an absence-related reason

#### Scenario: Specific ambiguous reason
- **WHEN** a correlated update contains an operational reason not fully captured by deterministic rules
- **THEN** the system SHALL request a redacted explanation from the language model and retain its specific explanation with the classified reason category

#### Scenario: Definitive impossibility
- **WHEN** a quoted update establishes that the operation cannot be performed definitively
- **THEN** the system SHALL classify it as `fallida` or `cancelada` and retain the stated reason

#### Scenario: Ambiguous update
- **WHEN** a correlated update cannot be classified with adequate confidence
- **THEN** the system SHALL create an event marked for review without changing the current order status

### Requirement: Identify unreported orders at day close
The system SHALL classify orders scheduled for a reporting day with no concluding operational update as `sin_reporte` in that day's summary without altering their underlying order history.

#### Scenario: No technician response
- **WHEN** the daily close occurs for an order without a completion, pending, failure, cancellation, or in-progress update that day
- **THEN** the order SHALL appear under `sin_reporte` in the daily summary

### Requirement: Permit audited administrative correction
The system SHALL provide an authenticated administrative operation to correct an order's current status or reason while preserving the original extraction and recording the correction actor and time.

#### Scenario: Correct model interpretation
- **WHEN** an administrator corrects a pending order to completed
- **THEN** the system SHALL retain the extracted event and record an administrative correction that becomes the current status

### Requirement: Provide a single-operator administrative panel
The system SHALL provide a local administrative panel for one operator to view daily operational metrics, filter orders, inspect event history, and submit corrections using the existing administrative token.

#### Scenario: Authorized panel session
- **WHEN** the operator supplies a valid administrative token in the panel
- **THEN** the panel SHALL show order data and retain the token only for the current browser session

#### Scenario: Invalid panel token
- **WHEN** the panel API request receives an unauthorized response
- **THEN** the panel SHALL remove its stored session token and require the operator to authenticate again
