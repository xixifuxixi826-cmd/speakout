## ADDED Requirements

### Requirement: System supports 4x4 card association rounds
The system SHALL provide a card association training mode with 16 cards arranged conceptually as a 4x4 matrix in each round.

#### Scenario: Round initializes with 16 cards
- **WHEN** a user starts a new card association round
- **THEN** the system creates exactly 16 card instances for that round

#### Scenario: Round contains noun and adjective content
- **WHEN** a new round is initialized
- **THEN** the system includes 8 noun words and 8 adjective words in the round content set

### Requirement: Users can train with any two selected cards
The system SHALL allow users to train with any two selected cards without enforcing word-type pairing rules.

#### Scenario: Noun and adjective pair is accepted
- **WHEN** a user selects one noun card and one adjective card
- **THEN** the system allows the user to proceed into training

#### Scenario: Two nouns are accepted
- **WHEN** a user selects two noun cards
- **THEN** the system allows the user to proceed into training

#### Scenario: Two adjectives are accepted
- **WHEN** a user selects two adjective cards
- **THEN** the system allows the user to proceed into training

### Requirement: Card usage state persists within a round
The system SHALL track per-card state as hidden, flipped, or used within a round and persist those states across the round lifecycle.

#### Scenario: Card flips on selection
- **WHEN** a user taps a hidden card
- **THEN** the system changes that card state to flipped and reveals the card word

#### Scenario: Selected cards become used after successful training
- **WHEN** a user completes a training submission using two selected cards
- **THEN** the system marks only those two cards as used

### Requirement: Round completion advances to a fresh round
The system SHALL treat a round as complete when all 16 cards have been used and SHALL create a fresh round on continuation.

#### Scenario: Round completes after all cards are used
- **WHEN** all 16 cards in the round have reached used state
- **THEN** the system marks the round complete and presents an action to enter the next round

#### Scenario: New round resets card state
- **WHEN** the user enters the next round
- **THEN** the system creates a new 16-card round with all card states reset

### Requirement: Card content avoids same-day duplicates for a user
The system SHALL avoid reusing already-served words for the same user within the same day whenever available inventory is sufficient.

#### Scenario: Same-day word is excluded from a later round
- **WHEN** a user starts another round on the same day
- **THEN** the system excludes words already served to that user earlier that day if enough alternatives exist

#### Scenario: Limited inventory falls back gracefully
- **WHEN** the available content inventory is insufficient to fully avoid repeats
- **THEN** the system prioritizes non-repeated words and allows controlled fallback instead of failing round creation
