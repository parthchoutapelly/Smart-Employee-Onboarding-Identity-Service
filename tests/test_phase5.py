"""
Phase 5 — Testing & Integration

Tests:
1.  stageDocumentCollection marks document_collection as in_progress (not complete)
2.  stageDocumentCollection raises ValueError on missing employee_id
3.  checkDocumentCollection returns pending when status is pending
4.  checkDocumentCollection returns complete when status is complete
5.  checkDocumentCollection returns complete when all documents are verified
6.  checkDocumentCollection raises ValueError on missing employee_id
7.  checkDocumentCollection raises ValueError when employee profile not found
8.  createEmployeeProfile calls sfn_client.start_execution after DynamoDB success
9.  createEmployeeProfile passes correct employee_id as execution input
10. createEmployeeProfile returns HTTP 500 if start_execution raises
11. createEmployeeProfile still invokes provisionCognitoUser after successful StartExecution
12. ASL polling loop: correct states and transitions exist
"""
import json
import os
import sys
import unittest
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Mock boto3 / botocore before importing any handler modules
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------
os.environ["STAGE"] = "dev"
os.environ["EMPLOYEE_TABLE_NAME"] = "onboarding-employee-profile-dev"
os.environ["DOCUMENTS_BUCKET_NAME"] = "onboarding-documents-dev-123456789012"
os.environ["PROVISION_FUNCTION_NAME"] = "onboarding-provision-cognito-user-dev"
os.environ["STATE_MACHINE_ARN"] = (
    "arn:aws:states:ap-south-1:331262815638:stateMachine:onboarding-state-machine-dev"
)
os.environ["AWS_DEFAULT_REGION"] = "ap-south-1"

import importlib.util


