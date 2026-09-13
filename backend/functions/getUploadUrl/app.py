import json
import logging
import os

import boto3
from botocore.exceptions import ClientError
try:
    from botocore.config import Config
except (ImportError, ModuleNotFoundError):
    from botocore import config
    Config = config.Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")

s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    config=Config(
        signature_version="s3v4",
        s3={"addressing_style": "virtual"}
    )
)

ALLOWED_DOCUMENT_TYPES = {"id_proof", "degree_certificate", "offer_letter"}
ALLOWED_EXTENSIONS = {"pdf", "jpg", "png"}
PRESIGNED_URL_EXPIRATION = 900  # 15 minutes in seconds

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
    Handles POST /documents/upload-url
    Generates a presigned S3 PUT URL for employee document uploads.
    """
    logger.info("Received getUploadUrl event: %s", json.dumps(event) if isinstance(event, dict) else str(event))

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
    elif isinstance(event, dict) and "employee_id" in event:
        payload = event
    else:
        return build_response(400, {"error": "Missing request body"})

    employee_id = payload.get("employee_id")
    document_type = payload.get("document_type")
    file_extension = payload.get("file_extension")

    if not employee_id or not isinstance(employee_id, str) or not employee_id.strip():
        return build_response(400, {"error": "Missing or invalid required field 'employee_id'"})

    employee_id = employee_id.strip()

    if not document_type or document_type not in ALLOWED_DOCUMENT_TYPES:
        return build_response(400, {
            "error": f"Invalid document_type '{document_type}'. Allowed types: {sorted(list(ALLOWED_DOCUMENT_TYPES))}"
        })

    if not file_extension or not isinstance(file_extension, str):
        return build_response(400, {
            "error": f"Invalid file_extension. Allowed extensions: {sorted(list(ALLOWED_EXTENSIONS))}"
        })

    clean_ext = file_extension.strip().lower().lstrip(".")
    if clean_ext not in ALLOWED_EXTENSIONS:
        return build_response(400, {
            "error": f"Invalid file_extension '{file_extension}'. Allowed extensions: {sorted(list(ALLOWED_EXTENSIONS))}"
        })

    bucket_name = os.environ.get("DOCUMENTS_BUCKET_NAME")
    if not bucket_name:
        logger.error("DOCUMENTS_BUCKET_NAME environment variable is not configured")
        return build_response(500, {"error": "Configuration error: DOCUMENTS_BUCKET_NAME missing"})

    s3_key = f"documents/{employee_id}/{document_type}.{clean_ext}"

    try:
        content_type_map = {
            "pdf": "application/pdf",
            "jpg": "image/jpeg",
            "png": "image/png"
        }
        content_type = content_type_map.get(clean_ext, "application/octet-stream")

        presigned_url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": bucket_name,
                "Key": s3_key,
                "ContentType": content_type
            },
            ExpiresIn=PRESIGNED_URL_EXPIRATION
        )

        logger.info("Generated presigned PUT URL for key '%s' (expires in %ss)", s3_key, PRESIGNED_URL_EXPIRATION)
        return build_response(200, {
            "upload_url": presigned_url,
            "s3_key": s3_key
        })

    except ClientError as e:
        logger.error("Failed to generate presigned S3 URL: %s", e.response["Error"]["Message"])
        return build_response(500, {"error": "Failed to generate presigned upload URL"})
