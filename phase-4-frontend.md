# Phase 4 — Frontend

## Context
Two-view web app hosted on S3. Depends on: Phase 1 (Cognito), Phase 2 (progress API), Phase 3 (upload API).

## Tasks
1. New Hire Onboarding Portal (`/portal`)
   - Login via Cognito (App Client from Phase 1)
   - Document upload UI (calls `POST /documents/upload-url`, then direct S3 PUT)
   - Progress view: calls `GET /onboarding/{employee_id}/status`, renders a progress bar (4 stages)
2. HR Admin Dashboard (`/admin`)
   - Login (Cognito, admin role — gate via `custom:role` attribute)
   - Table/grid of all new hires with pipeline status
   - Color-coded status chips per stage: `pending` = gray, `in_progress` = amber, `complete` = green, `rejected/failed` = red
   - List view backed by a Lambda `onboarding-list-employees` (`GET /onboarding/pipeline`) that scans/queries `EmployeeProfile`
3. Hosting
   - Build static assets, deploy to `onboarding-frontend-<env>` S3 bucket (from Phase 0)
   - Enable static website hosting; optionally front with CloudFront (nice-to-have, not required for internship scope)

## Technical Contracts

### API: `GET /onboarding/pipeline` (HR admin only)
Response `200`:
```json
[
  { "employee_id": "uuid", "name": "", "department": "", "onboarding_status": { "...": "..." } }
]
```

### Frontend stack
React + Vite (consistent with Leave Management and Document Vault projects)

## Acceptance Criteria
- [ ] New hire can log in, upload all documents, and see live progress bar update across the 4 stages
- [ ] HR admin can log in and see all active onboarding pipelines with correct color-coded status
- [ ] Both views correctly call their respective APIs with proper auth (Cognito JWT passed to API Gateway)
