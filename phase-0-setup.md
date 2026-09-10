# Phase 0 — Project Setup & Environment

## Context
Foundation phase. Nothing in Phase 1+ should be built before this is done. Reuse conventions from prior HRMS projects (Leave Management, Document Vault) where possible.

## Tasks
1. Confirm/create AWS environment
   - Reuse shared AWS account if available; otherwise create one
   - IAM: create least-privilege execution roles per Lambda function (do not use one shared admin role)
2. Repo setup
   - Initialize repo with structure from README.md
   - Add `.gitignore`, `README.md`, branch protection on `main`
3. IaC tooling
   - AWS SAM (consistent with prior projects)
   - Scaffold a minimal SAM `template.yaml` with one placeholder Lambda + DynamoDB table to prove deploy works
4. Naming convention (lock this in — used in every later phase)
   - Resources: `onboarding-<resource>-<env>` e.g. `onboarding-employee-profile-dev`
   - Lambda functions: `onboarding-<action>` e.g. `onboarding-create-employee-profile`
5. S3 buckets
   - `onboarding-documents-<env>` — private, SSE-S3 enabled, versioning on
   - `onboarding-frontend-<env>` — static website hosting enabled
6. Environment strategy
   - Single `dev` environment is fine for internship scope; structure IaC so `staging`/`prod` could be added later via a stage parameter

## Technical Contracts
- IaC tool: AWS SAM
- AWS region: `<DECIDE>`
- Env var convention: `STAGE`, `EMPLOYEE_TABLE_NAME`, `DOCUMENTS_BUCKET_NAME` passed to all Lambdas via IaC, not hardcoded

## Acceptance Criteria
- [ ] `sam build && sam deploy` deploys a placeholder Lambda + DynamoDB table successfully
- [ ] Repo pushed with agreed folder structure
- [ ] Naming convention documented in README
- [ ] Both S3 buckets created with correct settings
