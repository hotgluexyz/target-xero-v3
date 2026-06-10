"""Unit tests for XeroBatchSink batch request and response handling."""

import json
from unittest.mock import MagicMock

import pytest

from target_xero_v3.base_sinks import XeroBatchSink


@pytest.fixture
def batch_sink():
    sink = XeroBatchSink.__new__(XeroBatchSink)
    sink.stream_name = "Customers"
    sink.record_type = "Contact"
    sink.endpoint = "Contacts"
    sink.xero_client = MagicMock()
    sink.logger = MagicMock()
    return sink


def _batch_record(
    *,
    operation="create",
    external_id="FAKE-CUSTOMER-EXT-001",
    contact_id=None,
    name="Fake Customer Co (Sample)",
):
    contact = {
        "Name": name,
        "IsCustomer": True,
        "IsSupplier": False,
        "externalId": external_id,
    }
    if contact_id:
        contact["ContactID"] = contact_id
    return {
        "bId": "0",
        "operation": operation,
        "Contact": contact,
    }


def _mock_response(*, status_code=200, contacts=None, text=""):
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    response.json.return_value = {"Contacts": contacts or []}
    return response


class TestMakeBatchRequest:
    def test_strips_external_id_before_push(self, batch_sink):
        records = [_batch_record(external_id="FAKE-CUSTOMER-EXT-001")]
        batch_sink.xero_client.push.return_value = _mock_response()

        batch_sink.make_batch_request(records)

        payload = batch_sink.xero_client.push.call_args[0][1]
        contact = payload["Contacts"][0]
        assert "externalId" not in contact
        assert contact["Name"] == "Fake Customer Co (Sample)"

    def test_calls_xero_client_push_with_contacts_endpoint(self, batch_sink):
        records = [_batch_record()]
        expected_response = _mock_response()
        batch_sink.xero_client.push.return_value = expected_response

        response = batch_sink.make_batch_request(records)

        batch_sink.xero_client.push.assert_called_once_with(
            "Contacts",
            {
                "Contacts": [
                    {
                        "Name": "Fake Customer Co (Sample)",
                        "IsCustomer": True,
                        "IsSupplier": False,
                    }
                ]
            },
        )
        assert response is expected_response


class TestHandleBatchResponse:
    def test_returns_failure_when_response_is_none(self, batch_sink):
        records = [_batch_record(external_id="FAKE-CUSTOMER-EXT-001")]

        result = batch_sink.handle_batch_response(None, records)

        assert result == {
            "state_updates": [
                {
                    "success": False,
                    "externalId": "FAKE-CUSTOMER-EXT-001",
                    "error": "No response",
                }
            ]
        }

    def test_returns_failure_when_response_is_not_success(self, batch_sink):
        records = [_batch_record(external_id="FAKE-CUSTOMER-EXT-002")]
        response = _mock_response(status_code=400, text="Bad Request")

        result = batch_sink.handle_batch_response(response, records)

        assert result == {
            "state_updates": [
                {
                    "success": False,
                    "externalId": "FAKE-CUSTOMER-EXT-002",
                    "error": "Bad Request",
                }
            ]
        }

    def test_returns_success_state_for_created_contact(self, batch_sink):
        records = [_batch_record(external_id="FAKE-CUSTOMER-EXT-003")]
        response = _mock_response(
            contacts=[
                {
                    "ContactID": "00000000-0000-4000-8000-0000000000c1",
                    "HasValidationErrors": False,
                }
            ]
        )

        result = batch_sink.handle_batch_response(response, records)

        assert result == {
            "state_updates": [
                {
                    "id": "00000000-0000-4000-8000-0000000000c1",
                    "externalId": "FAKE-CUSTOMER-EXT-003",
                    "success": True,
                }
            ]
        }

    def test_marks_update_operations_as_updated(self, batch_sink):
        records = [
            _batch_record(
                operation="update",
                external_id="FAKE-CUSTOMER-EXT-004",
                contact_id="00000000-0000-4000-8000-0000000000c1",
            )
        ]
        response = _mock_response(
            contacts=[
                {
                    "ContactID": "00000000-0000-4000-8000-0000000000c1",
                    "HasValidationErrors": False,
                }
            ]
        )

        result = batch_sink.handle_batch_response(response, records)

        assert result["state_updates"][0] == {
            "id": "00000000-0000-4000-8000-0000000000c1",
            "externalId": "FAKE-CUSTOMER-EXT-004",
            "success": True,
            "is_updated": True,
        }

    def test_returns_validation_error_state(self, batch_sink):
        records = [_batch_record(external_id="FAKE-CUSTOMER-EXT-005")]
        validation_errors = [{"Message": "Email address is invalid"}]
        response = _mock_response(
            contacts=[
                {
                    "ContactID": "00000000-0000-4000-8000-0000000000c2",
                    "HasValidationErrors": True,
                    "ValidationErrors": validation_errors,
                }
            ]
        )

        result = batch_sink.handle_batch_response(response, records)

        assert result == {
            "state_updates": [
                {
                    "success": False,
                    "externalId": "FAKE-CUSTOMER-EXT-005",
                    "error": json.dumps(validation_errors),
                }
            ]
        }

    def test_handles_multiple_records_in_order(self, batch_sink):
        records = [
            _batch_record(external_id="FAKE-CUSTOMER-EXT-006", name="Fake Customer A"),
            _batch_record(external_id="FAKE-CUSTOMER-EXT-007", name="Fake Customer B"),
        ]
        response = _mock_response(
            contacts=[
                {
                    "ContactID": "00000000-0000-4000-8000-0000000000a1",
                    "HasValidationErrors": False,
                },
                {
                    "ContactID": "00000000-0000-4000-8000-0000000000a2",
                    "HasValidationErrors": True,
                    "ValidationErrors": [{"Message": "Duplicate name"}],
                },
            ]
        )

        result = batch_sink.handle_batch_response(response, records)

        assert result["state_updates"][0] == {
            "id": "00000000-0000-4000-8000-0000000000a1",
            "externalId": "FAKE-CUSTOMER-EXT-006",
            "success": True,
        }
        assert result["state_updates"][1] == {
            "success": False,
            "externalId": "FAKE-CUSTOMER-EXT-007",
            "error": json.dumps([{"Message": "Duplicate name"}]),
        }
