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

class MockConditionalCheckFailedException(MockClientError):
    def __init__(self):
        super().__init__({"Error": {"Code": "ConditionalCheckFailedException", "Message": "Conditional check failed"}}, "UpdateItem")

mock_botocore_exceptions.ClientError = MockClientError
sys.modules["boto3"] = mock_boto3
sys.modules["botocore"] = mock_botocore
sys.modules["botocore.exceptions"] = mock_botocore_exceptions

os.environ["STAGE"] = "dev"
os.environ["EMPLOYEE_TABLE_NAME"] = "onboarding-employee-profile-dev"
os.environ["DOCUMENTS_BUCKET_NAME"] = "onboarding-documents-dev-123456789012"
os.environ["NOTIFICATIONS_TOPIC_ARN"] = "arn:aws:sns:ap-south-1:123456789012:onboarding-hr-notifications-dev"
os.environ["AWS_DEFAULT_REGION"] = "ap-south-1"

import importlib.util

def load_module(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

upload_url_mod = load_module("upload_url_mod", "backend/functions/getUploadUrl/app.py")
validate_doc_mod = load_module("validate_doc_mod", "backend/functions/validateDocument/app.py")


class TestGetUploadUrl(unittest.TestCase):

    def setUp(self):
        self.mock_s3 = MagicMock()
        upload_url_mod.s3_client = self.mock_s3
        self.mock_s3.generate_presigned_url.return_value = "https://s3.amazonaws.com/presigned-put-url"

    def test_valid_payload_all_doc_types_and_extensions(self):
        doc_types = ["id_proof", "degree_certificate", "offer_letter"]
        extensions = ["pdf", "jpg", "png"]

        for dt in doc_types:
            for ext in extensions:
                event = {
                    "httpMethod": "POST",
                    "body": json.dumps({
                        "employee_id": "test-uuid-123",
                        "document_type": dt,
                        "file_extension": ext
                    })
                }
                response = upload_url_mod.lambda_handler(event, None)
                self.assertEqual(response["statusCode"], 200)

                body = json.loads(response["body"])
                self.assertIn("upload_url", body)
                expected_key = f"documents/test-uuid-123/{dt}.{ext}"
                self.assertEqual(body["s3_key"], expected_key)

                # Verify 900s expiration and s3 generate_presigned_url call
                self.mock_s3.generate_presigned_url.assert_called_with(
                    ClientMethod="put_object",
                    Params={
                        "Bucket": "onboarding-documents-dev-123456789012",
                        "Key": expected_key,
                        "ContentType": "application/pdf" if ext == "pdf" else f"image/{'jpeg' if ext == 'jpg' else 'png'}"
                    },
                    ExpiresIn=900
                )

    def test_missing_employee_id(self):
        event = {
            "httpMethod": "POST",
            "body": json.dumps({
                "document_type": "id_proof",
                "file_extension": "pdf"
            })
        }
        response = upload_url_mod.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("employee_id", json.loads(response["body"])["error"])

    def test_invalid_document_type(self):
        event = {
            "httpMethod": "POST",
            "body": json.dumps({
                "employee_id": "emp-123",
                "document_type": "passport_copy",  # Invalid
                "file_extension": "pdf"
            })
        }
        response = upload_url_mod.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Invalid document_type", json.loads(response["body"])["error"])

    def test_invalid_extension(self):
        event = {
            "httpMethod": "POST",
            "body": json.dumps({
                "employee_id": "emp-123",
                "document_type": "id_proof",
                "file_extension": "exe"  # Invalid
            })
        }
        response = upload_url_mod.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Invalid file_extension", json.loads(response["body"])["error"])

    def test_malformed_request_body(self):
        event = {
            "httpMethod": "POST",
            "body": "not-a-json"
        }
        response = upload_url_mod.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 400)


