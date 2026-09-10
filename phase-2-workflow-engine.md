# Phase 2 — Onboarding Workflow Engine

## Context
Orchestrates the multi-stage onboarding checklist. Depends on: Phase 1 (`EmployeeProfile` table + `employee_id` must exist before a workflow execution starts).

## Tasks
1. Step Functions state machine: `onboarding-state-machine`
   - States (Sequential): `DocumentCollection` -> `ITProvisioning` -> `PolicySignOff` -> `ManagerIntro` -> `Complete`
   - Each state invokes a dedicated Lambda; on success, moves to next state; on failure, retries (3x, exponential backoff) then moves to a `Failed` state
2. Lambda per stage (4 total): each updates `onboarding_status.<stage>` in DynamoDB and returns pass/fail
3. Reminder mechanism
   - EventBridge rule (or Step Functions `Wait` + choice state) checks stage duration
   - If a stage has been `in_progress`/`pending` for >24h, Lambda `onboarding-send-reminder` fires SES email to the relevant party (new hire for docs, IT for provisioning, etc.)
4. Progress API
   - Lambda: `onboarding-get-status`
   - Route: `GET /onboarding/{employee_id}/status`
   - Reads `onboarding_status` map from DynamoDB, returns per-stage status

## Technical Contracts

### Step Functions Input (execution start)
```json
{ "employee_id": "uuid" }
```

### Per-stage Lambda contract
Input: `{ "employee_id": "uuid" }`
Output: `{ "employee_id": "uuid", "stage": "document_collection", "status": "complete" | "failed" }`

### API: `GET /onboarding/{employee_id}/status`
Response `200`:
```json
{
  "employee_id": "uuid",
  "onboarding_status": {
    "document_collection": "complete",
    "it_provisioning": "in_progress",
    "policy_signoff": "pending",
    "manager_intro": "pending"
  }
}
```

## Acceptance Criteria
- [ ] Step Functions execution runs all 4 stages end-to-end for a test employee_id, visible in console
- [ ] Failure in one stage triggers retry, then correctly lands in `Failed` state (test by forcing a Lambda error)
- [ ] Reminder email fires when a stage is incomplete past threshold (test with a shortened threshold, e.g. 1 min, before setting to 24h)
- [ ] `GET /onboarding/{employee_id}/status` returns accurate live status
