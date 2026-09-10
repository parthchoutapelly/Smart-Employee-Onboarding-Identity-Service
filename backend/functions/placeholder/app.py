import json
import os

def lambda_handler(event, context):
    """
    Phase 0 Placeholder Lambda function to verify IAM execution role,
    environment variable injection, and SAM deployment capability.
    """
    stage = os.environ.get("STAGE", "unknown")
    employee_table = os.environ.get("EMPLOYEE_TABLE_NAME", "unknown")
    documents_bucket = os.environ.get("DOCUMENTS_BUCKET_NAME", "unknown")

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "status": "healthy",
            "message": "Smart Employee Onboarding & Identity Service - Placeholder Lambda is operational",
            "environment": {
                "STAGE": stage,
                "EMPLOYEE_TABLE_NAME": employee_table,
                "DOCUMENTS_BUCKET_NAME": documents_bucket
            }
        })
    }