class TestValidateDocument(unittest.TestCase):

    def setUp(self):
        self.mock_s3 = MagicMock()
        self.mock_dynamo = MagicMock()
        self.mock_table = MagicMock()
        self.mock_sns = MagicMock()

        validate_doc_mod.s3_client = self.mock_s3
        validate_doc_mod.dynamodb = self.mock_dynamo
        validate_doc_mod.sns_client = self.mock_sns
        self.mock_dynamo.Table.return_value = self.mock_table

        # Setup exception mocks
        self.mock_table.meta.client.exceptions.ConditionalCheckFailedException = MockConditionalCheckFailedException

        # Default employee exists
        self.mock_table.get_item.return_value = {
            "Item": {
                "employee_id": "emp-uuid-1",
                "onboarding_status": {
                    "document_collection": "pending",
                    "documents": {
                        "id_proof": "pending",
                        "degree_certificate": "pending",
                        "offer_letter": "pending"
                    }
                }
            }
        }

    def _create_s3_event(self, key, bucket="test-bucket"):
        return {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": bucket},
                        "object": {"key": key}
                    }
                }
            ]
        }

    def test_valid_pdf_under_10mb(self):
        self.mock_s3.head_object.return_value = {"ContentLength": 2 * 1024 * 1024}  # 2MB
        event = self._create_s3_event("documents/emp-uuid-1/id_proof.pdf")

        res = validate_doc_mod.lambda_handler(event, None)
        self.assertEqual(res["results"][0]["status"], "verified")
        self.mock_s3.delete_object.assert_not_called()
        self.mock_table.update_item.assert_called()

    def test_valid_jpg_under_10mb(self):
        self.mock_s3.head_object.return_value = {"ContentLength": 10485759}  # 1 byte under 10MB
        event = self._create_s3_event("documents/emp-uuid-1/degree_certificate.jpg")

        res = validate_doc_mod.lambda_handler(event, None)
        self.assertEqual(res["results"][0]["status"], "verified")
        self.mock_s3.delete_object.assert_not_called()

    def test_valid_png_under_10mb(self):
        self.mock_s3.head_object.return_value = {"ContentLength": 500000}  # 500KB
        event = self._create_s3_event("documents/emp-uuid-1/offer_letter.png")

        res = validate_doc_mod.lambda_handler(event, None)
        self.assertEqual(res["results"][0]["status"], "verified")
        self.mock_s3.delete_object.assert_not_called()

    def test_exactly_10mb_rejected(self):
        self.mock_s3.head_object.return_value = {"ContentLength": 10 * 1024 * 1024}  # 10,485,760 bytes
        event = self._create_s3_event("documents/emp-uuid-1/id_proof.pdf")

        res = validate_doc_mod.lambda_handler(event, None)
        self.assertEqual(res["results"][0]["status"], "rejected")
        self.assertIn("exceeds maximum allowed limit", res["results"][0]["reason"])
        # Verify S3 deletion and DynamoDB update
        self.mock_s3.delete_object.assert_called_once_with(Bucket="test-bucket", Key="documents/emp-uuid-1/id_proof.pdf")

    def test_over_10mb_rejected(self):
        self.mock_s3.head_object.return_value = {"ContentLength": 15 * 1024 * 1024}  # 15MB
        event = self._create_s3_event("documents/emp-uuid-1/offer_letter.pdf")

        res = validate_doc_mod.lambda_handler(event, None)
        self.assertEqual(res["results"][0]["status"], "rejected")
        self.mock_s3.delete_object.assert_called_once_with(Bucket="test-bucket", Key="documents/emp-uuid-1/offer_letter.pdf")

    def test_unsupported_extension_rejected(self):
        event = self._create_s3_event("documents/emp-uuid-1/id_proof.docx")

        res = validate_doc_mod.lambda_handler(event, None)
        self.assertEqual(res["results"][0]["status"], "rejected")
        self.assertIn("Unsupported file extension", res["results"][0]["reason"])
        self.mock_s3.delete_object.assert_called_once()

    def test_invalid_document_type_rejected(self):
        event = self._create_s3_event("documents/emp-uuid-1/utility_bill.pdf")

        res = validate_doc_mod.lambda_handler(event, None)
        self.assertEqual(res["results"][0]["status"], "rejected")
        self.assertIn("Invalid document_type", res["results"][0]["reason"])
        self.mock_s3.delete_object.assert_called_once()

    def test_malformed_s3_key_rejected(self):
        event = self._create_s3_event("invalid/path/file.pdf")

        res = validate_doc_mod.lambda_handler(event, None)
        self.assertEqual(res["results"][0]["status"], "rejected")
        self.mock_s3.delete_object.assert_called_once()


