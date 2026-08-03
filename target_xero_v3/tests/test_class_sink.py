from unittest.mock import MagicMock

import pytest
from hotglue_etl_exceptions import InvalidPayloadError

from target_xero_v3.sinks.class_sink import ClassSink


@pytest.fixture
def class_sink():
    sink = ClassSink.__new__(ClassSink)
    sink.name = ClassSink.name
    sink.stream_name = "Classes"
    sink.endpoint = ClassSink.endpoint
    sink.record_type = ClassSink.record_type
    sink.id_field = ClassSink.id_field
    sink.xero_client = MagicMock()
    sink.logger = MagicMock()
    sink._target = MagicMock(
        tenant_config={"xero": {"dimension_mappings": {"class": "Classes"}}},
        reference_data={},
    )
    return sink


def _batch_record(
    sink,
    *,
    operation="create",
    external_id="FAKE-CLASS-EXT-001",
    option_id=None,
    name="Fake Class (Sample)",
):
    mapped = {"Name": name, "externalId": external_id}
    if option_id:
        mapped[sink.id_field] = option_id
    return {
        "bId": "0",
        "operation": operation,
        "trackingCategoryId": "00000000-0000-4000-8000-0000000000tc1",
        sink.record_type: mapped,
    }


class TestClassSink:
    def test_creates_tracking_option(self, class_sink):
        records = [_batch_record(class_sink)]
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "Options": [
                {
                    "TrackingOptionID": "00000000-0000-4000-8000-0000000000cl2",
                    "Name": "Fake Class (Sample)",
                }
            ]
        }
        class_sink.xero_client.create_tracking_option.return_value = response

        responses = class_sink.make_batch_request(records)
        result = class_sink.handle_batch_response(responses, records)

        class_sink.xero_client.create_tracking_option.assert_called_once_with(
            "00000000-0000-4000-8000-0000000000tc1",
            {"Name": "Fake Class (Sample)"},
        )
        assert result["state_updates"][0] == {
            "id": "00000000-0000-4000-8000-0000000000cl2",
            "externalId": "FAKE-CLASS-EXT-001",
            "success": True,
        }

    def test_updates_tracking_option(self, class_sink):
        records = [
            _batch_record(
                class_sink,
                operation="update",
                external_id="FAKE-CLASS-EXT-002",
                option_id="00000000-0000-4000-8000-0000000000cl1",
                name="Fake Class Updated (Sample)",
            )
        ]
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "Options": [
                {
                    "TrackingOptionID": "00000000-0000-4000-8000-0000000000cl1",
                    "Name": "Fake Class Updated (Sample)",
                }
            ]
        }
        class_sink.xero_client.update_tracking_option.return_value = response

        responses = class_sink.make_batch_request(records)
        result = class_sink.handle_batch_response(responses, records)

        class_sink.xero_client.update_tracking_option.assert_called_once_with(
            "00000000-0000-4000-8000-0000000000tc1",
            "00000000-0000-4000-8000-0000000000cl1",
            {"Name": "Fake Class Updated (Sample)"},
        )
        assert result["state_updates"][0] == {
            "id": "00000000-0000-4000-8000-0000000000cl1",
            "externalId": "FAKE-CLASS-EXT-002",
            "success": True,
            "is_updated": True,
        }

    def test_raises_when_tracking_category_missing(self, class_sink):
        with pytest.raises(InvalidPayloadError, match="Tracking category 'Classes' not found"):
            class_sink.process_batch_record(
                {"externalId": "FAKE-CLASS-EXT-003", "name": "Missing Category"},
                0,
                {"TrackingCategory": None, "Classes": []},
            )
