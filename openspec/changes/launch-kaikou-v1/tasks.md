## 1. OpenSpec And Scope Freeze

- [ ] 1.1 Consolidate the existing V1 product and architecture documents into the OpenSpec `launch-kaikou-v1` change
- [ ] 1.2 Review the proposal, design, and capability specs for consistency with the current product direction
- [ ] 1.3 Freeze the V1 scope around WeChat login, card association training, AI feedback, membership, history, and minimum admin operations

## 2. Platform Data Model

- [ ] 2.1 Create the platform-level database schema for users, memberships, content items, training sessions, submissions, feedback, analytics, and orders
- [ ] 2.2 Add card-association-specific extension tables for rounds and card instances
- [ ] 2.3 Add the content source model and `content_generation_task` table to support future AI-generated content
- [ ] 2.4 Define indexes, unique constraints, and field conventions for session, content, and order identifiers

## 3. Backend Foundation

- [ ] 3.1 Initialize the module-oriented backend structure for user, membership, content, training, AI, speech, analytics, and admin domains
- [ ] 3.2 Implement unified response, error handling, configuration, and authentication infrastructure
- [ ] 3.3 Implement WeChat login session handling and user binding
- [ ] 3.4 Implement membership status lookup, daily quota enforcement, and order lifecycle basics

## 4. Content And Training Engine

- [ ] 4.1 Implement the unified content center with support for V1 word content and source typing
- [ ] 4.2 Implement card association round initialization with 16 cards, 8 nouns, 8 adjectives, and same-day deduplication logic
- [ ] 4.3 Implement card flip, select, round progression, and used-card persistence
- [ ] 4.4 Implement training session creation, submission storage, and history retrieval

## 5. AI And Speech Integration

- [ ] 5.1 Implement the AI provider abstraction and schema-based feedback persistence
- [ ] 5.2 Implement the card-association feedback flow with limited vs full membership visibility
- [ ] 5.3 Implement retryable AI analysis for failed feedback generation
- [ ] 5.4 Implement the V1 speech input path with ASR integration and text-input fallback

## 6. Frontend Mini Program

- [ ] 6.1 Initialize the WeChat Mini Program project structure and core navigation
- [ ] 6.2 Implement the home page, remaining quota summary, and training entry flow
- [ ] 6.3 Implement the card association page, thinking countdown, speaking input page, and feedback page
- [ ] 6.4 Implement history display and membership upsell entry points

## 7. Admin Operations

- [ ] 7.1 Initialize the admin web project structure and login flow
- [ ] 7.2 Implement the dashboard overview for users, training activity, and revenue
- [ ] 7.3 Implement user list, order list, and word content management pages
- [ ] 7.4 Add the minimum content generation task page scaffold for future AI-generated content workflows

## 8. Launch Readiness

- [ ] 8.1 Add analytics events for login, session creation, submission, completion, and payment success
- [ ] 8.2 Verify the end-to-end V1 flow from login to training completion and feedback retrieval
- [ ] 8.3 Verify membership gating, history visibility, and admin content operations
- [ ] 8.4 Prepare the V1 release checklist for deployment, testing, and Mini Program submission