class TestCompletionLogic(unittest.TestCase):

    def setUp(self):
        self.mock_s3 = MagicMock()
        self.mock_dynamo = MagicMock()
        self.mock_table = MagicMock()
        self.mock_sns = MagicMock()

        validate_doc_mod.s3_client = self.mock_s3
        validate_doc_mod.dynamodb = self.mock_dynamo
        validate_doc_mod.sns_client = self.mock_sns
        self.mock_dynamo.Table.return_value = self.mock_table
        self.mock_table.meta.client.exceptions.ConditionalCheckFailedException = MockConditionalCheckFailedException

        self.mock_s3.head_object.return_value = {"ContentLength": 1024}

    def test_one_or_two_verified_documents_no_sns(self):
        # 1 document verified
        self.mock_table.get_item.return_value = {
            "Item": {
                "employee_id": "emp-uuid-2",
                "onboarding_status": {
                    "document_collection": "pending",
                    "documents": {
                        "id_proof": "verified",
                        "degree_certificate": "pending",
                        "offer_letter": "pending"
                    }
                }
            }
        }
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "documents/emp-uuid-2/id_proof.pdf"}
                    }
                }
            ]
        }
        validate_doc_mod.lambda_handler(event, None)
        self.mock_sns.publish.assert_not_called()

        # 2 documents verified
        self.mock_table.get_item.return_value = {
            "Item": {
                "employee_id": "emp-uuid-2",
                "onboarding_status": {
                    "document_collection": "pending",
                    "documents": {
                        "id_proof": "verified",
                        "degree_certificate": "verified",
                        "offer_letter": "pending"
                    }
                }
            }
        }
        validate_doc_mod.lambda_handler(event, None)
        self.mock_sns.publish.assert_not_called()

    def test_all_three_verified_triggers_sns_and_status_complete(self):
        # All 3 documents verified
        self.mock_table.get_item.return_value = {
            "Item": {
                "employee_id": "emp-uuid-complete",
                "onboarding_status": {
                    "document_collection": "pending",
                    "documents": {
                        "id_proof": "verified",
                        "degree_certificate": "verified",
                        "offer_letter": "verified"
                    }
                }
            }
        }
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "documents/emp-uuid-complete/offer_letter.pdf"}
                    }
                }
            ]
        }
        validate_doc_mod.lambda_handler(event, None)

        # Verify SNS published exactly once
        self.mock_sns.publish.assert_called_once()
        call_kwargs = self.mock_sns.publish.call_args[1]
        msg = json.loads(call_kwargs["Message"])
        self.assertEqual(msg["employee_id"], "emp-uuid-complete")
        self.assertEqual(msg["event"], "all_documents_verified")

    def test_repeated_processing_does_not_duplicate_sns(self):
        # Table update_item throws ConditionalCheckFailedException because document_collection was already 'complete'
        def update_item_side_effect(**kwargs):
            if "ConditionExpression" in kwargs:
                raise MockConditionalCheckFailedException()
            return {}

        self.mock_table.update_item.side_effect = update_item_side_effect
        self.mock_table.get_item.return_value = {
            "Item": {
                "employee_id": "emp-uuid-already-complete",
                "onboarding_status": {
                    "document_collection": "complete",
                    "documents": {
                        "id_proof": "verified",
                        "degree_certificate": "verified",
                        "offer_letter": "verified"
                    }
                }
            }
        }
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "documents/emp-uuid-already-complete/offer_letter.pdf"}
                    }
                }
            ]
        }
        validate_doc_mod.lambda_handler(event, None)

        # SNS must NOT be called on retry
        self.mock_sns.publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
