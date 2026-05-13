## ADDED Requirements

### Requirement: System returns structured AI feedback for each completed training submission
The system SHALL generate AI feedback in a structured schema for every successfully submitted training session.

#### Scenario: Card training receives schema-based feedback
- **WHEN** a user submits a valid card association response
- **THEN** the system returns feedback with a declared feedback schema, total score, summary, detailed scoring data, suggestions, and rewrite content

#### Scenario: Feedback is persisted for later retrieval
- **WHEN** AI feedback is generated successfully
- **THEN** the system stores the feedback against the originating training session

### Requirement: AI feedback evaluates expression quality rather than word-type correctness
The system SHALL evaluate whether the user established a coherent relationship and expressed it clearly, and SHALL NOT reject a response because of word-type pairing.

#### Scenario: Two adjectives receive valid evaluation
- **WHEN** a user trains with two adjective cards and submits a coherent answer
- **THEN** the system evaluates the response on expression quality and does not mark it invalid due to the pairing

#### Scenario: Logic and clarity drive scoring
- **WHEN** the AI analyzes a submission
- **THEN** the scoring emphasizes structure, logic, specificity, and fluency instead of enforcing linguistic pairing rules

### Requirement: Membership status controls feedback detail
The system SHALL apply membership-based feedback visibility rules without changing the underlying stored feedback record.

#### Scenario: Free user sees limited feedback
- **WHEN** a free user views a feedback result
- **THEN** the system returns or renders the limited V1 feedback subset allowed for free users

#### Scenario: Member sees full feedback
- **WHEN** a member views a feedback result
- **THEN** the system returns or renders the complete stored feedback set for that session

### Requirement: AI analysis failures support retry without losing the submission
The system SHALL preserve the user submission when AI analysis fails and SHALL allow retry of the analysis.

#### Scenario: AI provider failure retains submission
- **WHEN** the AI analysis request fails after a valid submission is stored
- **THEN** the system keeps the submission record and marks analysis as retryable

#### Scenario: Retry regenerates feedback for the same session
- **WHEN** a retry is triggered for a failed analysis
- **THEN** the system attempts AI analysis again using the stored session and submission data
