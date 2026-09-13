import json
import logging
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
STAGE_NAME = "document_collection"

def lambda_handler(event, context):
    """
    Step Functions Stage Handler: DocumentCollection (initiator)
    Receives: { "employee_id": "<uuid>" }
    Marks onboarding_status.document_collection -> 'in_progress' to record that the stage
    has started.  Actual completion is determined asynchronously by validateDocument (Phase 3)
    and polled by CheckDocumentCollectionFunction via the WaitForDocuments Step Functions loop.
    Returns: { "employee_id": "<uuid>", "stage": "document_collection", "status": "in_progress" }
    """
    logger.info("Stage [%s] invoked with event: %s", STAGE_NAME, json.dumps(event))

    employee_id = event.get("employee_id")
    if not employee_id:
        error_msg = f"Missing required 'employee_id' in event for stage {STAGE_NAME}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    table_name = os.environ.get("EMPLOYEE_TABLE_NAME")
    if not table_name:
        error_msg = "EMPLOYEE_TABLE_NAME environment variable is not configured"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    table = dynamodb.Table(table_name)
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        table.update_item(
            Key={"employee_id": employee_id},
            UpdateExpression="SET onboarding_status.#stage = :status, onboarding_status.#updated = :ts",
            ExpressionAttributeNames={
                "#stage": STAGE_NAME,
                "#updated": f"{STAGE_NAME}_started_at"
            },
            ExpressionAttributeValues={
                ":status": "in_progress",
                ":ts": now_iso
            }
        )
        logger.info("Marked stage [%s] as in_progress for employee_id: %s", STAGE_NAME, employee_id)
    except ClientError as e:
        logger.error("DynamoDB update_item failed for employee_id %s: %s", employee_id, e.response["Error"]["Message"])
        raise

    return {
        "employee_id": employee_id,
        "stage": STAGE_NAME,
        "status": "in_progress"
    }
