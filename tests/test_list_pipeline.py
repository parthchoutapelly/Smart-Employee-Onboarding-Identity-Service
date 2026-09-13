import json
import os
import sys
import unittest
from unittest.mock import MagicMock, call

# Mock boto3 and botocore before importing handlers
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

os.environ["STAGE"] = "dev"
os.environ["EMPLOYEE_TABLE_NAME"] = "onboarding-employee-profile-dev"
os.environ["AWS_DEFAULT_REGION"] = "ap-south-1"

import importlib.util

spec = importlib.util.spec_from_file_location(
    "list_pipeline_mod",
    "backend/functions/listOnboardingEmployees/app.py"
)
list_pipeline_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(list_pipeline_mod)


class TestListOnboardingEmployees(unittest.TestCase):

    def setUp(self):
        self.mock_dynamo = MagicMock()
        self.mock_table = MagicMock()
        self.mock_dynamo.Table.return_value = self.mock_table
        list_pipeline_mod.dynamodb = self.mock_dynamo
        os.environ["EMPLOYEE_TABLE_NAME"] = "onboarding-employee-profile-dev"

    def test_list_employees_single_page_success(self):
        self.mock_table.scan.return_value = {
            "Items": [
                {
                    "employee_id": "uuid-1",
                    "name": "Jane Doe",
                    "email": "jane@example.com",
                    "department": "Engineering",
                    "role": "Software Engineer",
                    "manager": "Bob Mgr",
                    "joining_date": "2026-10-01",
                    "employment_type": "Full-Time",
                    "created_at": "2026-09-13T10:00:00Z",
                    "onboarding_status": {
                        "document_collection": "complete",
                        "it_provisioning": "in_progress",
                        "policy_signoff": "pending",
                        "manager_intro": "pending"
                    }
                },
                {
                    "employee_id": "uuid-2",
                    "name": "John Smith",
                    "email": "john@example.com",
                    "department": "Sales",
                    "role": "Account Exec",
                    "manager": "Alice Mgr",
                    "joining_date": "2026-10-15",
                    "employment_type": "Full-Time",
                    "created_at": "2026-09-13T12:00:00Z",
                    "onboarding_status": {
                        "document_collection": "in_progress",
                        "it_provisioning": "pending",
                        "policy_signoff": "pending",
                        "manager_intro": "pending"
                    }
                }
            ]
        }

        event = {"httpMethod": "GET"}
        response = list_pipeline_mod.lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["headers"]["Access-Control-Allow-Origin"], "*")

        body = json.loads(response["body"])
        self.assertIsInstance(body, list)
        self.assertEqual(len(body), 2)
        # Should be sorted descending by created_at (uuid-2 is newer)
        self.assertEqual(body[0]["employee_id"], "uuid-2")
        self.assertEqual(body[0]["department"], "Sales")
        self.assertEqual(body[0]["onboarding_status"]["document_collection"], "in_progress")
        self.assertEqual(body[1]["employee_id"], "uuid-1")

    def test_list_employees_multi_page_pagination(self):
        # First page returns LastEvaluatedKey, second page finishes
        self.mock_table.scan.side_effect = [
            {
                "Items": [
                    {
                        "employee_id": "uuid-page-1",
                        "name": "Alice Page",
                        "created_at": "2026-09-10T10:00:00Z"
                    }
                ],
                "LastEvaluatedKey": {"employee_id": "uuid-page-1"}
            },
            {
                "Items": [
                    {
                        "employee_id": "uuid-page-2",
                        "name": "Bob Page",
                        "created_at": "2026-09-11T10:00:00Z"
                    }
                ]
            }
        ]

        event = {"httpMethod": "GET"}
        response = list_pipeline_mod.lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(len(body), 2)
        self.assertEqual(self.mock_table.scan.call_count, 2)
        # Check fallback defaults for status when onboarding_status is missing
        self.assertEqual(body[0]["onboarding_status"]["document_collection"], "pending")
        self.assertEqual(body[0]["onboarding_status"]["it_provisioning"], "pending")

    def test_list_employees_options_preflight(self):
        event = {"httpMethod": "OPTIONS"}
        response = list_pipeline_mod.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 200)
        self.assertIn("Access-Control-Allow-Origin", response["headers"])

    def test_list_employees_dynamodb_error(self):
        self.mock_table.scan.side_effect = MockClientError(
            {"Error": {"Message": "ProvisionedThroughputExceededException"}},
            "Scan"
        )
        event = {"httpMethod": "GET"}
        response = list_pipeline_mod.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertIn("error", body)

    def test_list_employees_missing_table_env_var(self):
        del os.environ["EMPLOYEE_TABLE_NAME"]
        event = {"httpMethod": "GET"}
        response = list_pipeline_mod.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertIn("error", body)

    def test_template_contains_pipeline_resources(self):
        with open("template.yaml", "r") as f:
            template_content = f.read()

        # Check IAM Role
        self.assertIn("onboarding-list-employees-role-${Stage}", template_content)
        self.assertIn("dynamodb:Scan", template_content)
        self.assertIn("onboarding-list-employees-${Stage}", template_content)

        # Check API Route
        self.assertIn("Path: /onboarding/pipeline", template_content)
        self.assertIn("Method: get", template_content)
