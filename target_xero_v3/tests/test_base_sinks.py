"""Unit tests for XeroBatchSink batch request and response handling."""

from unittest.mock import MagicMock

import pytest
from hotglue_etl_exceptions import InvalidCredentialsError

from target_xero_v3.sinks.customer_sink import CustomerSink


@pytest.fixture
def batch_sink():
    sink = CustomerSink.__new__(CustomerSink)
    sink.name = CustomerSink.name
    sink.stream_name = "Customers"
    sink.endpoint = CustomerSink.endpoint
    sink.record_type = CustomerSink.record_type
    sink.id_field = CustomerSink.id_field
    sink.xero_client = MagicMock()
    sink.logger = MagicMock()
    sink._target = MagicMock(_latest_state={})
    return sink


def _batch_record(
    sink,
    *,
    operation="create",
    external_id="FAKE-CUSTOMER-EXT-001",
    record_id=None,
    name="Fake Customer Co (Sample)",
):
    mapped = {
        "Name": name,
        "externalId": external_id,
    }
    if record_id:
        mapped[sink.id_field] = record_id
    return {
        "bId": "0",
        "operation": operation,
        sink.record_type: mapped,
    }


def _mock_response(sink, *, status_code=200, items=None, text=""):
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    response.json.return_value = {sink.endpoint: items or []}
    return response


class TestMakeBatchRequest:
    def test_strips_external_id_before_push(self, batch_sink):
        records = [_batch_record(batch_sink, external_id="FAKE-CUSTOMER-EXT-001")]
        batch_sink.xero_client.push.return_value = _mock_response(batch_sink)

        batch_sink.make_batch_request(records)

        payload = batch_sink.xero_client.push.call_args[0][1]
        mapped = payload[batch_sink.endpoint][0]
        assert "externalId" not in mapped
        assert mapped["Name"] == "Fake Customer Co (Sample)"

    def test_calls_xero_client_push_with_endpoint(self, batch_sink):
        records = [_batch_record(batch_sink)]
        expected_response = _mock_response(batch_sink)
        batch_sink.xero_client.push.return_value = expected_response

        response = batch_sink.make_batch_request(records)

        batch_sink.xero_client.push.assert_called_once_with(
            batch_sink.endpoint,
            {batch_sink.endpoint: [{"Name": "Fake Customer Co (Sample)"}]},
        )
        assert response is expected_response


class TestHandleBatchResponse:
    def test_returns_success_state_for_created_record(self, batch_sink):
        records = [_batch_record(batch_sink, external_id="FAKE-CUSTOMER-EXT-003")]
        response = _mock_response(
            batch_sink,
            items=[
                {
                    batch_sink.id_field: "00000000-0000-4000-8000-0000000000c1",
                    "HasValidationErrors": False,
                }
            ],
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
                batch_sink,
                operation="update",
                external_id="FAKE-CUSTOMER-EXT-004",
                record_id="00000000-0000-4000-8000-0000000000c1",
            )
        ]
        response = _mock_response(
            batch_sink,
            items=[
                {
                    batch_sink.id_field: "00000000-0000-4000-8000-0000000000c1",
                    "HasValidationErrors": False,
                }
            ],
        )

        result = batch_sink.handle_batch_response(response, records)

        assert result["state_updates"][0] == {
            "id": "00000000-0000-4000-8000-0000000000c1",
            "externalId": "FAKE-CUSTOMER-EXT-004",
            "success": True,
            "is_updated": True,
        }

    def test_returns_validation_error_state(self, batch_sink):
        records = [_batch_record(batch_sink, external_id="FAKE-CUSTOMER-EXT-005")]
        response = _mock_response(
            batch_sink,
            items=[
                {
                    batch_sink.id_field: "00000000-0000-0000-0000-000000000000",
                    "HasValidationErrors": True,
                    "ValidationErrors": [{"Message": "Name cannot be empty"}],
                }
            ],
        )

        result = batch_sink.handle_batch_response(response, records)

        assert result == {
            "state_updates": [
                {
                    "success": False,
                    "externalId": "FAKE-CUSTOMER-EXT-005",
                    "error": "Name cannot be empty",
                    "hg_error_class": "InvalidPayloadError",
                }
            ]
        }

    def test_handles_multiple_records_in_order(self, batch_sink):
        records = [
            _batch_record(batch_sink, external_id="FAKE-CUSTOMER-EXT-006", name="Fake Customer A"),
            _batch_record(batch_sink, external_id="FAKE-CUSTOMER-EXT-007", name="Fake Customer B"),
        ]
        response = _mock_response(
            batch_sink,
            items=[
                {
                    batch_sink.id_field: "00000000-0000-4000-8000-0000000000a1",
                    "HasValidationErrors": False,
                },
                {
                    batch_sink.id_field: "00000000-0000-4000-8000-0000000000a2",
                    "HasValidationErrors": True,
                    "ValidationErrors": [{"Message": "Duplicate name"}],
                },
            ],
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
            "error": "Duplicate name",
            "hg_error_class": "InvalidPayloadError",
        }


class TestCredentialErrorState:
    def test_writes_cached_credential_error_state_for_batch_records(self, batch_sink):
        batch_sink.latest_state = {
            "bookmarks": {"Customers": []},
            "summary": {"Customers": {"success": 0, "fail": 0, "existing": 0, "updated": 0}},
        }
        batch_sink.summary_init = True
        batch_sink.xero_client.push.side_effect = InvalidCredentialsError(
            "Cannot refresh OAuth token: invalid_grant"
        )
        context = {
            "records": [
                {"externalId": "FAKE-CUSTOMER-EXT-008", "companyName": "Fake Co"}
            ]
        }
        batch_sink.get_batch_reference_data = MagicMock(return_value={})
        batch_sink.process_batch_record = MagicMock(
            return_value=_batch_record(batch_sink, external_id="FAKE-CUSTOMER-EXT-008")
        )

        with pytest.raises(InvalidCredentialsError):
            batch_sink.process_batch(context)

        assert batch_sink.latest_state["bookmarks"]["Customers"] == [
            {
                "success": False,
                "error": "Cannot refresh OAuth token: invalid_grant",
                "hg_error_class": "InvalidCredentialsError",
                "externalId": "FAKE-CUSTOMER-EXT-008",
            }
        ]
        assert batch_sink.latest_state["summary"]["Customers"]["fail"] == 1
        assert batch_sink._target._latest_state["bookmarks"]["Customers"] == [
            {
                "success": False,
                "error": "Cannot refresh OAuth token: invalid_grant",
                "hg_error_class": "InvalidCredentialsError",
                "externalId": "FAKE-CUSTOMER-EXT-008",
            }
        ]
