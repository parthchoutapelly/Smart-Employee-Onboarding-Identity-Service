# Phase 5 — Testing & Integration

## Context
Validates the full pipeline end-to-end. Depends on: Phases 1-4 complete.

## Tasks
1. Full journey test (manual + scripted if time allows)
   - Submit offer-acceptance form -> profile created -> Cognito login works -> upload 3 documents -> all 4 workflow stages complete -> status shows `Day 1 ready`
2. Reminder logic test
   - Temporarily shorten the 24h threshold (e.g. to 2 min) and confirm reminder email fires correctly, then revert to 24h
3. Failure/edge case tests
   - Invalid document upload (wrong type, oversized)
   - Force a stage Lambda to throw — confirm Step Functions retry + Failed state behavior
   - Duplicate form submission for same email — confirm no duplicate `employee_id` created (add idempotency check if missing)
4. Load/concurrency sanity check
   - Simulate 5-10 concurrent onboarding flows (manually or via script) to sanity-check for race conditions in DynamoDB updates — informs the 50/month cost estimate in Phase 6
5. Capture artifacts for Phase 6
   - Step Functions execution history screenshots (success case + failure/retry case)
   - Record full journey for demo video

## Acceptance Criteria
- [ ] At least one clean, fully recorded end-to-end run (used for Phase 6 demo video)
- [ ] Reminder email confirmed working
- [ ] All edge cases tested with documented expected vs. actual behavior (short table in this file or a linked doc)
- [ ] No duplicate employee records possible from double-submission
