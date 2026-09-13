# AWS Cost Estimate — 50 Onboarding Events/Month

## 1. Scope

This document provides an authoritative, transparent cost analysis for operating the **Smart Employee Onboarding & Identity Service** in the **AWS Asia Pacific (Mumbai) region (`ap-south-1`)**.

The model estimates the total monthly operating cost for a steady-state workload of **50 new employee onboarding events per month** running on the deployed serverless architecture (`onboarding-service-dev`).

All calculations reflect the actual deployed resource configuration in `template.yaml`, including:
- Pay-Per-Request (On-Demand) Amazon DynamoDB with Point-in-Time Recovery (PITR)
- AWS Lambda functions running on Python 3.12 (256 MB allocated memory)
- Amazon S3 Private Document Storage with SSE-S3 (`AES256`) and bucket versioning
- AWS Step Functions Standard State Machine workflow orchestration
- Amazon API Gateway Regional REST API with Amazon Cognito User Pools authorization
- Amazon SES outbound onboarding communications and Amazon SNS HR completion alerts

---

## 2. Architecture and Usage Assumptions

The baseline usage model is derived directly from the application workflow:

| Parameter | Value | Operational Context |
|---|---|---|
| **Monthly Onboarding Events** | **50 employees/month** | Target monthly new-hire volume |
| **Documents per Employee** | **3 documents** | Government ID Proof, Degree Certificate, Signed Offer Letter |
| **Total Uploads per Month** | **150 files/month** | 50 employees $\times$ 3 required documents |
| **Average Document Size** | **2.0 MB / file** | Standard multi-page PDF or JPEG/PNG scan (limit: $< 10\text{ MB}$) |
| **Monthly S3 Storage Ingestion** | **300 MB / month** | 150 files $\times$ 2.0 MB ($0.293\text{ GB/month}$) |
| **SES Outbound Emails** | **~4 emails / employee (200 total)** | Account invite, document reminders, milestone completions |
| **SNS Completion Alerts** | **50 notifications/month** | 1 notification published per completed 4-stage onboarding |
| **Step Functions Executions** | **50 executions/month** | 1 state machine execution per registered employee |
| **State Transitions / Execution** | **~6 to 10 transitions** | 4 linear stages + document verification polling loop |
| **Total State Transitions** | **~300 to 500 transitions/month** | 50 executions $\times$ ~6–10 transitions |
| **API Gateway Requests** | **~400 to 500 requests/month** | Profile creation, upload URLs, status queries, pipeline scans |
| **Lambda Memory Allocation** | **256 MB** | Actual deployed configuration (`Globals.Function.MemorySize: 256`) |
| **Lambda Average Duration** | **300 ms (0.30 seconds)** | Conservative estimate for DynamoDB/S3 micro-operations |
| **AWS Region** | **`ap-south-1` (Mumbai)** | Deployed region |

---

## 3. Cost Breakdown by Service

### 3.1 AWS Lambda

Each onboarding event triggers a sequence of micro-operations across the lifecycle:
- `createEmployeeProfile`: 1 invocation
- `provisionCognitoUser`: 1 invocation
- `getUploadUrl`: 3 invocations (1 per document)
- `validateDocument`: 3 invocations (triggered by S3 ObjectCreated events)
- `stageDocumentCollection`: 1 invocation
- `checkDocumentCollection`: ~6–10 polling checks while documents are uploaded
- `stageITProvisioning`: 1 invocation
- `stagePolicySignOff`: 1 invocation
- `stageManagerIntro`: 1 invocation
- `getOnboardingStatus`: ~5 portal polling queries per employee
- `listOnboardingEmployees`: ~2 pipeline directory refreshes per batch
- `sendReminderEmail`: 30 scheduled cron runs per month

$$\text{Estimated Invocations} = (50 \times 26) + 30 \approx \mathbf{1{,}330 \text{ invocations/month}} \quad (\text{Modelled conservatively as } 2{,}000)$$

- **Compute Memory**: 256 MB ($0.25\text{ GB}$)
- **Average Duration**: 300 ms ($0.30\text{ s}$)
- **Monthly Compute (GB-seconds)**:
  $$2{,}000 \text{ invocations} \times 0.30\text{ s} \times 0.25\text{ GB} = \mathbf{150 \text{ GB-seconds/month}}$$
