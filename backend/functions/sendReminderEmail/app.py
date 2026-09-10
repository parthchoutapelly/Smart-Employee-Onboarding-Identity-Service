import json
import logging
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
ses_client = boto3.client("ses")

STAGE_RECIPIENT_MAP = {
    "document_collection": "employee",
    "it_provisioning": "it_admin",
    "policy_signoff": "employee",
    "manager_intro": "manager"
}

def parse_iso_datetime(dt_str):
    if not dt_str:
        return None
    try:
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        return datetime.fromisoformat(dt_str)
    except Exception as e:
        logger.warning("Could not parse datetime string '%s': %s", dt_str, e)
        return None

def send_notification(recipient_email, stage_name, employee_name, employee_id, hours_elapsed):
    """
    Sends SES notification email for a pending onboarding stage.
    Gracefully handles SES sandbox and unverified identities in dev.
    """
    sender = os.environ.get("SES_SENDER_EMAIL", "onboarding-noreply@example.com")
    subject = f"Action Required: Onboarding Reminder - {stage_name.replace('_', ' ').title()}"
    body_text = (
        f"Hello,\n\n"
        f"This is a reminder that the onboarding stage '{stage_name.replace('_', ' ').title()}' "
        f"for employee {employee_name} (ID: {employee_id}) has been pending for over {hours_elapsed:.1f} hours.\n\n"
        f"Please log in to the Smart Employee Onboarding Portal to complete this stage.\n\n"
        f"Regards,\nHR Operations Team"
    )

    try:
        response = ses_client.send_email(
            Source=sender,
            Destination={"ToAddresses": [recipient_email]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Text": {"Data": body_text}}
            }
        )
        logger.info("Sent reminder email to %s for stage %s (SES Message ID: %s)",
                    recipient_email, stage_name, response.get("MessageId"))
        return True
    except ClientError as e:
        logger.warning("SES send_email failed (expected if sandbox/unverified in dev): %s",
                       e.response["Error"]["Message"])
        return False

def lambda_handler(event, context):
    """
    Scans EmployeeProfileTable for incomplete onboarding stages.
    If a stage is pending or in_progress past REMINDER_THRESHOLD_HOURS (default 24h),
    sends reminder notifications to the appropriate parties.
    """
    logger.info("Reminder Lambda invoked with event: %s", json.dumps(event) if isinstance(event, dict) else str(event))

    threshold_hours = float(os.environ.get("REMINDER_THRESHOLD_HOURS", "24"))
    if isinstance(event, dict) and "threshold_hours" in event:
        try:
            threshold_hours = float(event["threshold_hours"])
        except (ValueError, TypeError):
            pass

    table_name = os.environ.get("EMPLOYEE_TABLE_NAME")
    if not table_name:
        logger.error("EMPLOYEE_TABLE_NAME not configured")
        return {"status": "error", "message": "EMPLOYEE_TABLE_NAME missing"}

    table = dynamodb.Table(table_name)
    now = datetime.now(timezone.utc)

    try:
        # Scan table for employees
        response = table.scan()
        employees = response.get("Items", [])
    except ClientError as e:
        logger.error("Failed to scan EmployeeProfileTable: %s", e.response["Error"]["Message"])
        return {"status": "error", "message": e.response["Error"]["Message"]}

    reminders_dispatched = []

    for emp in employees:
        emp_id = emp.get("employee_id")
        emp_name = emp.get("name", "Employee")
        emp_email = emp.get("email")
        manager = emp.get("manager", "manager@example.com")
        created_at_str = emp.get("created_at")
        created_at = parse_iso_datetime(created_at_str) or now

        onboarding_status = emp.get("onboarding_status", {})

        for stage, status in onboarding_status.items():
            if status in ["pending", "in_progress"]:
                # Check duration
                elapsed_hours = (now - created_at).total_seconds() / 3600.0
                if elapsed_hours >= threshold_hours:
                    # Determine target email
                    role_type = STAGE_RECIPIENT_MAP.get(stage, "employee")
                    if role_type == "employee":
                        recipient = emp_email
                    elif role_type == "manager":
                        recipient = manager if "@" in manager else emp_email
                    else:
                        recipient = os.environ.get("IT_ADMIN_EMAIL", "it-support@example.com")

                    if recipient:
                        sent = send_notification(recipient, stage, emp_name, emp_id, elapsed_hours)
                        reminders_dispatched.append({
                            "employee_id": emp_id,
                            "stage": stage,
                            "recipient": recipient,
                            "elapsed_hours": round(elapsed_hours, 2),
                            "sent": sent
                        })

    return {
        "status": "success",
        "threshold_hours": threshold_hours,
        "employees_scanned": len(employees),
        "reminders_dispatched_count": len(reminders_dispatched),
        "reminders": reminders_dispatched
    }