def load_module(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


doc_coll_mod = load_module(
    "doc_coll_p5", "backend/functions/stageDocumentCollection/app.py"
)
check_doc_mod = load_module(
    "check_doc", "backend/functions/checkDocumentCollection/app.py"
)
create_mod = load_module(
    "create_p5", "backend/functions/createEmployeeProfile/app.py"
)


# ===========================================================================
# 1–2: stageDocumentCollection
# ===========================================================================
class TestStageDocumentCollectionPhase5(unittest.TestCase):

    def setUp(self):
        self.mock_dynamo = MagicMock()
        self.mock_table = MagicMock()
        self.mock_dynamo.Table.return_value = self.mock_table
        doc_coll_mod.dynamodb = self.mock_dynamo

    def test_marks_in_progress_not_complete(self):
        """stageDocumentCollection must set in_progress, never complete."""
        result = doc_coll_mod.lambda_handler({"employee_id": "emp-test-1"}, None)

        self.assertEqual(result["employee_id"], "emp-test-1")
        self.assertEqual(result["stage"], "document_collection")
        self.assertEqual(result["status"], "in_progress")

        # Verify DynamoDB write value
        call_kwargs = self.mock_table.update_item.call_args[1]
        self.assertEqual(
            call_kwargs["ExpressionAttributeValues"][":status"], "in_progress"
        )
        self.assertNotEqual(
            call_kwargs["ExpressionAttributeValues"][":status"], "complete",
            "stageDocumentCollection must NOT write 'complete' prematurely"
        )

    def test_raises_on_missing_employee_id(self):
        with self.assertRaises(ValueError):
            doc_coll_mod.lambda_handler({}, None)


# ===========================================================================
# 3–7: checkDocumentCollection
# ===========================================================================
class TestCheckDocumentCollection(unittest.TestCase):

    def setUp(self):
        self.mock_dynamo = MagicMock()
        self.mock_table = MagicMock()
        self.mock_dynamo.Table.return_value = self.mock_table
        check_doc_mod.dynamodb = self.mock_dynamo

    def _make_item(self, doc_collection_status, documents=None):
        return {
            "Item": {
                "employee_id": "emp-check-1",
                "onboarding_status": {
                    "document_collection": doc_collection_status,
                    "documents": documents or {
                        "id_proof": "pending",
                        "degree_certificate": "pending",
                        "offer_letter": "pending"
                    }
                }
            }
        }

    def test_returns_pending_when_status_is_pending(self):
        self.mock_table.get_item.return_value = self._make_item("pending")
        result = check_doc_mod.lambda_handler({"employee_id": "emp-check-1"}, None)
        self.assertEqual(result["employee_id"], "emp-check-1")
        self.assertEqual(result["document_collection"], "pending")

    def test_returns_complete_when_status_is_complete(self):
        self.mock_table.get_item.return_value = self._make_item(
            "complete",
            documents={
                "id_proof": "verified",
                "degree_certificate": "verified",
                "offer_letter": "verified"
            }
        )
        result = check_doc_mod.lambda_handler({"employee_id": "emp-check-1"}, None)
        self.assertEqual(result["document_collection"], "complete")

    def test_returns_in_progress_status(self):
        """Returns whatever the DynamoDB value is, including in_progress."""
        self.mock_table.get_item.return_value = self._make_item("in_progress")
        result = check_doc_mod.lambda_handler({"employee_id": "emp-check-1"}, None)
        self.assertEqual(result["document_collection"], "in_progress")

    def test_raises_value_error_on_missing_employee_id(self):
        with self.assertRaises(ValueError):
            check_doc_mod.lambda_handler({}, None)

    def test_raises_value_error_when_profile_not_found(self):
        self.mock_table.get_item.return_value = {}   # no Item key
        with self.assertRaises(ValueError):
            check_doc_mod.lambda_handler({"employee_id": "nonexistent"}, None)

    def test_raises_runtime_error_on_dynamodb_failure(self):
        self.mock_table.get_item.side_effect = MockClientError(
            {"Error": {"Code": "InternalServerError", "Message": "DynamoDB unavailable"}},
            "GetItem"
        )
        with self.assertRaises(RuntimeError):
            check_doc_mod.lambda_handler({"employee_id": "emp-check-1"}, None)

    def test_returns_pending_as_default_when_status_key_missing(self):
        """If onboarding_status has no document_collection key, default to pending."""
        self.mock_table.get_item.return_value = {
            "Item": {
                "employee_id": "emp-check-2",
                "onboarding_status": {}
            }
        }
        result = check_doc_mod.lambda_handler({"employee_id": "emp-check-2"}, None)
        self.assertEqual(result["document_collection"], "pending")


# ===========================================================================
# 8–11: createEmployeeProfile — Step Functions integration
# ===========================================================================
class TestCreateEmployeeProfilePhase5(unittest.TestCase):

    def setUp(self):
        self.mock_dynamo = MagicMock()
        self.mock_table = MagicMock()
        self.mock_dynamo.Table.return_value = self.mock_table
        create_mod.dynamodb = self.mock_dynamo

        self.mock_lambda = MagicMock()
        create_mod.lambda_client = self.mock_lambda

        self.mock_sfn = MagicMock()
        create_mod.sfn_client = self.mock_sfn

    def _valid_event(self, email="test@example.com"):
        return {
            "httpMethod": "POST",
            "body": json.dumps({
                "name": "Test Employee",
                "email": email,
                "department": "Engineering",
                "role": "SDE",
                "manager": "Manager Name",
                "joining_date": "2026-10-01",
                "employment_type": "Full-Time"
            })
        }

    def test_calls_start_execution_after_dynamo_success(self):
        response = create_mod.lambda_handler(self._valid_event(), None)
        self.assertEqual(response["statusCode"], 201)
        self.mock_sfn.start_execution.assert_called_once()

    def test_start_execution_input_contains_correct_employee_id(self):
        response = create_mod.lambda_handler(self._valid_event(), None)
        self.assertEqual(response["statusCode"], 201)

        body = json.loads(response["body"])
        generated_id = body["employee_id"]

        call_kwargs = self.mock_sfn.start_execution.call_args[1]
        self.assertEqual(
            call_kwargs["stateMachineArn"],
            os.environ["STATE_MACHINE_ARN"]
        )
        execution_input = json.loads(call_kwargs["input"])
        self.assertEqual(execution_input["employee_id"], generated_id)

    def test_returns_500_when_start_execution_raises(self):
        self.mock_sfn.start_execution.side_effect = Exception("Step Functions unavailable")

        response = create_mod.lambda_handler(self._valid_event(), None)
        # Must return 500, not 201
        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertIn("workflow", body["error"].lower())

    def test_cognito_provisioning_still_called_on_success(self):
        """Cognito provisioning lambda invoke must still be dispatched after successful StartExecution."""
        response = create_mod.lambda_handler(self._valid_event(), None)
        self.assertEqual(response["statusCode"], 201)
        self.mock_lambda.invoke.assert_called_once()
        invoke_kwargs = self.mock_lambda.invoke.call_args[1]
        self.assertEqual(invoke_kwargs["InvocationType"], "Event")
        self.assertIn("onboarding-provision-cognito-user", invoke_kwargs["FunctionName"])

    def test_sfn_not_called_when_dynamo_put_fails(self):
        """If DynamoDB fails, Step Functions must NOT be called."""
        self.mock_table.put_item.side_effect = MockClientError(
            {"Error": {"Code": "InternalServerError", "Message": "DynamoDB error"}},
            "PutItem"
        )
        response = create_mod.lambda_handler(self._valid_event(), None)
        self.assertEqual(response["statusCode"], 500)
        self.mock_sfn.start_execution.assert_not_called()


# ===========================================================================
# 12: ASL polling loop structure
# ===========================================================================
class TestASLPollingLoop(unittest.TestCase):

    def test_polling_states_exist_with_correct_transitions(self):
        asl_path = "backend/statemachines/onboarding-state-machine.asl.json"
        with open(asl_path, "r", encoding="utf-8") as f:
            asl = json.load(f)

        states = asl["States"]

        # DocumentCollection must transition to the checker (not ITProvisioning directly)
        self.assertEqual(states["DocumentCollection"]["Next"], "CheckDocumentCollection")

        # CheckDocumentCollection must exist with retry/catch
        check_state = states["CheckDocumentCollection"]
        self.assertEqual(check_state["Type"], "Task")
        self.assertIn("Retry", check_state)
        self.assertIn("Catch", check_state)
        self.assertEqual(check_state["Next"], "DocumentCollectionChoice")

        # Choice state must route complete -> ITProvisioning, default -> WaitForDocuments
        choice_state = states["DocumentCollectionChoice"]
        self.assertEqual(choice_state["Type"], "Choice")
        complete_choice = choice_state["Choices"][0]
        self.assertEqual(complete_choice["StringEquals"], "complete")
        self.assertEqual(complete_choice["Next"], "ITProvisioning")
        self.assertEqual(choice_state["Default"], "WaitForDocuments")

        # Wait state must route back to CheckDocumentCollection (no infinite direct loop)
        wait_state = states["WaitForDocuments"]
        self.assertEqual(wait_state["Type"], "Wait")
        self.assertGreater(wait_state["Seconds"], 0, "Wait must have a positive duration")
        self.assertEqual(wait_state["Next"], "CheckDocumentCollection")

        # Downstream stages preserved
        for stage in ["ITProvisioning", "PolicySignOff", "ManagerIntro"]:
            self.assertIn(stage, states)
            self.assertIn("Retry", states[stage])

        self.assertEqual(states["Complete"]["Type"], "Succeed")
        self.assertEqual(states["Failed"]["Type"], "Fail")


if __name__ == "__main__":
    unittest.main()
