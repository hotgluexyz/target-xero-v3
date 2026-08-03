import pytest
from hotglue_etl_exceptions import InvalidPayloadError

from target_xero_v3.mappers.bill_line_item_schema_mapper import BillLineItemSchemaMapper
from target_xero_v3.mappers.bill_schema_mapper import BillSchemaMapper


class TestBillLineItemSchemaMapper:
    def test_maps_bill_line_item_fields(self, bill_line_item_record, empty_reference_data):
        payload = BillLineItemSchemaMapper(
            bill_line_item_record, "BillLineItems", reference_data=empty_reference_data
        ).to_xero()

        assert payload["Description"] == "Bill line only"
        assert payload["AccountCode"] == "400"
        assert payload["Quantity"] == 2
        assert payload["UnitAmount"] == 30.0
        assert payload["TaxType"] == "INPUT"
        assert payload["Tracking"][0]["Name"] == "Classes"

    def test_maps_expense_amount(self, bill_expense_record, empty_reference_data):
        payload = BillLineItemSchemaMapper(
            bill_expense_record, "BillLineItems", reference_data=empty_reference_data
        ).to_xero()

        assert payload["LineAmount"] == 15.0
        assert payload["AccountCode"] == "400"


class TestBillSchemaMapper:
    def test_maps_new_bill_to_xero_payload(self, bill_record, empty_reference_data):
        reference_data = {
            **empty_reference_data,
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
        }
        payload = BillSchemaMapper(
            bill_record, "Bills", reference_data=reference_data
        ).to_xero()

        assert payload["Type"] == "ACCPAY"
        assert payload["InvoiceNumber"] == "HG-BILL-001"
        assert payload["Reference"] == "Fake bill reference"
        assert payload["Status"] == "DRAFT"
        assert payload["LineAmountTypes"] == "Exclusive"
        assert payload["Contact"]["ContactID"] == "00000000-0000-4000-8000-0000000000v1"
        assert len(payload["LineItems"]) == 2
        assert payload["LineItems"][0]["ItemCode"] == "FAKE-ITEM-CODE-001"
        assert payload["LineItems"][1]["LineAmount"] == 25.0

    def test_maps_existing_bill_by_id(self, bill_reference_data):
        record = {
            "id": "00000000-0000-4000-8000-0000000000bill1",
            "vendorId": "00000000-0000-4000-8000-0000000000v1",
            "lineItems": [{"description": "Updated line", "accountNumber": "400"}],
        }
        payload = BillSchemaMapper(record, "Bills", reference_data=bill_reference_data).to_xero()

        assert payload["InvoiceID"] == "00000000-0000-4000-8000-0000000000bill1"

    def test_maps_is_draft_false_to_authorised(self, empty_reference_data):
        record = {
            "vendorName": "Fake Vendor LLC (Sample)",
            "isDraft": False,
            "lineItems": [{"description": "Line", "accountNumber": "400"}],
        }
        payload = BillSchemaMapper(record, "Bills", reference_data=empty_reference_data).to_xero()

        assert payload["Status"] == "AUTHORISED"

    def test_explicit_status_overrides_is_draft(self, empty_reference_data):
        record = {
            "vendorName": "Fake Vendor LLC (Sample)",
            "status": "SUBMITTED",
            "isDraft": True,
            "lineItems": [{"description": "Line", "accountNumber": "400"}],
        }
        payload = BillSchemaMapper(record, "Bills", reference_data=empty_reference_data).to_xero()

        assert payload["Status"] == "SUBMITTED"

    def test_raises_when_vendor_missing(self, empty_reference_data):
        record = {"lineItems": [{"description": "Line", "accountNumber": "400"}]}
        with pytest.raises(InvalidPayloadError, match="Vendor contact is required"):
            BillSchemaMapper(record, "Bills", reference_data=empty_reference_data).to_xero()

    def test_maps_tax_included(self, empty_reference_data):
        record = {
            "vendorName": "Fake Vendor LLC (Sample)",
            "taxIncluded": True,
            "lineItems": [{"description": "Line", "accountNumber": "400"}],
        }
        payload = BillSchemaMapper(record, "Bills", reference_data=empty_reference_data).to_xero()

        assert payload["LineAmountTypes"] == "Inclusive"
