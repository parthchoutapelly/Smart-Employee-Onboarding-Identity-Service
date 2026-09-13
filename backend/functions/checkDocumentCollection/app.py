import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")


def lambda_handler(event, context):
    """
    Phase 5 — Step Functions Document Collection Polling Checker.

    Invoked by the WaitForDocuments polling loop inside the onboarding state machine.
    Reads onboarding_status.document_collection from EmployeeProfileTable.

    Receives (Step Functions input):
        { "employee_id": "<uuid>" }

    Returns (Step Functions-compatible dict — NOT an API Gateway response):
        { "employee_id": "<uuid>", "document_collection": "pending" }
        OR
        { "employee_id": "<uuid>", "document_collection": "complete" }

    Raises:
        ValueError  — missing employee_id (Step Functions marks execution as FAILED)
        RuntimeError — DynamoDB failure (Step Functions retries per ASL retry policy)
    """
    logger.info("checkDocumentCollection invoked with event: %s", json.dumps(event))

    employee_id = event.get("employee_id")
    if not employee_id:
        error_msg = "Missing required 'employee_id' in Step Functions input"
        logger.error(error_msg)
        raise ValueError(error_msg)

    table_name = os.environ.get("EMPLOYEE_TABLE_NAME")
    if not table_name:
        error_msg = "EMPLOYEE_TABLE_NAME environment variable is not configured"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    try:
        table = dynamodb.Table(table_name)
        response = table.get_item(Key={"employee_id": employee_id})
    except ClientError as e:
        logger.error(
            "DynamoDB get_item failed for employee_id %s: %s",
            employee_id,
            e.response["Error"]["Message"],
        )
        raise RuntimeError(
            f"DynamoDB error for employee_id {employee_id}: {e.response['Error']['Message']}"
        ) from e

    item = response.get("Item")
    if not item:
        logger.error("Employee profile not found for employee_id: %s", employee_id)
        raise ValueError(f"Employee profile not found for employee_id: {employee_id}")

    doc_collection_status = (
        item.get("onboarding_status", {}).get("document_collection", "pending")
    )
    logger.info(
        "employee_id=%s document_collection=%s", employee_id, doc_collection_status
    )

    return {
        "employee_id": employee_id,
        "document_collection": doc_collection_status,
    }
