# Smart Employee Onboarding & Identity Service

## Purpose
Fully automated digital onboarding system — offer acceptance to Day 1 readiness. Provisions accounts, collects documents, assigns equipment, sends scheduled welcome comms. This service creates the **canonical employee record** (`employee_id`) that other HRMS services (Leave Management, Document Vault, etc.) will reference.

## Architecture
```
[New Hire Form] --> API Gateway --> Lambda (createEmployeeProfile)
                                        |--> DynamoDB: EmployeeProfile
                                        |--> Cognito: create user
                                        |--> SES: send login link

[Step Functions: OnboardingStateMachine]
  DocumentCollection -> ITProvisioning -> PolicySignOff -> ManagerIntro
  each stage: Lambda handler + DynamoDB status update
  EventBridge: 24h no-progress -> reminder Lambda -> SES

[Document Upload] --> S3 (SSE) --> Lambda (validateDocument) --> DynamoDB status
                                        |--> SNS: notify HR when complete

[Frontend: S3 static hosting]
  /portal   -> New Hire Onboarding Portal (Cognito auth)
  /admin    -> HR Admin Dashboard

[API Gateway routes -> Lambda -> DynamoDB]
  GET /onboarding/{employee_id}/status
```

## Tech Stack
- **IaC Tool**: AWS SAM (`template.yaml` at repository root)
- **Compute**: AWS Lambda (Python 3.12, least-privilege IAM execution roles)
- **Database**: Amazon DynamoDB (Pay-Per-Request, Point-in-Time Recovery, SSE enabled)
- **Storage**: Amazon S3 (SSE-S3 encrypted documents bucket with versioning; separate static website hosting bucket)
- **Workflow & Orchestration**: AWS Step Functions & Amazon EventBridge
- **Auth & Messaging**: Amazon Cognito, Amazon SES, Amazon SNS, Amazon API Gateway
- **Frontend**: React + Vite (`/frontend/portal` and `/frontend/admin`)

---

## Naming Conventions
Strict naming conventions are enforced across all phases to align with prior HRMS services:

| Resource Type | Pattern | Example (`dev`) |
|---|---|---|
| **DynamoDB Tables** | `onboarding-<resource>-<stage>` | `onboarding-employee-profile-dev` |
| **S3 Documents Bucket** | `onboarding-documents-<stage>-<account_id>` | `onboarding-documents-dev-331262815638` |
| **S3 Frontend Bucket** | `onboarding-frontend-<stage>-<account_id>` | `onboarding-frontend-dev-331262815638` |
| **IAM Execution Roles** | `onboarding-<function>-role-<stage>` | `onboarding-placeholder-role-dev` |
| **Lambda Functions** | `onboarding-<action>-<stage>` | `onboarding-placeholder-dev` |

> **Note on S3 Global Namespace**: S3 bucket names include the AWS Account ID suffix (`-${AWS::AccountId}`) to guarantee global uniqueness while preserving the standard prefix `onboarding-<bucket>-<stage>`.

---

## Environment Strategy & Technical Contracts
- **Stage Parameter**: Managed through SAM template parameter `Stage` (defaults to `dev`, supports `staging` and `prod`).
- **Standard Injected Environment Variables**: Passed via IaC parameters/references to all Lambda functions (not hardcoded):
  - `STAGE`: Active deployment environment (e.g. `dev`).
  - `EMPLOYEE_TABLE_NAME`: Reference to the canonical DynamoDB table.
  - `DOCUMENTS_BUCKET_NAME`: Reference to the private documents S3 bucket.

---

## Repository Structure
```
├── template.yaml                  # Root AWS SAM template
├── README.md                      # Project documentation and conventions
├── .gitignore                     # Git ignore rules for SAM, Python, Node.js, frontend
├── backend/
│   ├── functions/
│   │   └── placeholder/           # Phase 0 placeholder lambda (health check / IaC verification)
│   │       ├── app.py
│   │       └── requirements.txt
│   └── statemachines/             # Step Functions ASL definitions
├── frontend/
│   ├── portal/                    # New Hire Onboarding Portal (React + Vite)
│   └── admin/                     # HR Admin Dashboard (React + Vite)
├── docs/                          # Architecture diagrams, ER diagrams, cost models
├── phase-0-setup.md               # Phase 0 task spec
└── phase-1-employee-identity.md ... phase-6-deliverables.md
```

---

## Build & Deployment

### 1. Prerequisites
- AWS CLI configured with active credentials (`ap-south-1` region)
- AWS SAM CLI installed (`sam --version >= 1.120`)
- Python 3.12+ and Node.js 20+

### 2. Validate SAM Template
```bash
sam validate --lint
```

### 3. Build Artifacts
```bash
sam build
```

### 4. Deploy Application
```bash
sam deploy --guided
```
When prompted during `--guided` setup:
- **Stack Name**: `onboarding-service-dev`
- **AWS Region**: `ap-south-1`
- **Parameter Stage**: `dev`
- **Confirm changes before deploy**: `Y`
- **Allow SAM CLI IAM role creation**: `Y`

---

## Phase 1 — Employee Record & Identity (Complete)

### API Contract: `POST /employees`
Endpoint created on Amazon API Gateway:
`POST https://{api-id}.execute-api.ap-south-1.amazonaws.com/{stage}/employees`

**Request Payload:**
```json
{
  "name": "Jane Doe",
  "email": "jane.doe@example.com",
  "department": "Engineering",
  "role": "Software Engineer",
  "manager": "Alex Manager",
  "joining_date": "2026-10-01",
  "employment_type": "full-time"
}
```

**Response (`201 Created`):**
```json
{
  "employee_id": "8d3e9112-c2e6-42f1-bd12-f7cb2f11ec4b",
  "status": "created"
}
```

### Sample `curl` Command:
```bash
curl -X POST "https://<API_ID>.execute-api.ap-south-1.amazonaws.com/dev/employees" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Doe",
    "email": "jane.doe@example.com",
    "department": "Engineering",
    "role": "Software Engineer",
    "manager": "Alex Manager",
    "joining_date": "2026-10-01",
    "employment_type": "full-time"
  }'
```

---

## Phase Index
- **Phase 0 — Project Setup & Environment** (Complete)
- **Phase 1 — Employee Record & Identity** (Complete)
- **Phase 2 — Onboarding Workflow Engine**
- **Phase 3 — Document Collection**
- **Phase 4 — Frontend**
- **Phase 5 — Testing & Integration**
- **Phase 6 — Deliverables & Documentation**

Each phase file is written as a self-contained task spec (context, tasks, technical contracts, acceptance criteria) so it can be handed to an automation agent one phase at a time.
