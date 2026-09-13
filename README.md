# Smart Employee Onboarding & Identity Service

[![AWS Region](https://img.shields.io/badge/AWS%20Region-ap--south--1%20(Mumbai)-orange.svg)](https://aws.amazon.com)
[![IaC](https://img.shields.io/badge/IaC-AWS%20SAM-red.svg)](https://aws.amazon.com/serverless/sam/)
[![Runtime](https://img.shields.io/badge/Runtime-Python%203.12-blue.svg)](https://www.python.org/)
[![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61dafb.svg)](https://react.dev/)
[![Tests](https://img.shields.io/badge/Tests-51%20Passed-brightgreen.svg)]()
[![Status](https://img.shields.io/badge/Deployment-dev%20(Complete)-success.svg)]()

A cloud-native, fully automated digital employee onboarding and identity provisioning service built on Amazon Web Services (AWS). The system orchestrates the complete journey from initial offer acceptance and HR registration through identity creation, secure document verification, IT provisioning, policy sign-off, and manager introduction—ensuring every new hire is **Day 1 Ready**.

---

## 1. Overview

### The Problem
Traditional employee onboarding is manual, fragmented, and error-prone. Human Resources, IT operations, and hiring managers frequently coordinate across disjointed spreadsheets, email chains, and disconnected tools. This leads to administrative delays, lost documents, unencrypted transmission of personally identifiable information (PII), delayed account provisioning, and new hires arriving on Day 1 without required equipment, system access, or verified compliance documentation.

### The Solution
The **Smart Employee Onboarding & Identity Service** is an enterprise-grade, serverless event-driven solution deployed in the `ap-south-1` (Mumbai) region. It eliminates manual friction by orchestrating all onboarding milestones through AWS Step Functions and AWS Lambda. Upon registration, the system automatically creates the canonical employee record, provisions corporate identity in Amazon Cognito, generates secure presigned upload channels for compliance documents, validates uploads via event-driven S3 triggers, and guides the candidate through IT provisioning and management introductions.

### Purpose & Integration Anchor
This service establishes the **canonical employee profile** (`employee_id`), which serves as the authoritative join key and identity anchor across downstream HRMS microservices—such as Leave Management, Payroll, Performance Tracking, and Document Vault.

### Target Users
- **New Hires / Employees**: Access the dedicated self-service Employee Portal to track their real-time onboarding milestones and securely upload verification documents directly from their browser.
- **HR Administrators / People Ops**: Utilize the HR Administration Dashboard to register new hires, monitor organization-wide onboarding pipelines, inspect document verification statuses, and receive automated lifecycle alerts.
- **IT Operations & Hiring Managers**: Benefit from automated workflow milestones that signal provisioning requirements and schedule manager introductions without manual HR intervention.

### Day 1 Readiness Goal
To ensure that prior to an employee's first official day, 100% of identity credentials are provisioned, compliance documents are validated, security policies are acknowledged, and team introductions are completed—with an end-to-end digital audit trail.

---

## 2. Key Features

- **Automated Employee Registration**: HR submits new hire details via the web dashboard or REST API (`POST /employees`), generating a unique UUIDv4 `employee_id` and canonical DynamoDB profile.
- **Cognito Identity Provisioning**: Automatically provisions corporate user identities in Amazon Cognito User Pool with temporary credentials, enforcing custom attributes (`custom:employee_id`, `custom:role`, `custom:department`).
- **Secure Document Collection**: Self-service employee portal collects mandatory onboarding documents (`id_proof`, `degree_certificate`, `offer_letter`).
- **Event-Driven Document Validation**: S3 `ObjectCreated` events trigger an asynchronous validation Lambda that inspects file types, extensions (`.pdf`, `.jpg`, `.png`), and enforces a strict file size ceiling (< 10 MB).
- **Automated Rejection Handling**: Non-compliant files are immediately deleted from S3, and the DynamoDB record is updated with specific rejection reasons for transparent candidate remediation.
- **Orchestrated Onboarding Workflow**: AWS Step Functions Standard State Machine manages the multi-stage lifecycle (`DocumentCollection` polling loop &rarr; `ITProvisioning` &rarr; `PolicySignOff` &rarr; `ManagerIntro` &rarr; `Complete`).
- **HR Pipeline Directory**: Real-time administrative pipeline (`GET /onboarding/pipeline`) backed by DynamoDB, enabling instant search, department filtering, and cross-stage progress monitoring.
- **Granular Status Tracking**: REST API (`GET /onboarding/{employee_id}/status`) delivers real-time stage milestones and document verification states to the frontend.
- **Automated Escalations & Reminders**: Amazon EventBridge daily rule triggers a reminder Lambda to identify pending stages exceeding 24 hours and dispatches email reminders via Amazon SES.
- **Transactional Notifications**: Amazon SES dispatches onboarding invitations and reminder alerts; an Amazon SNS topic (`onboarding-hr-notifications-dev`) alerts HR administrators the instant all documents are verified.
- **Secure Direct S3 Uploads**: Frontend uploads documents directly to private S3 storage using regional SigV4 presigned URLs (`POST /documents/upload-url`) with 15-minute expiration, eliminating server proxy overhead.
- **Zero-Trust Security & Auth**: Amazon Cognito JWT authorizer protects all API Gateway endpoints; least-privilege IAM execution roles isolate Lambda permissions; no AWS credentials exist in client code.
- **Infrastructure as Code (IaC)**: 100% declared and reproducible using AWS SAM (`template.yaml`), supporting parameterized, multi-stage deployments.

---

## 3. Architecture

The system employs a serverless, event-driven microservices architecture built on AWS managed services:

```
+---------------------------------------------------------------------------------------+
|                                  New Hire / HR Admin                                  |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                 React + Vite Frontend (Amazon S3 Static Website Hosting)              |
+---------------------------------------------------------------------------------------+
        |                                                              |
        v (Authenticate / Retrieve JWT)                                 v (Direct S3 Upload via Presigned URL)
+------------------------------------+                         +------------------------+
|   Amazon Cognito User Pool         |                         |  Private Documents S3  |
|   (Identity & JWT Auth)            |                         |  (SSE-S3, Versioning)  |
+------------------------------------+                         +------------------------+
        |                                                                  ^
        v (Bearer Token / JWT)                                             | (Upload Event)
+--------------------------------------------------------------------+     |
|          Amazon API Gateway Regional REST API                      |     |
|          (Cognito Authorizer, CORS Enabled)                        |     |
+--------------------------------------------------------------------+     |
        |                         |                         |              |
        | POST /employees         | GET /status & /pipeline | POST /upload-url
        v                         v                         v              |
+------------------+      +------------------+      +------------------+   |
| createEmployee   |      | getStatus /      |      | getUploadUrl     |---+ (Generates SigV4 URL)
| Profile Lambda   |      | listEmployees    |      | Lambda           |
+------------------+      +------------------+      +------------------+
        |        |                 |
        |        |                 |
        |        v                 v
        |  +---------------------------------------------------+
        |  |        Amazon DynamoDB: EmployeeProfile           |
        |  |        (Canonical Record, Primary Key: employee_id)|<----------+
        |  +---------------------------------------------------+           |
        |                                                                  |
        v (Starts Execution)                                               |
+--------------------------------------------------------------------+     |
|              AWS Step Functions Standard State Machine             |     |
|                                                                    |     |
|  [DocumentCollection]                                              |     |
|          | (marks in_progress)                                     |     |
|          v                                                         |     |
|  [CheckDocumentCollection] <----+ (30s Polling Loop)               |     |
|          |                      |                                  |     |
|          v                      |                                  |     |
|  <All 3 Docs Verified?> --No--> [WaitForDocuments]                 |     |
|          |                                                         |     |
|         Yes                                                        |     |
|          v                                                         |     |
|  [ITProvisioning] (Lambda)                                         |     |
|          v                                                         |     |
|  [PolicySignOff] (Lambda)                                          |     |
|          v                                                         |     |
|  [ManagerIntro] (Lambda)                                           |     |
|          v                                                         |     |
|  [Complete] (Day 1 Ready!)                                         |     |
+--------------------------------------------------------------------+     |
                                                                           |
                                                                           |
+-------------------------------------------------------------+            |
|       S3 ObjectCreated Event Driven Validation Pipeline     |            |
|                                                             |            |
|  Private S3 Upload Event                                    |            |
|          |                                                  |            |
|          v                                                  |            |
|  validateDocument Lambda                                    |            |
|    (Enforces size < 10MB, allowed types & extensions)       |            |
|          |                                                  |            |
|          +-----> Updates Verified/Rejected Status ----------+------------+
|          |
|          +-----> When all 3 verified -> Publishes Event
|                                                   |
|                                                   v
|                                          Amazon SNS Topic
|                                          (HR Notification)
+-------------------------------------------------------------+

+-------------------------------------------------------------+
|         Scheduled Background Reminders Pipeline             |
|                                                             |
|  Amazon EventBridge (Daily Schedule: rate(1 day))           |
|          |                                                  |
|          v                                                  |
|  sendReminderEmail Lambda (Scans pending stages > 24 hrs)   |
|          |                                                  |
|          v                                                  |
|  Amazon SES (Dispatches Transactional Reminder Emails)      |
+-------------------------------------------------------------+
```

---

## 4. AWS Services

The architecture strictly uses AWS serverless managed services to deliver high availability, automatic scaling, and zero idle operational overhead:

| Service | Purpose in Architecture |
|---|---|
| **Amazon S3** | Encrypted private storage for onboarding documents (`SSE-S3`, versioning enabled) and static website hosting for the React frontend application. |
| **Amazon API Gateway** | Regional REST API exposing protected operational routes with Cognito User Pool authorizers, CORS support, and custom gateway error responses. |
| **AWS Lambda** | Serverless compute running Python 3.12 microservices for employee creation, status tracking, presigned URL generation, document validation, and Step Functions stage tasks. |
| **Amazon DynamoDB** | Single-table NoSQL database hosting the canonical `EmployeeProfile` table with Pay-Per-Request billing, Point-in-Time Recovery (PITR), and encryption at rest. |
| **Amazon Cognito** | User directory and authentication service managing user pools, temporary passwords, JWT issuance, and custom employee identity claims. |
| **AWS Step Functions** | Standard State Machine orchestrating the sequential onboarding workflow, asynchronous polling loops, retries, and failure catch blocks. |
| **Amazon SES** | Transactional email delivery service dispatching new hire welcome invitations, login credentials, and stage reminder notifications. |
| **Amazon SNS** | Pub/Sub notification topic (`onboarding-hr-notifications-dev`) publishing real-time administrative alerts upon document verification completion. |
| **Amazon EventBridge** | Cloud-native event scheduler running a daily rule (`rate(1 day)`) to trigger the stage reminder scanning Lambda. |
| **AWS IAM** | Granular, least-privilege execution roles attached to individual Lambda functions and the Step Functions state machine. |
| **AWS SAM** | Infrastructure as Code (IaC) framework used to declare, build, validate, package, and deploy all cloud resources via CloudFormation. |

---

## 5. End-to-End Workflow

The complete end-to-end lifecycle follows 17 deterministic steps:

1. **HR Submits Employee Information**: HR enters employee profile data (name, email, department, role, manager, joining date, employment type) through the HR Admin Dashboard or directly via `POST /employees`.
2. **EmployeeProfile Created**: `onboarding-create-employee-profile-dev` generates a UUIDv4 `employee_id` and writes the canonical profile item to the DynamoDB `EmployeeProfile` table with all stages set to `pending`.
3. **Cognito User Provisioned**: The Lambda calls `AdminCreateUser` on the Amazon Cognito User Pool (`ap-south-1_LDOpZYY1U`), assigning custom attributes (`custom:employee_id`, `custom:role`, `custom:department`) and a secure temporary password.
4. **Welcome Communication Sent**: Amazon SES sends an automated welcome email containing the employee's portal URL and initial sign-in credentials.
5. **Step Functions Execution Starts**: `onboarding-create-employee-profile-dev` initiates the AWS Step Functions Standard State Machine (`onboarding-state-machine-dev`), passing `{"employee_id": "<uuid>"}`.
6. **DocumentCollection Enters `in_progress`**: The state machine invokes `stageDocumentCollection`, transitioning `onboarding_status.document_collection` from `pending` to `in_progress`.
7. **Employee Requests Presigned Upload URL**: The new hire signs into the Employee Portal and selects a document to upload (`id_proof`, `degree_certificate`, or `offer_letter`). The client calls `POST /documents/upload-url` with the document type and extension.
8. **Document Uploaded Directly to Private S3**: `onboarding-get-upload-url-dev` generates an S3 SigV4 virtual-hosted presigned PUT URL (15-minute TTL). The browser transmits the file directly to `onboarding-documents-dev-331262815638` with the proper `Content-Type`.
9. **S3 Event Triggers Validation Lambda**: S3 fires an `s3:ObjectCreated:*` notification for the prefix `documents/`, invoking `onboarding-validate-document-dev`.
10. **Document Status Becomes Verified or Rejected**: The Lambda inspects file key format, validates extension (`pdf`, `jpg`, `png`), and checks file size (< 10 MB):
    - *If invalid*: The offending S3 object is immediately deleted, and the document is marked `rejected` with an explanatory reason.
    - *If valid*: The document is marked `verified` with an ISO-8601 timestamp in DynamoDB.
11. **All Three Documents Verified**: Once `id_proof`, `degree_certificate`, and `offer_letter` all have status `verified`, the validation Lambda atomically marks `onboarding_status.document_collection = complete`.
12. **DocumentCollection Completes & SNS Alerts HR**: The validation Lambda publishes an `all_documents_verified` alert to the SNS topic `onboarding-hr-notifications-dev`. Meanwhile, Step Functions' polling loop (`CheckDocumentCollection` &rarr; `WaitForDocuments`) detects `document_collection == complete` and exits the wait loop.
13. **IT Provisioning**: Step Functions advances to `ITProvisioning`, executing `onboarding-stage-it-provisioning-dev`, which provisions system access/equipment records and updates status to `complete`.
14. **Policy Sign-Off**: Step Functions invokes `onboarding-stage-policy-signoff-dev`, simulating company compliance acknowledgment and setting status to `complete`.
15. **Manager Intro**: Step Functions executes `onboarding-stage-manager-intro-dev`, scheduling manager introductions and updating status to `complete`.
16. **Onboarding Reaches Final Completed State**: Step Functions transitions to `Complete`. The execution status reaches `SUCCEEDED`. The employee is officially **Day 1 Ready**.
17. **HR Pipeline Directory Reflects Current Status**: HR views the real-time pipeline via `GET /onboarding/pipeline`. The directory reflects all 4 stages as `complete` with verified document indicators.

---

## 6. Data Model

The data layer uses a single canonical DynamoDB table designed for high throughput and consistent atomic updates:

- **Full Data Model Specification**: [`docs/data-model.md`](docs/data-model.md)
- **Authoritative ER Diagram**: [`docs/employee-profile-er-diagram.png`](docs/employee-profile-er-diagram.png)

```
+---------------------------------------------------------------------------------------------------+
|                                  DynamoDB: EmployeeProfile                                        |
|                          (Table: onboarding-employee-profile-dev)                                 |
+---------------------------------------------------------------------------------------------------+
|  PK (Partition Key): employee_id (String, UUIDv4)                                                 |
+---------------------------------------------------------------------------------------------------+
|  cognito_sub       : String       (Cognito User Directory Subject UUID)                           |
|  name              : String       (Full Name)                                                     |
|  email             : String       (Corporate / Personal Email Address)                            |
|  department        : String       (Engineering, Product, People Ops, Marketing, Finance)          |
|  role              : String       (Job Title)                                                     |
|  employment_type   : String       (Full-time, Contract, Part-time)                                |
|  joining_date      : String       (YYYY-MM-DD)                                                    |
|  manager           : String       (Manager Name / Identifier)                                     |
|  created_at        : String       (ISO-8601 Timestamp)                                            |
|  onboarding_status : Map                                                                          |
|    |-- document_collection : String ("pending" | "in_progress" | "complete")                      |
|    |-- it_provisioning     : String ("pending" | "in_progress" | "complete")                      |
|    |-- policy_signoff      : String ("pending" | "in_progress" | "complete")                      |
|    |-- manager_intro       : String ("pending" | "in_progress" | "complete")                      |
|    \-- documents           : Map                                                                  |
|          |-- id_proof           : Map { status, s3_key, uploaded_at, verified_at, rejection_reason }
|          |-- degree_certificate : Map { status, s3_key, uploaded_at, verified_at, rejection_reason }
|          \-- offer_letter       : Map { status, s3_key, uploaded_at, verified_at, rejection_reason }
+---------------------------------------------------------------------------------------------------+
```

### Key Schema Characteristics
1. **Single Canonical Table**: No separate `Document`, `AuditLog`, or `Task` tables are created. All onboarding state, sub-stages, and document metadata are maintained inside the canonical `EmployeeProfile` record, guaranteeing atomic updates and eliminating multi-table synchronization overhead.
2. **Primary Key**: `employee_id` (String UUIDv4) serves as the primary partition key.
3. **Cross-HRMS Integration Key**: `employee_id` is the permanent identifier exported to and referenced by downstream HRMS services (Leave Management, Payroll, Document Vault, Performance).
4. **Nested Document Maps**: Each document slot tracks verification state (`uploaded`, `verified`, or `rejected`), direct S3 key paths, timestamps, and error messages.

---

## 7. API Endpoints

The API is deployed as an Amazon API Gateway Regional REST API in `ap-south-1`. All production endpoints are secured with an Amazon Cognito User Pool Authorizer:

**Base URL**: `https://5goe29bglh.execute-api.ap-south-1.amazonaws.com/dev`

| Method | Resource Path | Auth Required | Description |
|---|---|---|---|
| `POST` | `/employees` | **Yes** (Cognito JWT) | Registers a new employee, creates the canonical DynamoDB profile, provisions Cognito identity, and starts the Step Functions onboarding state machine. |
| `GET` | `/onboarding/{employee_id}/status` | **Yes** (Cognito JWT) | Retrieves real-time stage statuses (`document_collection`, `it_provisioning`, `policy_signoff`, `manager_intro`) and document verification metadata for an employee. |
| `POST` | `/documents/upload-url` | **Yes** (Cognito JWT) | Validates document type and file extension, returning a regional SigV4 virtual-hosted presigned S3 PUT URL with a 15-minute expiration. |
| `GET` | `/onboarding/pipeline` | **Yes** (Cognito JWT) | Performs an administrative scan of the `EmployeeProfile` table, returning all employee records and stage statuses for the HR Pipeline Directory. |

### API Gateway GatewayResponses & CORS
The API Gateway configuration defines explicit `GatewayResponses` for `UNAUTHORIZED` (HTTP 401) and `DEFAULT_4XX` (HTTP 4xx), injecting standard CORS headers (`Access-Control-Allow-Origin: '*'`, `Access-Control-Allow-Headers: '*'`). This guarantees that authentication failures or invalid requests surface cleanly to browser clients without being obscured by browser CORS errors.

> **Security Note**: All requests require an active Cognito User Pool token passed via the `Authorization: <token>` header. No passwords, tokens, presigned URLs, or secrets are exposed or logged.

---

## 8. Security

The service implements a defense-in-depth security model adhering to the AWS Well-Architected Security Pillar:

- **Cognito User Pool Authentication**: Authentication is enforced via an Amazon Cognito User Pool (`ap-south-1_LDOpZYY1U`). Passwords require uppercase, lowercase, numbers, symbols, and a minimum length of 8 characters. Temporary passwords force confirmation on first login.
- **API Gateway Authorizer**: All REST endpoints are guarded by a Cognito User Pool authorizer (`CognitoAuthorizer`). Unauthenticated requests are rejected at the API edge with HTTP 401 before compute is invoked.
- **Private S3 Storage**: The document storage bucket (`onboarding-documents-dev-331262815638`) has AWS S3 Block Public Access fully enabled (`BlockPublicAcls`, `IgnorePublicAcls`, `BlockPublicPolicy`, `RestrictPublicBuckets`).
- **Server-Side Encryption (SSE-S3)**: All document objects stored in S3 are encrypted at rest using 256-bit Advanced Encryption Standard (`AES256`).
- **Bucket Versioning**: S3 versioning is enabled on the documents bucket to prevent accidental overwrite or loss and provide an immutable audit trail of document updates.
- **TLS-Only Bucket Policy**: S3 bucket policies enforce encrypted transport in transit (`aws:SecureTransport: true`), denying any plain HTTP requests.
- **SigV4 Presigned Upload URLs**: Documents are transferred directly from the user's browser to S3 via presigned PUT URLs signed with regional SigV4 credentials and restricted to a 15-minute TTL. No file contents traverse Lambda or API Gateway.
- **Least-Privilege IAM Roles**: Every Lambda function has an independent IAM execution role with resource-scoped policies:
  - `CreateEmployeeProfile`: Restricted to `dynamodb:PutItem`, `states:StartExecution`, and `cognito-idp:AdminCreateUser`.
  - `GetUploadUrl`: Restricted to `s3:PutObject` on `documents/*`.
  - `ValidateDocument`: Restricted to `s3:GetObject` and `s3:DeleteObject` on `documents/*`, `dynamodb:UpdateItem` on the employee table, and `sns:Publish` on the HR notification topic.
  - `ListOnboardingEmployees`: Restricted to `dynamodb:Scan` on the employee table.
- **No Client-Side Credentials**: No AWS access keys, secret keys, or administrative tokens are bundled into the React frontend. The application relies exclusively on ephemeral Cognito session tokens.
- **Infrastructure Injected Config**: Service endpoints, bucket names, and table names are dynamically injected via CloudFormation references at deployment time.

---

## 9. Reliability & Error Handling

- **Step Functions Retries & Exponential Backoff**: Each workflow task state is configured with automated retry rules for transient service errors (`Lambda.ServiceException`, `Lambda.AWSLambdaException`, `Lambda.SdkClientException`). Retries execute up to 3 times with an initial 2-second interval and a 2.0 backoff rate.
- **Graceful State Machine Catching**: All workflow stages implement fallback `Catch` clauses that capture unhandled errors and route them to a `Failed` terminal state, preventing workflows from hanging indefinitely.
- **Asynchronous Polling Loop**: The state machine avoids race conditions by entering a non-blocking polling loop (`CheckDocumentCollection` &rarr; `WaitForDocuments` with 30-second backoff) until DynamoDB confirms all required documents are verified.
- **Strict Document Validation & Auto-Remediation**: The `validateDocument` handler enforces size (< 10 MB) and format constraints. Invalid uploads are purged immediately from S3, preventing storage pollution, and detailed error messages are written to DynamoDB.
- **DynamoDB Exception Handling**: All Lambda handlers wrap DynamoDB interactions in structured `try/except` blocks handling `ClientError` and `ProvisionedThroughputExceededException`, returning standardized HTTP error payloads.
- **Daily EventBridge Escalation**: The `onboarding-send-reminder-dev` scheduled rule runs once every 24 hours to identify stalled stages, dispatching proactive SES reminders to prevent onboarding bottlenecks.
- **Frontend Error Boundaries**: The React application features token validation guards, session refresh handling, and explicit authentication error states.

---

## 10. Testing & Validation

The service has been validated across all development phases using automated unit tests, integration test suites, and live cloud deployment checks:

### Automated Test Suite
- **Unit & Integration Tests**: **51 tests passed** (`51 passed in 0.014s`) using Python's `unittest` framework across all modules:
  - Phase 1 tests (`tests/test_phase1.py`): Profile creation, validation, Cognito provisioning.
  - Phase 2 tests (`tests/test_phase2.py`): Step Functions triggers, stage transitions, polling logic.
  - Phase 3 tests (`tests/test_phase3.py`): Presigned URL generation, file size enforcement (< 10 MB), format checking, auto-deletion of invalid uploads, SNS completion events (30/30 tests passed at Phase 3 milestone).
  - Phase 5 tests (`tests/test_phase5.py`): End-to-end integration, CORS preflight, error handling.
  - Pipeline tests (`tests/test_list_pipeline.py`): Pipeline directory querying, scanning, and format validation.

```bash
$ python3 -m unittest discover tests
...................................................
----------------------------------------------------------------------
Ran 51 tests in 0.014s

OK
```

### Cloud & Infrastructure Validation
- **SAM Template Linting**: `sam validate --lint` executed cleanly with zero template errors or warnings.
- **SAM Build**: `sam build` successfully compiled all 13 Python 3.12 Lambda functions.
- **Frontend Build**: `npm run build` compiled clean production assets with zero bundling errors.
- **CloudFormation Status**: Stack `onboarding-service-dev` reached `CREATE_COMPLETE` and subsequently `UPDATE_COMPLETE` across iterative deployments.
- **API Security Verification**: Unauthenticated calls to `/employees`, `/onboarding/pipeline`, `/onboarding/{id}/status`, and `/documents/upload-url` confirmed returning HTTP 401 Unauthorized.
- **S3 Presigned Uploads**: Regional SigV4 PUT uploads verified returning HTTP 200 OK.
- **Live End-to-End Orchestration**: Verified live execution where test employee `7037b507-00c9-4ccf-b6a9-6598b30c609e` uploaded all three documents, Step Functions execution `bb791e48-a436-4ada-bd4c-3d2d7e3303fc` progressed through polling to `SUCCEEDED`, and all four onboarding stages reached `complete`.

---

## 11. Phase 6 Evidence

Detailed evidence, architecture specifications, and verification traces generated during Phase 6 are maintained in the repository:

- **[Working Onboarding Flow](docs/working-onboarding-flow.md)**: Authoritative end-to-end trace of the verified onboarding lifecycle, AWS execution ARNs, and state machine transitions.
- **[Data Model Specification](docs/data-model.md)**: Exhaustive documentation of the `EmployeeProfile` DynamoDB table, attribute schemas, and cross-HRMS integration keys.
- **[EmployeeProfile ER Diagram](docs/employee-profile-er-diagram.png)**: Visual entity-relationship diagram illustrating table structures and downstream service relationships.
- **[Cost Estimate Model](docs/cost-estimate.md)**: In-depth financial analysis and operational cost breakdown for 50 onboarding events/month.

> **Note**: The comprehensive live demonstration video covering HR registration, employee login, document upload, automated verification, and pipeline monitoring was recorded separately for internship submission and evaluator review.

---

## 12. Cost Estimate

A detailed cost model for **50 onboarding events per month** is documented in [`docs/cost-estimate.md`](docs/cost-estimate.md).

### Summary for 50 Onboardings / Month:
- **Expected Monthly Volume**:
  - 50 new hire onboarding lifecycles
  - 150 document uploads (approx. 450 MB total storage per month)
  - 50 Step Functions Standard workflow executions
  - ~1,500 AWS Lambda invocations (~30 per candidate)
  - ~1,750 DynamoDB read/write request units
  - ~150 transactional SES emails and SNS alerts
- **Under AWS Free Tier**: **$0.00 / month** (all monthly usage falls completely within the AWS Free Tier allowances for Lambda, DynamoDB, S3, Cognito, and Step Functions).
- **List Price Without Free Tier**: **~$0.043 / month** (equivalent to **~$0.00086 per employee onboarding**).
- **Effective Monthly Cost (With Year-over-Year S3 Document Accumulation)**: **~$0.020 / month**.

For complete mathematical breakdowns, price-per-service calculations, and enterprise scaling projections (up to 1,000 onboardings/month), consult [`docs/cost-estimate.md`](docs/cost-estimate.md).

---

## 13. Deployment

The service is fully declared in AWS SAM (`template.yaml`) and deploys to AWS using standard SAM CLI tooling:

### 1. Prerequisites
- AWS CLI configured with active credentials (`ap-south-1` region)
- AWS SAM CLI installed (`sam --version >= 1.120`)
- Python 3.12 and Node.js 20+

### 2. Validate SAM Template
```bash
sam validate --lint
```

### 3. Build Serverless Artifacts
```bash
sam build
```

### 4. Deploy Infrastructure
For initial guided deployment:
```bash
sam deploy --guided
```
Or for subsequent deployments using settings stored in `samconfig.toml`:
```bash
sam deploy
```

Configuration parameters used in `dev`:
- **Stack Name**: `onboarding-service-dev`
- **AWS Region**: `ap-south-1`
- **Parameter Stage**: `dev`

### 5. Build & Deploy Frontend (Optional)
```bash
cd frontend
npm install
npm run build
aws s3 sync dist/ s3://onboarding-frontend-dev-<ACCOUNT_ID>/ --delete
```

---

## 14. Repository Structure

```
.
├── README.md                      # Authoritative project documentation & architecture write-up
├── template.yaml                  # Root AWS SAM template (IaC declaring all resources)
├── samconfig.toml                 # SAM deployment configuration (dev stage, ap-south-1)
├── .gitignore                     # Git ignore rules for Python, SAM, Node.js, and env files
├── backend/                       # Serverless backend implementation
│   ├── functions/                 # Python 3.12 Lambda microservices
│   │   ├── checkDocumentCollection/   # Polls DynamoDB status for Step Functions loop
│   │   ├── createEmployeeProfile/     # POST /employees handler, kicks off Step Functions
│   │   ├── getOnboardingStatus/       # GET /onboarding/{id}/status handler
│   │   ├── getUploadUrl/              # POST /documents/upload-url presigned URL generator
│   │   ├── listOnboardingEmployees/   # GET /onboarding/pipeline HR pipeline scan handler
│   │   ├── placeholder/               # Phase 0 verification & health check function
│   │   ├── provisionCognitoUser/      # Provisions Cognito user & triggers welcome email
│   │   ├── sendReminderEmail/         # EventBridge daily scheduled reminder processor
│   │   ├── stageDocumentCollection/   # Marks document collection stage in_progress
│   │   ├── stageITProvisioning/       # IT provisioning workflow stage handler
│   │   ├── stageManagerIntro/         # Manager introduction workflow stage handler
│   │   ├── stagePolicySignOff/        # Policy sign-off workflow stage handler
│   │   └── validateDocument/          # S3 event-driven validation for uploaded documents
│   └── statemachines/             # Step Functions ASL definitions
│       └── onboarding-state-machine.asl.json # 4-stage state machine definition
├── frontend/                      # React + Vite Single Page Application (SPA)
│   ├── index.html                 # Main HTML entry point
│   ├── package.json               # Node.js dependencies & scripts
│   ├── vite.config.js             # Vite bundler configuration
│   └── src/                       # Frontend application source code
│       ├── App.jsx                # Router & main application shell
│       ├── main.jsx               # React DOM entry point
│       ├── auth/                  # AWS Amplify / Cognito authentication session helpers
│       ├── components/            # Reusable UI components (Navbar, ProtectedRoute, etc.)
│       ├── pages/                 # Portal views (EmployeePortal, AdminPage, Login, etc.)
│       ├── services/              # API client & S3 direct upload service
│       └── styles/                # Vanilla CSS design system
├── docs/                          # Phase 6 architecture, data model, & evidence documentation
│   ├── cost-estimate.md           # Phase 6 Deliverable 4: 50 onboarding/month cost model
│   ├── data-model.md              # Phase 6 Deliverable 2: DynamoDB schema & ER specification
│   ├── employee-profile-er-diagram.png # Phase 6 Deliverable 2: Visual ER diagram
│   └── working-onboarding-flow.md # Phase 6 Deliverable 1: Verified end-to-end lifecycle
└── tests/                         # Automated unit and integration test suite (51 tests)
    ├── test_phase1.py             # Profile creation & identity tests
    ├── test_phase2.py             # Step Functions & stage transition tests
    ├── test_phase3.py             # Presigned URLs, validation & SNS tests
    ├── test_phase5.py             # Integration, CORS, & error handling tests
    └── test_list_pipeline.py      # HR Pipeline scan API tests
```

---

## 15. Naming Conventions

The project enforces strict, standardized naming conventions across all AWS resources to maintain consistency with enterprise HRMS standards:

| Resource Type | Naming Convention Pattern | Active `dev` Example |
|---|---|---|
| **DynamoDB Tables** | `onboarding-<resource>-<stage>` | `onboarding-employee-profile-dev` |
| **S3 Documents Bucket** | `onboarding-documents-<stage>-<account_id>` | `onboarding-documents-dev-331262815638` |
| **S3 Frontend Bucket** | `onboarding-frontend-<stage>-<account_id>` | `onboarding-frontend-dev-331262815638` |
| **Lambda Functions** | `onboarding-<action>-<stage>` | `onboarding-create-employee-profile-dev` |
| **IAM Execution Roles** | `onboarding-<action>-role-<stage>` | `onboarding-create-employee-profile-role-dev` |
| **Step Functions** | `onboarding-state-machine-<stage>` | `onboarding-state-machine-dev` |
| **SNS Topics** | `onboarding-hr-notifications-<stage>` | `onboarding-hr-notifications-dev` |

*Note: S3 bucket names append the AWS Account ID (`-${AWS::AccountId}`) to satisfy global uniqueness requirements while preserving predictable prefix naming.*

---

## 16. Project Status

| Phase | Description | Status |
|---|---|---|
| **Phase 0** | Project Setup, Git Repository, SAM Initialization, & IaC Foundation | ✅ **Complete** |
| **Phase 1** | Employee Record Creation, DynamoDB Schema, & Cognito Identity | ✅ **Complete** |
| **Phase 2** | Step Functions Workflow Engine, Stage Handlers, & Polling Loop | ✅ **Complete** |
| **Phase 3** | Secure S3 Document Collection, Event-Driven Validation, & SNS Alerts | ✅ **Complete** |
| **Phase 4** | React + Vite Frontend Application (Employee Portal & HR Dashboard) | ✅ **Complete** |
| **Phase 5** | System Integration, API Security, CORS Alignment, & Automated Testing | ✅ **Complete** |
| **Phase 6** | Documentation, Architecture Write-up, Data Models, & Final Packaging | 🟡 **Final Documentation / Packaging** |

**Deployment Verification**: The active development environment (`dev`) in `ap-south-1` has been validated end-to-end across all functional requirements, security boundaries, asynchronous polling loops, S3 event triggers, and authenticated frontend portals.

---

## 17. Future Enhancements

The following architectural enhancements are planned as future iterations beyond the current internship scope:

- **Multi-Environment CI/CD Automation**: Implement GitHub Actions or AWS CodePipeline pipelines with automated testing, linting, and automated promotion across `dev`, `staging`, and `prod` environments.
- **Granular Role-Based Access Control (RBAC)**: Expand Cognito User Pool Groups (`HR_Admin`, `IT_Staff`, `Department_Manager`, `Employee`) with API Gateway route-level IAM/OAuth scoping to restrict endpoint access based on enterprise roles.
- **CloudFront CDN & Custom Domain Names**: Place Amazon CloudFront in front of the S3 frontend bucket and API Gateway with AWS WAF protection, automated SSL/TLS certificates via AWS Certificate Manager (ACM), and custom domain routing via Route 53.
- **Enterprise HRMS Event Integrations**: Connect Step Functions completion events to Amazon EventBridge custom event buses to trigger downstream microservices (automated leave balance provisioning, payroll setup, and badge printing).
- **Real-Time WebSocket Updates**: Integrate AWS API Gateway WebSocket APIs to push live document verification and stage progression events to the Employee Portal, replacing client polling.
- **Automated Document OCR & Verification**: Integrate Amazon Textract within the `validateDocument` Lambda to automatically parse and verify the authenticity of uploaded government IDs and certificates against applicant profile records.
