from unittest.mock import MagicMock

import pytest
from hotglue_etl_exceptions import InvalidPayloadError

from target_xero_v3.sinks.bill_sink import BillSink


@pytest.fixture
def bill_sink():
    sink = BillSink.__new__(BillSink)
    sink.name = BillSink.name
    sink.stream_name = "Bills"
    sink.endpoint = BillSink.endpoint
    sink.record_type = BillSink.record_type
    sink.id_field = BillSink.id_field
    sink.xero_client = MagicMock()
    sink.logger = MagicMock()
    sink._target = MagicMock(
        tenant_config={"xero": {"dimension_mappings": {"class": "Classes"}}},
        reference_data={"Currencies": [], "Organisation": []},
    )
    return sink


def _batch_record(
    sink,
    *,
    operation="create",
    external_id="FAKE-BILL-EXT-001",
    bill_id=None,
    bill_number="HG-BILL-001",
):
    mapped = {
        "Type": "ACCPAY",
        "InvoiceNumber": bill_number,
        "Contact": {"ContactID": "00000000-0000-4000-8000-0000000000v1"},
        "LineItems": [{"Description": "Supplies", "AccountCode": "400"}],
        "externalId": external_id,
    }
    if bill_id:
        mapped[sink.id_field] = bill_id
    return {
        "bId": "0",
        "operation": operation,
        sink.record_type: mapped,
    }


class TestBillSink:
    def test_get_batch_reference_data_uses_shared_helper(self, bill_sink, bill_record):
        bill_sink.xero_client.get_existing_entities_for_records.side_effect = [
            [],
            [{"ContactID": "00000000-0000-4000-8000-0000000000v1"}],
            [],
        ]
        bill_sink.xero_client.filter.return_value = [{"AccountID": "a1", "Code": "400"}]

        reference_data = bill_sink.get_batch_reference_data([bill_record])

        assert reference_data["Bills"] == []
        assert reference_data["Vendors"][0]["ContactID"] == (
            "00000000-0000-4000-8000-0000000000v1"
        )
        assert bill_sink.xero_client.get_existing_entities_for_records.call_count == 3

    def test_process_batch_record(self, bill_sink, bill_record):
        reference_data = {
            "Bills": [],
            "Vendors": [
                {
                    "ContactID": "00000000-0000-4000-8000-0000000000v1",
                    "Name": "Fake Vendor LLC (Sample)",
                }
            ],
            "Items": [
                {
                    "ItemID": "00000000-0000-4000-8000-0000000000i1",
                    "Code": "FAKE-ITEM-CODE-001",
                }
            ],
            "Accounts": [{"AccountID": "00000000-0000-4000-8000-0000000000a2", "Code": "400"}],
            "tenant_config": bill_sink._target.tenant_config,
        }
        batch_record = bill_sink.process_batch_record(bill_record, 0, reference_data)

        assert batch_record["operation"] == "create"
        assert batch_record["Invoice"]["Type"] == "ACCPAY"
        assert len(batch_record["Invoice"]["LineItems"]) == 2

    def test_handle_batch_response_validation_error(self, bill_sink):
        records = [_batch_record(bill_sink)]
        response = MagicMock()
        response.json.return_value = {
            "Invoices": [
                {
                    "InvoiceID": "00000000-0000-0000-0000-000000000000",
                    "HasValidationErrors": True,
                    "ValidationErrors": [
                        {"Message": "The TaxType code INVALIDTAX does not exist"}
                    ],
                }
            ]
        }
        result = bill_sink.handle_batch_response(response, records)

        assert result["state_updates"][0]["success"] is False
        assert "INVALIDTAX" in result["state_updates"][0]["error"]

    def test_raises_when_expense_mapping_fails(self, bill_sink):
        record = {
            "externalId": "FAKE-BILL-EXT-002",
            "vendorName": "Fake Vendor LLC (Sample)",
            "expenses": [{"description": "Bad expense", "itemId": "missing-item-id"}],
        }
        reference_data = {
            "Bills": [],
            "Vendors": [],
            "Items": [],
            "Accounts": [],
            "tenant_config": bill_sink._target.tenant_config,
        }
        with pytest.raises(InvalidPayloadError, match="Item with Id="):
            bill_sink.process_batch_record(record, 0, reference_data)
