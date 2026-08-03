from unittest.mock import MagicMock

import pytest
from hotglue_etl_exceptions import InvalidPayloadError

from target_xero_v3.sinks.invoice_sink import InvoiceSink


@pytest.fixture
def invoice_sink():
    sink = InvoiceSink.__new__(InvoiceSink)
    sink.name = InvoiceSink.name
    sink.stream_name = "Invoices"
    sink.endpoint = InvoiceSink.endpoint
    sink.record_type = InvoiceSink.record_type
    sink.id_field = InvoiceSink.id_field
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
    external_id="FAKE-INVOICE-EXT-001",
    invoice_id=None,
    invoice_number="HG-INV-001",
):
    mapped = {
        "Type": "ACCREC",
        "InvoiceNumber": invoice_number,
        "Contact": {"ContactID": "00000000-0000-4000-8000-0000000000c1"},
        "LineItems": [{"Description": "Consulting", "AccountCode": "200"}],
        "externalId": external_id,
    }
    if invoice_id:
        mapped[sink.id_field] = invoice_id
    return {
        "bId": "0",
        "operation": operation,
        sink.record_type: mapped,
    }


class TestInvoiceSink:
    def test_process_batch_record(self, invoice_sink, invoice_record):
        reference_data = {
            "Invoices": [],
            "Customers": [
                {
                    "ContactID": "00000000-0000-4000-8000-0000000000c1",
                    "Name": "Fake Customer Co (Sample)",
                }
            ],
            "Items": [
                {
                    "ItemID": "00000000-0000-4000-8000-0000000000i1",
                    "Code": "FAKE-ITEM-CODE-001",
                }
            ],
            "Accounts": [{"AccountID": "00000000-0000-4000-8000-0000000000a1", "Code": "200"}],
            "tenant_config": invoice_sink._target.tenant_config,
            "TrackingCategories": [
                {
                    "TrackingCategoryID": "00000000-0000-4000-8000-0000000000tc1",
                    "Name": "Classes",
                    "Options": [
                        {
                            "TrackingOptionID": "00000000-0000-4000-8000-0000000000cl1",
                            "Name": "Fake Class (Sample)",
                        }
                    ],
                }
            ],
        }
        batch_record = invoice_sink.process_batch_record(invoice_record, 0, reference_data)

        assert batch_record["operation"] == "create"
        assert batch_record["Invoice"]["Type"] == "ACCREC"
        assert batch_record["Invoice"]["externalId"] == "FAKE-INVOICE-EXT-001"

    def test_make_batch_request_strips_external_id(self, invoice_sink):
        records = [_batch_record(invoice_sink)]
        invoice_sink.xero_client.push.return_value = MagicMock()

        invoice_sink.make_batch_request(records)

        payload = invoice_sink.xero_client.push.call_args[0][1]
        assert "externalId" not in payload["Invoices"][0]

    def test_handle_batch_response_success(self, invoice_sink):
        records = [_batch_record(invoice_sink)]
        response = MagicMock()
        response.json.return_value = {
            "Invoices": [
                {
                    "InvoiceID": "00000000-0000-4000-8000-0000000000inv2",
                    "HasValidationErrors": False,
                }
            ]
        }
        result = invoice_sink.handle_batch_response(response, records)

        assert result["state_updates"][0] == {
            "id": "00000000-0000-4000-8000-0000000000inv2",
            "externalId": "FAKE-INVOICE-EXT-001",
            "success": True,
        }

    def test_handle_batch_response_validation_error(self, invoice_sink):
        records = [_batch_record(invoice_sink)]
        response = MagicMock()
        response.json.return_value = {
            "Invoices": [
                {
                    "InvoiceID": "00000000-0000-0000-0000-000000000000",
                    "HasValidationErrors": True,
                    "ValidationErrors": [{"Message": "Invoice not of valid status for modification"}],
                }
            ]
        }
        result = invoice_sink.handle_batch_response(response, records)

        assert result["state_updates"][0] == {
            "success": False,
            "externalId": "FAKE-INVOICE-EXT-001",
            "error": "Invoice not of valid status for modification",
            "hg_error_class": "InvalidPayloadError",
        }

    def test_raises_when_line_item_mapping_fails(self, invoice_sink):
        record = {
            "externalId": "FAKE-INVOICE-EXT-002",
            "customerName": "Fake Customer Co (Sample)",
            "lineItems": [{"description": "Bad line", "itemId": "missing-item-id", "accountNumber": "200"}],
        }
        reference_data = {
            "Invoices": [],
            "Customers": [],
            "Items": [],
            "Accounts": [],
            "tenant_config": invoice_sink._target.tenant_config,
        }
        with pytest.raises(InvalidPayloadError, match="Item with Id="):
            invoice_sink.process_batch_record(record, 0, reference_data)

    def test_get_batch_reference_data_uses_shared_helper(self, invoice_sink, invoice_record):
        invoice_sink.xero_client.get_existing_entities_for_records.side_effect = [
            [],
            [{"ContactID": "00000000-0000-4000-8000-0000000000c1"}],
            [],
        ]
        invoice_sink.xero_client.filter.return_value = [{"AccountID": "a1", "Code": "200"}]

        reference_data = invoice_sink.get_batch_reference_data([invoice_record])

        assert reference_data["Invoices"] == []
        assert reference_data["Customers"][0]["ContactID"] == (
            "00000000-0000-4000-8000-0000000000c1"
        )
        assert invoice_sink.xero_client.get_existing_entities_for_records.call_count == 3
