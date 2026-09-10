import json
import logging
import os
import secrets
import string

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cognito_client = boto3.client("cognito-idp")
dynamodb = boto3.resource("dynamodb")
ses_client = boto3.client("ses")

def generate_temporary_password(length=14):
    """
    Generates a secure temporary password satisfying Cognito password complexity rules:
    - Minimum 8 chars
    - Uppercase, lowercase, numeric, and special characters
    """
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(secrets.choice(chars) for _ in range(length))
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in "!@#$%^&*" for c in password)):
            return password

def lambda_handler(event, context):
    """
    Provisions a user account in Amazon Cognito User Pool for a new employee,
    sets custom attributes (employee_id, role, department), initiates welcome email,
    and links cognito_sub back to the EmployeeProfile DynamoDB record.
    """
    logger.info("Provisioning Cognito User with payload: %s", json.dumps(event))

    # Parse payload if passed as string or nested body
    if isinstance(event, str):
        try:
            event = json.loads(event)
        except json.JSONDecodeError:
            logger.error("Invalid JSON input")
            return {"status": "error", "message": "Invalid JSON input"}

    if "body" in event and isinstance(event["body"], str):
        try:
            event = json.loads(event["body"])
        except json.JSONDecodeError:
            pass

    employee_id = event.get("employee_id")
    email = event.get("email")
    name = event.get("name", "")
    role = event.get("role", "")
    department = event.get("department", "")

    if not employee_id or not email:
        logger.error("Missing required employee_id or email in event")
        return {"status": "error", "message": "Missing employee_id or email"}

    email = email.strip().lower()
    user_pool_id = os.environ.get("USER_POOL_ID")
    table_name = os.environ.get("EMPLOYEE_TABLE_NAME")

    if not user_pool_id:
        logger.error("USER_POOL_ID environment variable not configured")
        return {"status": "error", "message": "USER_POOL_ID missing"}

    temp_password = generate_temporary_password()

    user_attributes = [
        {"Name": "email", "Value": email},
        {"Name": "email_verified", "Value": "true"},
        {"Name": "custom:employee_id", "Value": employee_id},
        {"Name": "custom:role", "Value": role},
        {"Name": "custom:department", "Value": department}
    ]
    if name:
        user_attributes.append({"Name": "name", "Value": name})

    cognito_sub = None

    try:
        logger.info("Creating Cognito user in pool %s for email: %s", user_pool_id, email)
        response = cognito_client.admin_create_user(
            UserPoolId=user_pool_id,
            Username=email,
            UserAttributes=user_attributes,
            TemporaryPassword=temp_password,
            DesiredDeliveryMediums=["EMAIL"]
        )

        user_attrs = response.get("User", {}).get("Attributes", [])
        for attr in user_attrs:
            if attr.get("Name") == "sub":
                cognito_sub = attr.get("Value")
                break

        logger.info("Successfully created Cognito user: %s with sub: %s", email, cognito_sub)

    except cognito_client.exceptions.UsernameExistsException:
        logger.warning("User %s already exists in Cognito pool. Retrieving existing record...", email)
        try:
            existing_user = cognito_client.admin_get_user(
                UserPoolId=user_pool_id,
                Username=email
            )
            for attr in existing_user.get("UserAttributes", []):
                if attr.get("Name") == "sub":
                    cognito_sub = attr.get("Value")
                    break

            # Update attributes to ensure custom:employee_id is mapped
            cognito_client.admin_update_user_attributes(
                UserPoolId=user_pool_id,
                Username=email,
                UserAttributes=user_attributes
            )
        except ClientError as e:
            logger.error("Failed to query/update existing Cognito user: %s", e.response["Error"]["Message"])
            return {"status": "error", "message": e.response["Error"]["Message"]}

    except ClientError as e:
        logger.error("Cognito admin_create_user failed: %s", e.response["Error"]["Message"])
        return {"status": "error", "message": e.response["Error"]["Message"]}

    # Update DynamoDB EmployeeProfile with linked cognito_sub
    if cognito_sub and table_name:
        try:
            table = dynamodb.Table(table_name)
            table.update_item(
                Key={"employee_id": employee_id},
                UpdateExpression="SET cognito_sub = :sub",
                ExpressionAttributeValues={":sub": cognito_sub}
            )
            logger.info("Updated EmployeeProfile %s with cognito_sub %s", employee_id, cognito_sub)
        except ClientError as e:
            logger.warning("Failed to update EmployeeProfile with cognito_sub: %s", e.response["Error"]["Message"])

    # Optional SES welcome email dispatch if sender configured
    ses_sender = os.environ.get("SES_SENDER_EMAIL")
    if ses_sender:
        try:
            ses_client.send_email(
                Source=ses_sender,
                Destination={"ToAddresses": [email]},
                Message={
                    "Subject": {"Data": "Welcome to the Team — Set up your account"},
                    "Body": {
                        "Html": {
                            "Data": (
                                f"<h3>Welcome to the Team, {name}!</h3>"
                                f"<p>Your employee onboarding account is ready.</p>"
                                f"<p><b>Employee ID:</b> {employee_id}<br/>"
                                f"<b>Username:</b> {email}<br/>"
                                f"<b>Temporary Password:</b> {temp_password}</p>"
                                f"<p>Please log in to your Onboarding Portal to complete onboarding.</p>"
                            )
                        }
                    }
                }
            )
            logger.info("SES welcome email dispatched to %s", email)
        except ClientError as e:
            logger.warning("SES email dispatch skipped/failed: %s", e.response["Error"]["Message"])

    return {
        "status": "provisioned",
        "employee_id": employee_id,
        "email": email,
        "cognito_sub": cognito_sub
    }
