import pytest
from hotglue_etl_exceptions import InvalidPayloadError

from target_xero_v3.mappers.invoice_line_item_schema_mapper import (
    InvoiceLineItemSchemaMapper,
)


class TestInvoiceLineItemSchemaMapper:
    def test_maps_line_item_fields(self, invoice_line_item_record, empty_reference_data):
        payload = InvoiceLineItemSchemaMapper(
            invoice_line_item_record, "InvoiceLineItems", reference_data=empty_reference_data
        ).to_xero()

        assert payload["Description"] == "Line item only"
        assert payload["ItemCode"] == "FAKE-ITEM-CODE-001"
        assert payload["Quantity"] == 1
        assert payload["UnitAmount"] == 50.0
        assert payload["AccountCode"] == "200"
        assert payload["TaxType"] == "OUTPUT"
        assert payload["Tracking"][0]["TrackingOptionID"] == (
            "00000000-0000-4000-8000-0000000000cl1"
        )

    def test_maps_item_by_id(self, empty_reference_data):
        record = {
            "description": "Lookup by item id",
            "itemId": "00000000-0000-4000-8000-0000000000i1",
            "quantity": 1,
            "unitPrice": 25.0,
            "accountNumber": "200",
        }
        reference_data = {
            **empty_reference_data,
            "Items": [
                {
                    "ItemID": "00000000-0000-4000-8000-0000000000i1",
                    "Code": "FAKE-ITEM-CODE-001",
                    "Name": "Fake Item (Sample)",
                }
            ],
        }
        payload = InvoiceLineItemSchemaMapper(
            record, "InvoiceLineItems", reference_data=reference_data
        ).to_xero()

        assert payload["ItemCode"] == "FAKE-ITEM-CODE-001"

    def test_maps_account_by_id(self, empty_reference_data):
        record = {
            "description": "Lookup by account id",
            "quantity": 1,
            "unitPrice": 25.0,
            "accountId": "00000000-0000-4000-8000-0000000000a1",
        }
        payload = InvoiceLineItemSchemaMapper(
            record, "InvoiceLineItems", reference_data=empty_reference_data
        ).to_xero()

        assert payload["AccountCode"] == "200"

    def test_raises_when_item_not_found(self, empty_reference_data):
        record = {
            "description": "Missing item",
            "itemId": "00000000-0000-4000-8000-000000000099",
            "accountNumber": "200",
        }
        with pytest.raises(InvalidPayloadError, match="Item with Id="):
            InvoiceLineItemSchemaMapper(
                record, "InvoiceLineItems", reference_data=empty_reference_data
            ).to_xero()

    def test_raises_when_tracking_option_not_found(self, empty_reference_data):
        record = {
            "description": "Missing class",
            "accountNumber": "200",
            "className": "Missing Class",
        }
        with pytest.raises(InvalidPayloadError, match="Tracking option"):
            InvoiceLineItemSchemaMapper(
                record, "InvoiceLineItems", reference_data=empty_reference_data
            ).to_xero()

    def test_maps_line_item_id_for_update(self, empty_reference_data):
        record = {
            "id": "00000000-0000-4000-8000-0000000000li1",
            "description": "Updated line",
            "accountNumber": "200",
        }
        payload = InvoiceLineItemSchemaMapper(
            record, "InvoiceLineItems", reference_data=empty_reference_data
        ).to_xero()

        assert payload["LineItemID"] == "00000000-0000-4000-8000-0000000000li1"
