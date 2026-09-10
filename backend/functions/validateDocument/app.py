import json
import logging
import os
import urllib.parse
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
sns_client = boto3.client("sns")

ALLOWED_DOCUMENT_TYPES = {"id_proof", "degree_certificate", "offer_letter"}
ALLOWED_EXTENSIONS = {"pdf", "jpg", "png"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10,485,760 bytes (strictly < 10MB)

def ensure_documents_map(table, employee_id, item):
    """
    Ensures that onboarding_status.documents exists in the DynamoDB record.
    Initializes missing fields if this is an older Phase 1/2 record.
    """
    onboarding_status = item.get("onboarding_status", {})
    if "documents" not in onboarding_status or not isinstance(onboarding_status["documents"], dict):
        initial_documents = {
            "id_proof": "pending",
            "degree_certificate": "pending",
            "offer_letter": "pending"
        }
        try:
            table.update_item(
                Key={"employee_id": employee_id},
                UpdateExpression="SET onboarding_status.documents = if_not_exists(onboarding_status.documents, :docs)",
                ExpressionAttributeValues={":docs": initial_documents}
            )
            logger.info("Initialized onboarding_status.documents for employee_id: %s", employee_id)
        except ClientError as e:
            logger.warning("Failed to initialize documents map: %s", e.response["Error"]["Message"])

def process_rejection(s3_bucket, s3_key, table, employee_id, document_type, reason):
    """
    Deletes the invalid S3 object and records rejection status and reason in DynamoDB.
    """
    logger.warning("Rejecting document [%s] for employee [%s]. Reason: %s", s3_key, employee_id, reason)

    # 1. Delete the offending S3 object
    try:
        s3_client.delete_object(Bucket=s3_bucket, Key=s3_key)
        logger.info("Deleted invalid S3 object: %s/%s", s3_bucket, s3_key)
    except ClientError as e:
        logger.error("Failed to delete S3 object %s/%s: %s", s3_bucket, s3_key, e.response["Error"]["Message"])

    # 2. Update DynamoDB if employee_id and document_type are identifiable
    if table and employee_id and document_type:
        now_iso = datetime.now(timezone.utc).isoformat()
        reason_key = f"{document_type}_rejection_reason"
        try:
            table.update_item(
                Key={"employee_id": employee_id},
                UpdateExpression="SET onboarding_status.documents.#doc = :status, onboarding_status.documents.#reason = :reason, onboarding_status.documents.#ts = :ts",
                ExpressionAttributeNames={
                    "#doc": document_type,
                    "#reason": reason_key,
                    "#ts": f"{document_type}_rejected_at"
                },
                ExpressionAttributeValues={
                    ":status": "rejected",
                    ":reason": reason,
                    ":ts": now_iso
                }
            )
            logger.info("Recorded rejection status for %s (%s) in DynamoDB", employee_id, document_type)
        except ClientError as e:
            logger.error("Failed to update rejection in DynamoDB: %s", e.response["Error"]["Message"])

    return {
        "status": "rejected",
        "employee_id": employee_id,
        "document_type": document_type,
        "reason": reason
    }

def process_record(record, table_name, topic_arn):
    s3_info = record.get("s3", {})
    bucket_name = s3_info.get("bucket", {}).get("name")
    raw_key = s3_info.get("object", {}).get("key")

    if not bucket_name or not raw_key:
        logger.error("Malformed S3 record: missing bucket or key: %s", record)
        return {"status": "skipped", "reason": "malformed_record"}

    s3_key = urllib.parse.unquote_plus(raw_key)
    logger.info("Processing S3 object: bucket=%s, key=%s", bucket_name, s3_key)

    # Key format check: documents/{employee_id}/{document_type}.{extension}
    parts = s3_key.split("/")
    if len(parts) != 3 or parts[0] != "documents":
        reason = f"Malformed S3 key '{s3_key}'. Expected format: documents/{{employee_id}}/{{document_type}}.{{extension}}"
        return process_rejection(bucket_name, s3_key, None, None, None, reason)

    employee_id = parts[1].strip()
    filename = parts[2].strip()

    if not employee_id:
        reason = "Empty employee_id in S3 key"
        return process_rejection(bucket_name, s3_key, None, None, None, reason)

    if "." not in filename:
        reason = f"Filename '{filename}' lacks an extension"
        return process_rejection(bucket_name, s3_key, None, employee_id, None, reason)

    document_type, ext = os.path.splitext(filename)
    clean_ext = ext.lstrip(".").lower()

    table = dynamodb.Table(table_name) if table_name else None

    # Verify employee profile exists
    emp_item = None
    if table:
        try:
            resp = table.get_item(Key={"employee_id": employee_id})
            emp_item = resp.get("Item")
            if not emp_item:
                reason = f"Employee profile not found for employee_id '{employee_id}'"
                return process_rejection(bucket_name, s3_key, None, employee_id, document_type, reason)
            ensure_documents_map(table, employee_id, emp_item)
        except ClientError as e:
            logger.error("DynamoDB get_item error for employee %s: %s", employee_id, e.response["Error"]["Message"])

    # Validate document_type
    if document_type not in ALLOWED_DOCUMENT_TYPES:
        reason = f"Invalid document_type '{document_type}'. Allowed types: {sorted(list(ALLOWED_DOCUMENT_TYPES))}"
        return process_rejection(bucket_name, s3_key, table, employee_id, document_type, reason)

    # Validate file extension
    if clean_ext not in ALLOWED_EXTENSIONS:
        reason = f"Unsupported file extension '.{clean_ext}'. Allowed extensions: {sorted(list(ALLOWED_EXTENSIONS))}"
        return process_rejection(bucket_name, s3_key, table, employee_id, document_type, reason)

    # Inspect object metadata and size from S3
    try:
        head = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
        content_length = head.get("ContentLength", 0)
    except ClientError as e:
        logger.error("Failed to head S3 object %s/%s: %s", bucket_name, s3_key, e.response["Error"]["Message"])
        reason = f"Could not access S3 object: {e.response['Error']['Message']}"
        return process_rejection(bucket_name, s3_key, table, employee_id, document_type, reason)

    # Strict size rule: strictly < 10 * 1024 * 1024 bytes (10,485,760 bytes)
    if content_length >= MAX_FILE_SIZE_BYTES:
        reason = f"File size {content_length} bytes exceeds maximum allowed limit of {MAX_FILE_SIZE_BYTES - 1} bytes (< 10MB)"
        return process_rejection(bucket_name, s3_key, table, employee_id, document_type, reason)

    # --- Valid Document Processing ---
    logger.info("Document [%s] passed validation (size: %s bytes)", s3_key, content_length)
    now_iso = datetime.now(timezone.utc).isoformat()
    reason_key = f"{document_type}_rejection_reason"

    try:
        table.update_item(
            Key={"employee_id": employee_id},
            UpdateExpression="SET onboarding_status.documents.#doc = :status, onboarding_status.documents.#ts = :ts REMOVE onboarding_status.documents.#reason",
            ExpressionAttributeNames={
                "#doc": document_type,
                "#ts": f"{document_type}_verified_at",
                "#reason": reason_key
            },
            ExpressionAttributeValues={
                ":status": "verified",
                ":ts": now_iso
            }
        )
        logger.info("Updated status of [%s] to 'verified' for employee %s", document_type, employee_id)
    except ClientError as e:
        # If attribute to remove does not exist, update without REMOVE
        table.update_item(
            Key={"employee_id": employee_id},
            UpdateExpression="SET onboarding_status.documents.#doc = :status, onboarding_status.documents.#ts = :ts",
            ExpressionAttributeNames={
                "#doc": document_type,
                "#ts": f"{document_type}_verified_at"
            },
            ExpressionAttributeValues={
                ":status": "verified",
                ":ts": now_iso
            }
        )

    # Check if all 3 required documents are verified
    try:
        updated_item = table.get_item(Key={"employee_id": employee_id}).get("Item", {})
        docs_status = updated_item.get("onboarding_status", {}).get("documents", {})

        all_verified = all(
            docs_status.get(req_doc) == "verified"
            for req_doc in ["id_proof", "degree_certificate", "offer_letter"]
        )

        if all_verified:
            logger.info("All 3 documents verified for employee %s! Checking completion status...", employee_id)
            current_stage_status = updated_item.get("onboarding_status", {}).get("document_collection")

            # Use conditional update to guarantee at-most-once transition and prevent duplicate SNS notifications
            try:
                table.update_item(
                    Key={"employee_id": employee_id},
                    UpdateExpression="SET onboarding_status.document_collection = :complete, onboarding_status.document_collection_completed_at = :ts",
                    ConditionExpression="onboarding_status.document_collection <> :complete",
                    ExpressionAttributeValues={
                        ":complete": "complete",
                        ":ts": now_iso
                    }
                )
                logger.info("Atomically set onboarding_status.document_collection = 'complete' for %s", employee_id)

                # Publish to SNS Topic
                if topic_arn:
                    sns_message = {
                        "employee_id": employee_id,
                        "event": "all_documents_verified"
                    }
                    sns_resp = sns_client.publish(
                        TopicArn=topic_arn,
                        Message=json.dumps(sns_message),
                        Subject="Employee Onboarding: All Documents Verified"
                    )
                    logger.info("Published all_documents_verified event to SNS: %s (MessageId: %s)",
                                topic_arn, sns_resp.get("MessageId"))

            except table.meta.client.exceptions.ConditionalCheckFailedException:
                logger.info("document_collection is already marked complete for %s. Skipping duplicate SNS publish.", employee_id)

    except ClientError as e:
        logger.error("Error during all-documents-verified evaluation: %s", e.response["Error"]["Message"])

    return {
        "status": "verified",
        "employee_id": employee_id,
        "document_type": document_type,
        "size_bytes": content_length
    }

def lambda_handler(event, context):
    """
    S3 ObjectCreated trigger handler.
    Validates uploaded documents (<10MB, allowed types, allowed extensions),
    updates DynamoDB status, deletes invalid uploads, and notifies HR via SNS
    when all 3 required documents are verified.
    """
    logger.info("ValidateDocument invoked with event: %s", json.dumps(event) if isinstance(event, dict) else str(event))

    table_name = os.environ.get("EMPLOYEE_TABLE_NAME")
    topic_arn = os.environ.get("NOTIFICATIONS_TOPIC_ARN")

    records = event.get("Records", [])
    results = []

    # Support direct invocation or mock events
    if not records and "s3" in event:
        records = [event]
    elif not records and "employee_id" in event and "s3_key" in event:
        # Mock direct event
        records = [{
            "s3": {
                "bucket": {"name": event.get("bucket", os.environ.get("DOCUMENTS_BUCKET_NAME", "documents-bucket"))},
                "object": {"key": event["s3_key"]}
            }
        }]

    for record in records:
        res = process_record(record, table_name, topic_arn)
        results.append(res)

    return {
        "status": "processed",
        "processed_count": len(results),
        "results": results
    }
