import pytest
from hotglue_etl_exceptions import InvalidPayloadError

from target_xero_v3.mappers.invoice_schema_mapper import InvoiceSchemaMapper


class TestInvoiceSchemaMapper:
    def test_maps_new_invoice_to_xero_payload(self, invoice_record, empty_reference_data):
        reference_data = {
            **empty_reference_data,
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
                    "Name": "Fake Item (Sample)",
                }
            ],
        }
        payload = InvoiceSchemaMapper(
            invoice_record, "Invoices", reference_data=reference_data
        ).to_xero()

        assert payload["Type"] == "ACCREC"
        assert payload["InvoiceNumber"] == "HG-INV-001"
        assert payload["Reference"] == "Fake invoice reference"
        assert payload["CurrencyCode"] == "USD"
        assert payload["CurrencyRate"] == 1.0
        assert payload["Status"] == "DRAFT"
        assert payload["Date"] == "2026-07-01"
        assert payload["DueDate"] == "2026-07-31"
        assert payload["Contact"]["ContactID"] == "00000000-0000-4000-8000-0000000000c1"
        assert len(payload["LineItems"]) == 1
        assert payload["LineItems"][0]["ItemCode"] == "FAKE-ITEM-CODE-001"
        assert "InvoiceID" not in payload

    def test_maps_existing_invoice_by_id(self, invoice_reference_data):
        record = {
            "id": "00000000-0000-4000-8000-0000000000inv1",
            "customerId": "00000000-0000-4000-8000-0000000000c1",
            "lineItems": [{"description": "Updated line", "accountNumber": "200"}],
        }
        payload = InvoiceSchemaMapper(
            record, "Invoices", reference_data=invoice_reference_data
        ).to_xero()

        assert payload["InvoiceID"] == "00000000-0000-4000-8000-0000000000inv1"

    def test_maps_existing_invoice_by_invoice_number(self, invoice_reference_data):
        record = {
            "invoiceNumber": "HG-INV-EXISTING",
            "customerId": "00000000-0000-4000-8000-0000000000c1",
            "lineItems": [{"description": "Updated line", "accountNumber": "200"}],
        }
        payload = InvoiceSchemaMapper(
            record, "Invoices", reference_data=invoice_reference_data
        ).to_xero()

        assert payload["InvoiceID"] == "00000000-0000-4000-8000-0000000000inv1"

    def test_maps_customer_by_name_when_not_in_reference(self, empty_reference_data):
        record = {
            "customerName": "New Customer By Name",
            "lineItems": [{"description": "Line", "accountNumber": "200"}],
        }
        payload = InvoiceSchemaMapper(
            record, "Invoices", reference_data=empty_reference_data
        ).to_xero()

        assert payload["Contact"] == {"Name": "New Customer By Name"}

    def test_raises_when_customer_missing(self, empty_reference_data):
        record = {"lineItems": [{"description": "Line", "accountNumber": "200"}]}
        with pytest.raises(InvalidPayloadError, match="Customer contact is required"):
            InvoiceSchemaMapper(
                record, "Invoices", reference_data=empty_reference_data
            ).to_xero()

    def test_uses_posting_date_over_issue_date(self, empty_reference_data):
        record = {
            "customerName": "Customer",
            "issueDate": "2026-07-01",
            "postingDate": "2026-08-01",
            "lineItems": [{"description": "Line", "accountNumber": "200"}],
        }
        payload = InvoiceSchemaMapper(
            record, "Invoices", reference_data=empty_reference_data
        ).to_xero()

        assert payload["Date"] == "2026-08-01"
