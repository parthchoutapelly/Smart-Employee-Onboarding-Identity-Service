# Phase 6 — Deliverables & Documentation

## Context
Final packaging phase. Depends on: Phase 5 complete (need a clean recorded run + tested edge cases).

## Tasks
1. Working onboarding flow write-up + Step Functions execution history screenshots (from Phase 5)
2. ER diagram of the DynamoDB employee schema
   - Show `EmployeeProfile` table, attribute types, and how `employee_id` is the join key other HRMS services (Leave Management, Document Vault) would reference
3. Video demo: full new-hire journey from form fill to Day 1 login (use the clean run recorded in Phase 5)
4. Cost estimate for 50 onboarding events/month
   - Break down per service:
     - Lambda: invocations x avg duration x memory
     - DynamoDB: read/write capacity or on-demand pricing for expected item counts
     - S3: storage (documents) + PUT/GET requests
     - Cognito: MAUs (50/month new users)
     - SES: emails sent (welcome + reminders, estimate ~3-5 per employee)
     - SNS: notifications published
     - Step Functions: state transitions (50 executions x ~6 transitions each)
     - API Gateway: request count
   - Use AWS Pricing Calculator, export as a table in `docs/cost-estimate.md`
5. Final README / architecture write-up (expand on the root README.md)
6. Resource cleanup
   - Tear down or clearly mark test-only resources before final submission

## Acceptance Criteria
- [ ] All 4 required deliverables complete: flow+screenshots, ER diagram, demo video, cost estimate
- [ ] Cost estimate broken down per AWS service with source (Pricing Calculator link or manual calc shown)
- [ ] Submission package reviewed by whole team before handoff
