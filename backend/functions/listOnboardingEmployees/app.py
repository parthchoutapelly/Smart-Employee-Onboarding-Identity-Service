import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "GET,OPTIONS"
}


def build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body)
    }


def lambda_handler(event, context):
    """
    Handles GET /onboarding/pipeline
    Scans the EmployeeProfileTable with pagination and returns a list of onboarding employee profiles.
    """
    logger.info("Received listOnboardingEmployees event: %s", json.dumps(event) if isinstance(event, dict) else str(event))

    http_method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")
    if http_method == "OPTIONS":
        return build_response(200, {"message": "OK"})

    table_name = os.environ.get("EMPLOYEE_TABLE_NAME")
    if not table_name:
        logger.error("EMPLOYEE_TABLE_NAME is not configured")
        return build_response(500, {"error": "Configuration error: EMPLOYEE_TABLE_NAME missing"})

    try:
        table = dynamodb.Table(table_name)

        items = []
        scan_kwargs = {
            "ProjectionExpression": "employee_id, #nm, email, department, #rl, manager, joining_date, employment_type, created_at, onboarding_status",
            "ExpressionAttributeNames": {
                "#nm": "name",
                "#rl": "role"
            }
        }

        done = False
        start_key = None
        while not done:
            if start_key:
                scan_kwargs["ExclusiveStartKey"] = start_key
            response = table.scan(**scan_kwargs)
            items.extend(response.get("Items", []))
            start_key = response.get("LastEvaluatedKey")
            if not start_key:
                done = True

        logger.info("Successfully scanned %d employee records", len(items))

        default_status = {
            "document_collection": "pending",
            "it_provisioning": "pending",
            "policy_signoff": "pending",
            "manager_intro": "pending"
        }

        pipeline = []
        for item in items:
            raw_status = item.get("onboarding_status") or {}
            onboarding_status = {
                "document_collection": raw_status.get("document_collection", default_status["document_collection"]),
                "it_provisioning": raw_status.get("it_provisioning", default_status["it_provisioning"]),
                "policy_signoff": raw_status.get("policy_signoff", default_status["policy_signoff"]),
                "manager_intro": raw_status.get("manager_intro", default_status["manager_intro"])
            }
            if "documents" in raw_status:
                onboarding_status["documents"] = raw_status["documents"]

            pipeline.append({
                "employee_id": item.get("employee_id"),
                "name": item.get("name", ""),
                "email": item.get("email", ""),
                "department": item.get("department", ""),
                "role": item.get("role", ""),
                "manager": item.get("manager", ""),
                "joining_date": item.get("joining_date", ""),
                "employment_type": item.get("employment_type", ""),
                "created_at": item.get("created_at", ""),
                "onboarding_status": onboarding_status
            })

        # Sort descending by created_at (or empty string if missing)
        pipeline.sort(key=lambda x: x.get("created_at") or "", reverse=True)

        return build_response(200, pipeline)

    except ClientError as e:
        logger.error("DynamoDB scan failed: %s", e.response["Error"]["Message"])
        return build_response(500, {"error": "Failed to retrieve employee onboarding pipeline records"})
    except Exception as e:
        logger.error("Unexpected error in listOnboardingEmployees: %s", str(e))
        return build_response(500, {"error": "Internal server error"})
