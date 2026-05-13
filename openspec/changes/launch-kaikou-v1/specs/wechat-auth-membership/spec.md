## ADDED Requirements

### Requirement: User can sign in with WeChat identity
The system SHALL allow users to sign in through WeChat Mini Program login and bind the resulting identity to a platform user record without requiring separate account registration.

#### Scenario: First-time WeChat login creates a user
- **WHEN** a user enters the Mini Program for the first time and submits a valid WeChat login code
- **THEN** the system creates a platform user record bound to the user's `openid`

#### Scenario: Returning WeChat login reuses the existing user
- **WHEN** a returning user submits a valid WeChat login code
- **THEN** the system resolves the existing bound user and returns a valid login session

### Requirement: System enforces daily training quota for free users
The system SHALL track and enforce daily training quota based on user membership status.

#### Scenario: Free user sees remaining quota
- **WHEN** a free user loads the home summary for the current day
- **THEN** the system returns the current remaining training count for that day

#### Scenario: Free user exhausts daily quota
- **WHEN** a free user has used all daily free sessions
- **THEN** the system blocks creation of a new training session and returns a membership upgrade prompt

### Requirement: Membership status controls premium access
The system SHALL use membership status to control premium features, including unlimited training, full AI feedback, and history visibility.

#### Scenario: Member receives unlimited training access
- **WHEN** a user has an active membership
- **THEN** the system SHALL not apply the daily session limit to that user

#### Scenario: Non-member is denied premium history access
- **WHEN** a non-member requests premium-only history data
- **THEN** the system SHALL deny full access and indicate that membership is required
