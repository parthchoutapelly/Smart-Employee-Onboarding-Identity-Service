# Phase 1 — Employee Record & Identity

## Context
Builds the canonical employee record. This is the identity spine — schema decisions here are consumed by every later phase and potentially other HRMS services. Depends on: Phase 0 (env, tables, buckets exist).

## Tasks
1. DynamoDB table: `EmployeeProfile`
2. Lambda: `onboarding-create-employee-profile`
   - Trigger: API Gateway `POST /employees` (on offer-acceptance form submission)
   - Validates input, generates `employee_id` (UUID v4), writes item to `EmployeeProfile`
   - Returns `{ employee_id, status }`
3. Lambda: `onboarding-provision-cognito-user`
   - Triggered after profile creation (direct call or EventBridge event)
   - Creates Cognito user in User Pool with temporary password
   - Sets custom attributes: `custom:employee_id`, `custom:role`
4. SES: send welcome email with login link + temp credentials
   - Template: "Welcome to [Company] — set up your account"
5. Cognito setup
   - User Pool with custom attributes: `employee_id`, `role`, `department`
   - App client for frontend auth (Phase 4)

## Technical Contracts

### DynamoDB Table: `EmployeeProfile`
| Attribute | Type | Notes |
|---|---|---|
| `employee_id` (PK) | String | UUID v4 |
| `name` | String | |
| `email` | String | |
| `department` | String | |
| `role` | String | |
| `manager` | String | manager's employee_id or name |
| `joining_date` | String | ISO 8601 date |
| `employment_type` | String | e.g. full-time / intern / contractor |
| `onboarding_status` | Map | `{ document_collection, it_provisioning, policy_signoff, manager_intro }` each: `pending` \| `in_progress` \| `complete` |
| `cognito_sub` | String | linked Cognito user ID |
| `created_at` | String | ISO 8601 timestamp |

### API: `POST /employees`
Request:
```json
{ "name": "", "email": "", "department": "", "role": "", "manager": "", "joining_date": "", "employment_type": "" }
```
Response `201`:
```json
{ "employee_id": "uuid", "status": "created" }
```

## Acceptance Criteria
- [ ] `POST /employees` creates a DynamoDB item with correct schema
- [ ] Cognito user is created with temp password and custom attributes set
- [ ] Welcome email is received with a working login link
- [ ] Draft ER diagram started for this table (finalized in Phase 6)
