import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
lambda_client = boto3.client("lambda")

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
REQUIRED_FIELDS = ["name", "email", "department", "role", "manager", "joining_date", "employment_type"]

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "POST,OPTIONS"
}

def build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body)
    }

def lambda_handler(event, context):
    """
    Handles POST /employees
    Creates the canonical EmployeeProfile record in DynamoDB and triggers Cognito user provisioning.
    """
    logger.info("Received event: %s", json.dumps(event) if isinstance(event, dict) else str(event))

    # Support CORS preflight
    http_method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")
    if http_method == "OPTIONS":
        return build_response(200, {"message": "OK"})

    # Parse request body
    body = event.get("body")
    if isinstance(body, str):
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return build_response(400, {"error": "Invalid JSON format in request body"})
    elif isinstance(body, dict):
        payload = body
    elif isinstance(event, dict) and any(k in event for k in REQUIRED_FIELDS):
        payload = event
    else:
        return build_response(400, {"error": "Missing request body"})

    # Validate required fields
    missing_fields = [f for f in REQUIRED_FIELDS if f not in payload or not str(payload[f]).strip()]
    if missing_fields:
        return build_response(400, {
            "error": f"Missing required fields: {', '.join(missing_fields)}"
        })

    email = str(payload["email"]).strip().lower()
    if not EMAIL_REGEX.match(email):
        return build_response(400, {"error": "Invalid email address format"})

    joining_date = str(payload["joining_date"]).strip()
    # Basic date validation (YYYY-MM-DD)
    if not re.match(r"^\d{4}-\d{2}-\d{2}", joining_date):
        return build_response(400, {"error": "Invalid joining_date format; expected ISO format YYYY-MM-DD"})

    employee_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    employee_item = {
        "employee_id": employee_id,
        "name": str(payload["name"]).strip(),
        "email": email,
        "department": str(payload["department"]).strip(),
        "role": str(payload["role"]).strip(),
        "manager": str(payload["manager"]).strip(),
        "joining_date": joining_date,
        "employment_type": str(payload["employment_type"]).strip(),
        "onboarding_status": {
            "document_collection": "pending",
            "it_provisioning": "pending",
            "policy_signoff": "pending",
            "manager_intro": "pending",
            "documents": {
                "id_proof": "pending",
                "degree_certificate": "pending",
                "offer_letter": "pending"
            }
        },
        "created_at": created_at
    }

    table_name = os.environ.get("EMPLOYEE_TABLE_NAME")
    if not table_name:
        logger.error("EMPLOYEE_TABLE_NAME environment variable not configured")
        return build_response(500, {"error": "Configuration error: EMPLOYEE_TABLE_NAME missing"})

    try:
        table = dynamodb.Table(table_name)
        table.put_item(Item=employee_item)
        logger.info("Successfully created EmployeeProfile for employee_id: %s", employee_id)
    except ClientError as e:
        logger.error("DynamoDB put_item failed: %s", e.response["Error"]["Message"])
        return build_response(500, {"error": "Failed to persist employee record to database"})

    # Trigger Cognito user provisioning Lambda asynchronously
    provision_func = os.environ.get("PROVISION_FUNCTION_NAME")
    if provision_func:
        try:
            lambda_client.invoke(
                FunctionName=provision_func,
                InvocationType="Event",
                Payload=json.dumps({
                    "employee_id": employee_id,
                    "name": employee_item["name"],
                    "email": employee_item["email"],
                    "department": employee_item["department"],
                    "role": employee_item["role"]
                })
            )
            logger.info("Dispatched provisioning event for employee_id: %s to %s", employee_id, provision_func)
        except Exception as e:
            logger.error("Failed to invoke provisioning Lambda: %s", str(e))
            # Profile is created, provisioning will be retried or handled; don't fail the 201 creation

    return build_response(201, {
        "employee_id": employee_id,
        "status": "created"
    })
