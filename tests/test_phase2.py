import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

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
os.environ["REMINDER_THRESHOLD_HOURS"] = "24"
os.environ["SES_SENDER_EMAIL"] = "onboarding-noreply@example.com"
os.environ["AWS_DEFAULT_REGION"] = "ap-south-1"

import importlib.util

def load_module(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

doc_coll_mod = load_module("doc_coll", "backend/functions/stageDocumentCollection/app.py")
it_prov_mod = load_module("it_prov", "backend/functions/stageITProvisioning/app.py")
policy_mod = load_module("policy", "backend/functions/stagePolicySignOff/app.py")
mgr_intro_mod = load_module("mgr_intro", "backend/functions/stageManagerIntro/app.py")
status_mod = load_module("status_mod", "backend/functions/getOnboardingStatus/app.py")
reminder_mod = load_module("reminder_mod", "backend/functions/sendReminderEmail/app.py")


class TestStageLambdas(unittest.TestCase):

    def setUp(self):
        self.mock_dynamo = MagicMock()
        self.mock_table = MagicMock()
        self.mock_dynamo.Table.return_value = self.mock_table

    def test_stage_document_collection(self):
        doc_coll_mod.dynamodb = self.mock_dynamo
        event = {"employee_id": "test-uuid-1"}
        result = doc_coll_mod.lambda_handler(event, None)

        self.assertEqual(result["employee_id"], "test-uuid-1")
        self.assertEqual(result["stage"], "document_collection")
        self.assertEqual(result["status"], "complete")
        self.mock_table.update_item.assert_called_once()
        call_kwargs = self.mock_table.update_item.call_args[1]
        self.assertEqual(call_kwargs["Key"], {"employee_id": "test-uuid-1"})

    def test_stage_it_provisioning(self):
        it_prov_mod.dynamodb = self.mock_dynamo
        event = {"employee_id": "test-uuid-2"}
        result = it_prov_mod.lambda_handler(event, None)

        self.assertEqual(result["employee_id"], "test-uuid-2")
        self.assertEqual(result["stage"], "it_provisioning")
        self.assertEqual(result["status"], "complete")
        self.mock_table.update_item.assert_called_once()

    def test_stage_policy_signoff(self):
        policy_mod.dynamodb = self.mock_dynamo
        event = {"employee_id": "test-uuid-3"}
        result = policy_mod.lambda_handler(event, None)

        self.assertEqual(result["employee_id"], "test-uuid-3")
        self.assertEqual(result["stage"], "policy_signoff")
        self.assertEqual(result["status"], "complete")
        self.mock_table.update_item.assert_called_once()

    def test_stage_manager_intro(self):
        mgr_intro_mod.dynamodb = self.mock_dynamo
        event = {"employee_id": "test-uuid-4"}
        result = mgr_intro_mod.lambda_handler(event, None)

        self.assertEqual(result["employee_id"], "test-uuid-4")
        self.assertEqual(result["stage"], "manager_intro")
        self.assertEqual(result["status"], "complete")
        self.mock_table.update_item.assert_called_once()

    def test_stage_missing_employee_id(self):
        doc_coll_mod.dynamodb = self.mock_dynamo
        with self.assertRaises(ValueError):
            doc_coll_mod.lambda_handler({}, None)


class TestGetOnboardingStatus(unittest.TestCase):

    def setUp(self):
        self.mock_dynamo = MagicMock()
        self.mock_table = MagicMock()
        self.mock_dynamo.Table.return_value = self.mock_table
        status_mod.dynamodb = self.mock_dynamo

    def test_get_status_found(self):
        self.mock_table.get_item.return_value = {
            "Item": {
                "employee_id": "emp-101",
                "onboarding_status": {
                    "document_collection": "complete",
                    "it_provisioning": "in_progress",
                    "policy_signoff": "pending",
                    "manager_intro": "pending"
                }
            }
        }
        event = {
            "httpMethod": "GET",
            "pathParameters": {"employee_id": "emp-101"}
        }
        response = status_mod.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 200)

        body = json.loads(response["body"])
        self.assertEqual(body["employee_id"], "emp-101")
        self.assertEqual(body["onboarding_status"]["document_collection"], "complete")
        self.assertEqual(body["onboarding_status"]["it_provisioning"], "in_progress")

    def test_get_status_not_found(self):
        self.mock_table.get_item.return_value = {}
        event = {
            "httpMethod": "GET",
            "pathParameters": {"employee_id": "non-existent"}
        }
        response = status_mod.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 404)
        body = json.loads(response["body"])
        self.assertIn("not found", body["error"].lower())

    def test_get_status_missing_param(self):
        event = {
            "httpMethod": "GET",
            "pathParameters": None
        }
        response = status_mod.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 400)


class TestSendReminderEmail(unittest.TestCase):

    def setUp(self):
        self.mock_dynamo = MagicMock()
        self.mock_table = MagicMock()
        self.mock_dynamo.Table.return_value = self.mock_table
        reminder_mod.dynamodb = self.mock_dynamo

        self.mock_ses = MagicMock()
        reminder_mod.ses_client = self.mock_ses

    def test_reminder_dispatches_when_overdue(self):
        old_time = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
        self.mock_table.scan.return_value = {
            "Items": [
                {
                    "employee_id": "overdue-emp-1",
                    "name": "Overdue John",
                    "email": "john@example.com",
                    "manager": "manager@example.com",
                    "created_at": old_time,
                    "onboarding_status": {
                        "document_collection": "pending",
                        "it_provisioning": "pending",
                        "policy_signoff": "complete",
                        "manager_intro": "complete"
                    }
                }
            ]
        }

        event = {"threshold_hours": 24}
        result = reminder_mod.lambda_handler(event, None)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["employees_scanned"], 1)
        self.assertEqual(result["reminders_dispatched_count"], 2)  # doc_coll + it_prov


class TestStateMachineASL(unittest.TestCase):

    def test_asl_syntax_and_flow(self):
        asl_path = "backend/statemachines/onboarding-state-machine.asl.json"
        self.assertTrue(os.path.exists(asl_path), f"ASL file {asl_path} missing")

        with open(asl_path, "r", encoding="utf-8") as f:
            asl = json.load(f)

        self.assertEqual(asl.get("StartAt"), "DocumentCollection")
        states = asl.get("States", {})

        # Verify all sequential states exist
        expected_states = ["DocumentCollection", "ITProvisioning", "PolicySignOff", "ManagerIntro", "Complete", "Failed"]
        for s in expected_states:
            self.assertIn(s, states, f"State {s} missing in ASL")

        # Verify retry and catch logic on DocumentCollection
        doc_state = states["DocumentCollection"]
        self.assertIn("Retry", doc_state)
        self.assertIn("Catch", doc_state)
        self.assertEqual(doc_state["Next"], "ITProvisioning")

        # Verify final states
        self.assertEqual(states["Complete"]["Type"], "Succeed")
        self.assertEqual(states["Failed"]["Type"], "Fail")


if __name__ == "__main__":
    unittest.main()
