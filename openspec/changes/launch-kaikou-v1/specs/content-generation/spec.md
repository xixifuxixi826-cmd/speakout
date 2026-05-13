## ADDED Requirements

### Requirement: System stores training content in a unified content center
The system SHALL store V1 training content in a unified content model that supports multiple content types and source types.

#### Scenario: Preset word content is stored in content center
- **WHEN** a V1 word item is created for card association training
- **THEN** the system stores it as a content item with content type and source type metadata

#### Scenario: Future content types reuse the same content center
- **WHEN** the platform later introduces debate topics or speech scripts
- **THEN** those items can be stored without changing the fundamental content center contract

### Requirement: System distinguishes content source strategy
The system SHALL distinguish between preset, AI-generated, and imported content sources.

#### Scenario: Preset content is marked explicitly
- **WHEN** a word item is created manually in the admin
- **THEN** the system marks its source type as preset

#### Scenario: AI-generated content is marked explicitly
- **WHEN** content is created through a generation task
- **THEN** the system marks its source type as AI-generated

### Requirement: System tracks content generation tasks for future dynamic content workflows
The system SHALL support a content generation task model for AI-generated or domain-scoped content, even if V1 defaults to preset content.

#### Scenario: Admin creates a content generation task
- **WHEN** an authorized admin creates a generation task for word content
- **THEN** the system stores the requested content type, difficulty, domain, count, and task status

#### Scenario: Generated content can be published into the content pool
- **WHEN** a generation task completes successfully and its results are approved for use
- **THEN** the system can publish those generated items into the active content pool

### Requirement: Training session can request content by source strategy
The system SHALL allow training creation logic to declare whether it wants preset content, AI-generated content, or a mixed content strategy.

#### Scenario: Session requests preset content
- **WHEN** a V1 card association session is created with preset content strategy
- **THEN** the system builds the round from eligible preset word items

#### Scenario: Session requests mixed content
- **WHEN** a future session is created with mixed content strategy
- **THEN** the system can combine eligible preset and AI-generated content without changing the training session contract
