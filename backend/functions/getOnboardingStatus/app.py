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
    Handles GET /onboarding/{employee_id}/status
    Reads the employee record from EmployeeProfileTable and returns the onboarding_status map.
    """
    logger.info("Received getOnboardingStatus event: %s", json.dumps(event) if isinstance(event, dict) else str(event))

    http_method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")
    if http_method == "OPTIONS":
        return build_response(200, {"message": "OK"})

    path_params = event.get("pathParameters") or {}
    employee_id = path_params.get("employee_id") or event.get("employee_id")

    if not employee_id:
        return build_response(400, {"error": "Missing required path parameter 'employee_id'"})

    table_name = os.environ.get("EMPLOYEE_TABLE_NAME")
    if not table_name:
        logger.error("EMPLOYEE_TABLE_NAME is not configured")
        return build_response(500, {"error": "Configuration error: EMPLOYEE_TABLE_NAME missing"})

    try:
        table = dynamodb.Table(table_name)
        response = table.get_item(Key={"employee_id": employee_id})
        item = response.get("Item")

        if not item:
            logger.info("Employee profile not found for employee_id: %s", employee_id)
            return build_response(404, {
                "error": "Employee profile not found",
                "employee_id": employee_id
            })

        onboarding_status = item.get("onboarding_status", {
            "document_collection": "pending",
            "it_provisioning": "pending",
            "policy_signoff": "pending",
            "manager_intro": "pending"
        })

        return build_response(200, {
            "employee_id": employee_id,
            "onboarding_status": onboarding_status
        })

    except ClientError as e:
        logger.error("DynamoDB get_item failed: %s", e.response["Error"]["Message"])
        return build_response(500, {"error": "Failed to retrieve employee onboarding status"})
