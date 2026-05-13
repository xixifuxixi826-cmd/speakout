## ADDED Requirements

### Requirement: System provides a minimum viable admin dashboard
The system SHALL provide an admin-facing dashboard with core user, training, and revenue overview metrics for V1 operations.

#### Scenario: Admin sees overview metrics
- **WHEN** an authenticated admin opens the dashboard
- **THEN** the system shows at least registered users, daily active users, training volume, paid users, and revenue overview

### Requirement: System provides admin user and order visibility
The system SHALL allow authorized admins to view user and order lists for V1 operations.

#### Scenario: Admin accesses user list
- **WHEN** an authorized admin opens the users page
- **THEN** the system returns a paginated list containing user identity, registration time, activity state, membership status, and training summary fields

#### Scenario: Admin accesses order list
- **WHEN** an authorized admin opens the orders page
- **THEN** the system returns a paginated list containing order number, user, amount, status, and payment time

### Requirement: System allows admin content management for words
The system SHALL allow authorized admins to create, edit, publish, and offline word content items used in V1 card association training.

#### Scenario: Admin publishes a new word item
- **WHEN** an authorized admin creates a valid word content item and publishes it
- **THEN** the system makes that content item available to eligible training selection logic

#### Scenario: Offline content is excluded from new rounds
- **WHEN** a word content item is marked offline
- **THEN** the system excludes that content item from future round generation
