import json
import os
import sys
import unittest
from unittest.mock import MagicMock

# Mock boto3 and botocore before importing handlers so tests can run in any environment
mock_boto3 = MagicMock()
mock_botocore = MagicMock()
mock_botocore_exceptions = MagicMock()

class MockClientError(Exception):
    def __init__(self, error_response, operation_name):
        self.response = error_response
        self.operation_name = operation_name
        super().__init__(str(error_response))

mock_botocore_exceptions.ClientError = MockClientError

sys.modules["boto3"] = mock_boto3
sys.modules["botocore"] = mock_botocore
sys.modules["botocore.exceptions"] = mock_botocore_exceptions

# Environment setup
os.environ["STAGE"] = "dev"
os.environ["EMPLOYEE_TABLE_NAME"] = "onboarding-employee-profile-dev"
os.environ["DOCUMENTS_BUCKET_NAME"] = "onboarding-documents-dev-123456789012"
os.environ["PROVISION_FUNCTION_NAME"] = "onboarding-provision-cognito-user-dev"
os.environ["USER_POOL_ID"] = "ap-south-1_dummyPoolId"
os.environ["AWS_DEFAULT_REGION"] = "ap-south-1"

import importlib.util

spec_create = importlib.util.spec_from_file_location("create_app", "backend/functions/createEmployeeProfile/app.py")
create_module = importlib.util.module_from_spec(spec_create)
spec_create.loader.exec_module(create_module)

spec_provision = importlib.util.spec_from_file_location("provision_app", "backend/functions/provisionCognitoUser/app.py")
provision_module = importlib.util.module_from_spec(spec_provision)
spec_provision.loader.exec_module(provision_module)

class TestCreateEmployeeProfile(unittest.TestCase):

    def setUp(self):
        self.mock_dynamo = MagicMock()
        self.mock_table = MagicMock()
        self.mock_dynamo.Table.return_value = self.mock_table
        create_module.dynamodb = self.mock_dynamo

        self.mock_lambda = MagicMock()
        create_module.lambda_client = self.mock_lambda

    def test_create_employee_success(self):
        valid_payload = {
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
            "department": "Engineering",
            "role": "Software Engineer",
            "manager": "Alex Manager",
            "joining_date": "2026-10-01",
            "employment_type": "full-time"
        }

        event = {
            "httpMethod": "POST",
            "body": json.dumps(valid_payload)
        }

        response = create_module.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 201)

        body = json.loads(response["body"])
        self.assertIn("employee_id", body)
        self.assertEqual(body["status"], "created")

        # Verify DynamoDB put_item called with correct schema
        self.mock_table.put_item.assert_called_once()
        item = self.mock_table.put_item.call_args[1]["Item"]
        self.assertEqual(item["email"], "jane.doe@example.com")
        self.assertEqual(item["name"], "Jane Doe")
        self.assertEqual(item["department"], "Engineering")
        self.assertEqual(item["role"], "Software Engineer")
        self.assertEqual(item["manager"], "Alex Manager")
        self.assertEqual(item["joining_date"], "2026-10-01")
        self.assertEqual(item["employment_type"], "full-time")
        self.assertEqual(item["onboarding_status"]["document_collection"], "pending")
        self.assertEqual(item["onboarding_status"]["it_provisioning"], "pending")
        self.assertEqual(item["onboarding_status"]["policy_signoff"], "pending")
        self.assertEqual(item["onboarding_status"]["manager_intro"], "pending")
        self.assertIn("documents", item["onboarding_status"])
        self.assertIn("created_at", item)

        # Verify asynchronous invocation of provisionCognitoUser
        self.mock_lambda.invoke.assert_called_once()
        invoke_kwargs = self.mock_lambda.invoke.call_args[1]
        self.assertEqual(invoke_kwargs["InvocationType"], "Event")
        self.assertEqual(invoke_kwargs["FunctionName"], "onboarding-provision-cognito-user-dev")
        payload = json.loads(invoke_kwargs["Payload"])
        self.assertEqual(payload["email"], "jane.doe@example.com")
        self.assertEqual(payload["employee_id"], item["employee_id"])

    def test_missing_fields_validation(self):
        event = {
            "httpMethod": "POST",
            "body": json.dumps({
                "name": "Jane Doe",
                "email": "jane.doe@example.com"
            })
        }
        response = create_module.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertIn("Missing required fields", body["error"])

    def test_invalid_email_validation(self):
        event = {
            "httpMethod": "POST",
            "body": json.dumps({
                "name": "Jane Doe",
                "email": "invalid-email",
                "department": "Engineering",
                "role": "Engineer",
                "manager": "Alex",
                "joining_date": "2026-10-01",
                "employment_type": "full-time"
            })
        }
        response = create_module.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertIn("Invalid email address format", body["error"])


class TestProvisionCognitoUser(unittest.TestCase):

    def setUp(self):
        self.mock_cognito = MagicMock()
        provision_module.cognito_client = self.mock_cognito

        self.mock_dynamo = MagicMock()
        self.mock_table = MagicMock()
        self.mock_dynamo.Table.return_value = self.mock_table
        provision_module.dynamodb = self.mock_dynamo

    def test_provision_user_success(self):
        self.mock_cognito.admin_create_user.return_value = {
            "User": {
                "Attributes": [
                    {"Name": "sub", "Value": "cognito-sub-12345"},
                    {"Name": "email", "Value": "jane.doe@example.com"}
                ]
            }
        }

        event = {
            "employee_id": "emp-uuid-12345",
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
            "department": "Engineering",
            "role": "Software Engineer"
        }

        response = provision_module.lambda_handler(event, None)
        self.assertEqual(response["status"], "provisioned")
        self.assertEqual(response["cognito_sub"], "cognito-sub-12345")

        # Verify admin_create_user attributes
        self.mock_cognito.admin_create_user.assert_called_once()
        create_args = self.mock_cognito.admin_create_user.call_args[1]
        self.assertEqual(create_args["Username"], "jane.doe@example.com")
        attrs = {a["Name"]: a["Value"] for a in create_args["UserAttributes"]}
        self.assertEqual(attrs["custom:employee_id"], "emp-uuid-12345")
        self.assertEqual(attrs["custom:role"], "Software Engineer")
        self.assertEqual(attrs["custom:department"], "Engineering")

        # Verify DynamoDB update with cognito_sub
        self.mock_table.update_item.assert_called_once_with(
            Key={"employee_id": "emp-uuid-12345"},
            UpdateExpression="SET cognito_sub = :sub",
            ExpressionAttributeValues={":sub": "cognito-sub-12345"}
        )

if __name__ == "__main__":
    unittest.main()
