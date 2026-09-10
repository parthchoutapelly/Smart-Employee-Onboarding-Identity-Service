# Phase 3 — Document Collection

## Context
Feeds the `DocumentCollection` stage in Phase 2's state machine. Depends on: Phase 0 (`onboarding-documents-<env>` S3 bucket), Phase 1 (`employee_id`).

## Tasks
1. Upload mechanism
   - Frontend requests a pre-signed S3 PUT URL via API Gateway/Lambda (`onboarding-get-upload-url`)
   - New hire uploads directly to S3 using the pre-signed URL (ID proof, degree certificate, signed offer letter)
   - S3 key convention: `documents/{employee_id}/{document_type}.{ext}`
2. Lambda: `onboarding-validate-document` (S3 `ObjectCreated` trigger)
   - Validates file type (`pdf`, `jpg`, `png` only) and size (<10MB)
   - On invalid: delete object, update DynamoDB with `flagged` status + reason
   - On valid: update `onboarding_status.document_collection` progress (track per-document-type completion, not just one flag)
3. SNS topic: `onboarding-hr-notifications`
   - Publish message when ALL 3 required documents pass validation for an employee
   - HR admin subscribed via email (or Lambda subscriber feeding the dashboard)

## Technical Contracts

### API: `POST /documents/upload-url`
Request:
```json
{ "employee_id": "uuid", "document_type": "id_proof" | "degree_certificate" | "offer_letter", "file_extension": "pdf" }
```
Response `200`:
```json
{ "upload_url": "https://...", "s3_key": "documents/uuid/id_proof.pdf" }
```

### DynamoDB additions to `EmployeeProfile.onboarding_status`
```json
"documents": {
  "id_proof": "pending" | "uploaded" | "verified" | "rejected",
  "degree_certificate": "pending" | "uploaded" | "verified" | "rejected",
  "offer_letter": "pending" | "uploaded" | "verified" | "rejected"
}
```

### SNS message payload
```json
{ "employee_id": "uuid", "event": "all_documents_verified" }
```

## Acceptance Criteria
- [ ] New hire can request an upload URL and successfully upload all 3 document types
- [ ] Invalid file (wrong type or >10MB) is rejected and status reflects `rejected` with a reason
- [ ] SNS notification fires only once all 3 documents are `verified`
- [ ] Document Collection stage in Step Functions correctly reflects this status