- **Pricing (`ap-south-1`)**:
  - Request price: $\$0.20$ per $1{,}000{,}000$ requests
  - Duration price: $\$0.0000166667$ per GB-second
- **Calculated Monthly Cost**:
  $$\text{Compute Cost} = 150 \times \$0.0000166667 = \$0.00250$$
  $$\text{Request Cost} = \frac{2{,}000}{1{,}000{,}000} \times \$0.20 = \$0.00040$$
  $$\text{Total Lambda List Cost} = \mathbf{\$0.00290 / \text{month}}$$
- **AWS Free Tier**: Includes 1,000,000 free requests and 400,000 GB-seconds of compute time per month indefinitely.
- **Effective Cost with Free Tier**: **$0.00**
- *Source*: [AWS Lambda Pricing — ap-south-1](https://aws.amazon.com/lambda/pricing/)

---

### 3.2 Amazon DynamoDB

The canonical `onboarding-employee-profile-dev` table operates in **On-Demand Capacity Mode (`PAY_PER_REQUEST`)**.

- **Write Request Units (WRU)**:
  - 1 item insertion (`createEmployeeProfile`): 1 WRU
  - 4 stage transitions + 3 document validations: ~8 WRUs
  - Total writes: $50 \times 9 = 450\text{ WRUs/month}$
- **Read Request Units (RRU)**:
  - Workflow status checks + portal queries + directory scans: ~1,500 RRUs/month
- **Pricing (`ap-south-1`)**:
  - Write units: $\$1.25$ per million WRUs
  - Read units: $\$0.25$ per million RRUs
  - Data storage: First 25 GB free, then $\$0.25$ per GB-month
  - Point-in-Time Recovery (PITR): $\$0.20$ per GB-month
- **Calculated Monthly Cost**:
  $$\text{Write Cost} = \frac{450}{1{,}000{,}000} \times \$1.25 = \$0.00056$$
  $$\text{Read Cost} = \frac{1{,}500}{1{,}000{,}000} \times \$0.25 = \$0.00038$$
  $$\text{Storage (100 KB total data)} = \$0.00000$$
  $$\text{PITR Backup Cost} = 0.0001\text{ GB} \times \$0.20 = \$0.00002$$
  $$\text{Total DynamoDB List Cost} = \mathbf{\$0.00096 / \text{month}}$$
- **AWS Free Tier**: 25 GB of storage included free perpetually.
- **Effective Cost with Free Tier**: **$0.00**
- *Source*: [Amazon DynamoDB Pricing — ap-south-1](https://aws.amazon.com/dynamodb/pricing/)

---

### 3.3 Amazon S3

Private documents bucket (`onboarding-documents-dev-331262815638`) stores raw document uploads under SSE-S3 encryption with versioning enabled.

- **Storage Growth**:
  $$150 \text{ files} \times 2.0\text{ MB} = 300\text{ MB} = 0.293\text{ GB/month}$$
- **Request Volume**:
  - PUT requests: 150 uploads
  - GET/HEAD requests: ~300 validation and retrieval checks
- **Pricing (`ap-south-1`)**:
  - Standard Storage: $\$0.023$ per GB-month
  - PUT, COPY, POST requests: $\$0.005$ per 1,000 requests
  - GET, SELECT requests: $\$0.0004$ per 1,000 requests
- **Calculated Monthly Cost**:
  $$\text{Storage Cost} = 0.293\text{ GB} \times \$0.023 = \$0.00674$$
  $$\text{PUT Request Cost} = \frac{150}{1{,}000} \times \$0.005 = \$0.00075$$
  $$\text{GET Request Cost} = \frac{300}{1{,}000} \times \$0.0004 = \$0.00012$$
  $$\text{Total S3 List Cost} = \mathbf{\$0.00761 / \text{month}}$$
- **AWS Free Tier**: 5 GB Standard storage, 20,000 GET requests, and 2,000 PUT requests per month for 12 months.
- **Effective Cost with Free Tier**: **$0.00**
- *Source*: [Amazon S3 Pricing — ap-south-1](https://aws.amazon.com/s3/pricing/)

---

### 3.4 Amazon Cognito

User pool `onboarding-user-pool-dev` manages credentials and authentication for new hires and HR administrators.

- **Monthly Active Users (MAUs)**:
  - 50 new hire employees + ~5 HR administrators = **55 MAUs/month**
- **Pricing (`ap-south-1`)**:
  - First **50,000 MAUs per month: FREE**
  - Next 50,000 MAUs: $\$0.0055$ per MAU
- **Calculated Monthly Cost**:
  $$\text{Cognito List Cost} = \mathbf{\$0.00 / \text{month}}$$
- **AWS Free Tier**: Cognito offers 50,000 MAUs free per month on a permanent basis.
- **Effective Cost with Free Tier**: **$0.00**
- *Source*: [Amazon Cognito Pricing](https://aws.amazon.com/cognito/pricing/)

---

### 3.5 Amazon SES

Handles outbound automated communication, including initial employee invitations and scheduled reminders.

- **Monthly Email Volume**:
  $$50 \text{ employees} \times 4 \text{ emails/employee} = \mathbf{200 \text{ emails/month}}$$
- **Pricing (`ap-south-1`)**:
  - Outbound email: $\$0.10$ per 1,000 emails
  - Inbound email: First 1,000 free (not utilized)
- **Calculated Monthly Cost**:
  $$\text{SES Outbound Cost} = \frac{200}{1{,}000} \times \$0.10 = \mathbf{\$0.02000 / \text{month}}$$
- **AWS Free Tier**: Free tier applies when sending from EC2. Sending via serverless Lambda outside EC2 is billed at standard list rate.
- **Effective Cost with Free Tier**: **$0.02 / month**
- *Source*: [Amazon SES Pricing](https://aws.amazon.com/ses/pricing/)

---

### 3.6 Amazon SNS

Topic `onboarding-hr-notifications-dev` dispatches completion alerts to HR stakeholders when an employee finishes all 4 stages.

- **Monthly Volume**: 50 published messages/month
- **Pricing (`ap-south-1`)**:
  - Topic publish requests: $\$0.50$ per 1,000,000 requests
  - Email notification deliveries: First 1,000 deliveries free each month, then $\$2.00$ per 100,000
- **Calculated Monthly Cost**:
  $$\text{Publish Cost} = \frac{50}{1{,}000{,}000} \times \$0.50 = \$0.000025$$
  $$\text{Email Delivery Cost} = \$0.000000 \quad (\text{within 1,000 free deliveries})$$
  $$\text{Total SNS List Cost} = \mathbf{\$0.000025 / \text{month}}$$
- **AWS Free Tier**: 1,000,000 API requests and 1,000 email notifications free every month perpetually.
- **Effective Cost with Free Tier**: **$0.00**
- *Source*: [Amazon SNS Pricing](https://aws.amazon.com/sns/pricing/)

---

### 3.7 AWS Step Functions

Orchestrates the multi-stage onboarding workflow using a **Standard Workflow** (`onboarding-state-machine-dev`).

- **Executions**: 50 executions/month
- **State Transitions**: ~6 to 10 transitions per execution (including wait loops)
  $$50 \text{ executions} \times 8 \text{ avg transitions} = \mathbf{400 \text{ state transitions/month}}$$
- **Pricing (`ap-south-1`)**:
  - $\$0.025$ per 1,000 state transitions ($\$0.000025$ per transition)
- **Calculated Monthly Cost**:
  $$\text{Step Functions List Cost} = \frac{400}{1{,}000} \times \$0.025 = \mathbf{\$0.01000 / \text{month}}$$
- **AWS Free Tier**: Step Functions includes **4,000 free state transitions per month** perpetually across all regions.
- **Effective Cost with Free Tier**: **$0.00**
- *Source*: [AWS Step Functions Pricing](https://aws.amazon.com/step-functions/pricing/)

---

### 3.8 Amazon API Gateway

Regional REST API (`onboarding-api-dev`) routes frontend client requests to backend handlers.

- **Monthly Request Volume**:
  - `POST /employees`: 50
  - `POST /documents/upload-url`: 150
  - `GET /onboarding/{id}/status`: ~150
  - `GET /onboarding/pipeline`: ~50
  - Preflight `OPTIONS` requests: ~100
  - Total: **~500 requests/month**
- **Pricing (`ap-south-1`)**:
  - $\$3.50$ per million requests for the first 333 million requests/month
- **Calculated Monthly Cost**:
  $$\text{API Gateway List Cost} = \frac{500}{1{,}000{,}000} \times \$3.50 = \mathbf{\$0.00175 / \text{month}}$$
- **AWS Free Tier**: API Gateway includes 1,000,000 free API calls per month for the first 12 months.
- **Effective Cost with Free Tier**: **$0.00**
- *Source*: [Amazon API Gateway Pricing](https://aws.amazon.com/api-gateway/pricing/)

---

## 4. Monthly Cost Summary

The following table summarizes the monthly operating cost for 50 onboarding events per month in `ap-south-1`:

| AWS Service | Resource / Identifier | Estimated Monthly Usage | List Cost (USD) | Effective Cost w/ Free Tier (USD) | Notes |
|---|---|---|---|---|---|
| **AWS Lambda** | 12 Microservices (`python3.12`) | 2,000 requests, 150 GB-s | $0.00290 | **$0.00** | Covered by 400,000 GB-s Free Tier |
| **Amazon DynamoDB** | `onboarding-employee-profile-dev` | 450 WRU, 1,500 RRU, <1 MB | $0.00096 | **$0.00** | Covered by 25 GB Free Tier + on-demand |
| **Amazon S3** | `onboarding-documents-dev` | 300 MB storage, 450 reqs | $0.00761 | **$0.00** | Covered by 5 GB S3 Standard Free Tier |
| **Amazon Cognito** | `onboarding-user-pool-dev` | 55 MAUs | $0.00000 | **$0.00** | Covered by 50,000 MAU Free Tier |
| **Amazon SES** | System transactional comms | 200 outbound emails | $0.02000 | **$0.02** | Billed at $0.10 / 1,000 emails |
| **Amazon SNS** | `onboarding-hr-notifications-dev` | 50 publish events | $0.00003 | **$0.00** | Covered by 1M request / 1K email Free Tier |
| **AWS Step Functions** | `onboarding-state-machine-dev` | 400 state transitions | $0.01000 | **$0.00** | Covered by 4,000 transition Free Tier |
| **Amazon API Gateway** | `onboarding-api-dev` (REST) | 500 requests | $0.00175 | **$0.00** | Covered by 1M call Free Tier |
| **TOTALS** | | | **$0.04325** | **$0.02000** | **~$0.04 List / ~$0.02 Effective** |

### Projected Cost in Local Currency (INR)
At a representative exchange rate of USD 1 = INR 84.00:
- **Total List Cost**: $\approx \mathbf{₹3.63 \text{ per month}}$
- **Effective Cost (with Free Tier)**: $\approx \mathbf{₹1.68 \text{ per month}}$
- **Cost per Onboarding Event**: $\approx \mathbf{\$0.00086 \text{ (₹0.07)}}$

> **Disclaimer**: Actual AWS billing will vary based on document payload sizes, session token refresh frequency, email notification deliverability, and account-level Free Tier expiration.

---

## 5. Calculation Methodology

The formulas below enable immediate verification and reproduction:

### 1. AWS Lambda
$$\text{Cost}_{\text{Lambda}} = \left(\text{Invocations} \times \text{Duration (s)} \times \frac{\text{Memory (MB)}}{1024} \times \$0.0000166667\right) + \left(\frac{\text{Invocations}}{1{,}000{,}000} \times \$0.20\right)$$

### 2. Amazon DynamoDB (On-Demand)
$$\text{Cost}_{\text{DDB}} = \left(\frac{\text{WRU}}{1{,}000{,}000} \times \$1.25\right) + \left(\frac{\text{RRU}}{1{,}000{,}000} \times \$0.25\right) + \left(\text{Storage (GB)} \times \$0.25\right) + \left(\text{Storage (GB)} \times \$0.20\right)$$

### 3. Amazon S3
$$\text{Cost}_{\text{S3}} = \left(\text{Storage (GB)} \times \$0.023\right) + \left(\frac{\text{PUT Requests}}{1{,}000} \times \$0.005\right) + \left(\frac{\text{GET Requests}}{1{,}000} \times \$0.0004\right)$$

### 4. Amazon SES
$$\text{Cost}_{\text{SES}} = \frac{\text{Outbound Emails}}{1{,}000} \times \$0.10$$

### 5. AWS Step Functions
$$\text{Cost}_{\text{SFN}} = \text{Executions} \times \frac{\text{Transitions}}{\text{Execution}} \times \frac{\$0.025}{1{,}000}$$

### 6. Amazon API Gateway
$$\text{Cost}_{\text{APIGW}} = \frac{\text{Requests}}{1{,}000{,}000} \times \$3.50$$

---

## 6. Free Tier Considerations

AWS categorizes Free Tier discounts into **Permanent (Always Free)** and **12-Month Free**:

| AWS Service | Free Tier Category | Monthly Free Allowance | Application to 50 Events/Month |
|---|---|---|---|
| **AWS Lambda** | **Always Free** | 1M requests + 400,000 GB-seconds | **Fully Absorbed** (150 GB-s used $\ll$ 400,000) |
| **Amazon DynamoDB** | **Always Free** | 25 GB storage | **Fully Absorbed** (<1 MB used $\ll$ 25 GB) |
| **Amazon Cognito** | **Always Free** | 50,000 MAUs | **Fully Absorbed** (55 MAUs used $\ll$ 50,000) |
| **AWS Step Functions** | **Always Free** | 4,000 state transitions | **Fully Absorbed** (400 used $\ll$ 4,000) |
| **Amazon SNS** | **Always Free** | 1M publish requests + 1K email alerts | **Fully Absorbed** (50 used $\ll$ 1,000,000) |
| **Amazon S3** | **12-Month Free** | 5 GB Standard storage + 2,000 PUTs | **Fully Absorbed** (0.29 GB used $\ll$ 5 GB) |
| **Amazon API Gateway** | **12-Month Free** | 1,000,000 API calls | **Fully Absorbed** (500 used $\ll$ 1,000,000) |
| **Amazon SES** | Non-EC2 standard rate | No non-EC2 free tier | Billed at **$0.02/month** |

---

## 7. Additional and Operational Costs

For long-term operational planning, the following secondary factors were evaluated:

1. **DynamoDB Point-in-Time Recovery (PITR)**:
   - Enabled on `onboarding-employee-profile-dev` for compliance and recovery.
   - Billed at $\$0.20/\text{GB-month}$. For small tables ($< 1\text{ MB}$), this costs less than $\$0.0001/\text{month}$.
2. **S3 Object Versioning**:
   - The documents bucket retains noncurrent object versions when updated. At 150 documents/month with negligible re-uploads, noncurrent storage overhead is negligible ($< 50\text{ MB/month}$).
3. **Amazon CloudWatch Logs**:
   - Each Lambda writes structured execution logs to dedicated log groups.
   - Ingestion: ~2,000 invocations $\times$ 1 KB = ~2 MB/month.
   - CloudWatch includes **5 GB of log data ingestion free** each month; storage is $\$0.03/\text{GB-month}$.
4. **Data Transfer OUT**:
   - Outbound internet data transfer includes the first **100 GB per month free** across all AWS services. Total egress for this workload is $< 1\text{ GB/month}$.

---

## 8. Pricing Sources

All rates are referenced from official AWS pricing pages for the `ap-south-1` (Mumbai) region:

- **AWS Lambda**: [https://aws.amazon.com/lambda/pricing/](https://aws.amazon.com/lambda/pricing/)
- **Amazon DynamoDB**: [https://aws.amazon.com/dynamodb/pricing/on-demand/](https://aws.amazon.com/dynamodb/pricing/on-demand/)
- **Amazon S3**: [https://aws.amazon.com/s3/pricing/](https://aws.amazon.com/s3/pricing/)
- **Amazon Cognito**: [https://aws.amazon.com/cognito/pricing/](https://aws.amazon.com/cognito/pricing/)
- **Amazon SES**: [https://aws.amazon.com/ses/pricing/](https://aws.amazon.com/ses/pricing/)
- **Amazon SNS**: [https://aws.amazon.com/sns/pricing/](https://aws.amazon.com/sns/pricing/)
- **AWS Step Functions**: [https://aws.amazon.com/step-functions/pricing/](https://aws.amazon.com/step-functions/pricing/)
- **Amazon API Gateway**: [https://aws.amazon.com/api-gateway/pricing/](https://aws.amazon.com/api-gateway/pricing/)
- **AWS Free Tier Official Details**: [https://aws.amazon.com/free/](https://aws.amazon.com/free/)

---

## 9. AWS Pricing Calculator

This estimate can be reproduced and adjusted using the official AWS Pricing Calculator:

- **Official Service Tool**: **[AWS Pricing Calculator](https://calculator.aws/)**
- **Region Filter**: `Asia Pacific (Mumbai) ap-south-1`
