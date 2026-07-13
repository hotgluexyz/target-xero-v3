import pytest
from hotglue_etl_exceptions import InvalidPayloadError

from target_xero_v3.mappers.bill_payment_schema_mapper import BillPaymentSchemaMapper
from target_xero_v3.mappers.invoice_payment_schema_mapper import InvoicePaymentSchemaMapper


class TestInvoicePaymentSchemaMapper:
    def test_maps_invoice_payment_to_xero_payload(
        self, invoice_payment_record, invoice_payment_reference_data
    ):
        payload = InvoicePaymentSchemaMapper(
            invoice_payment_record,
            "InvoicePayments",
            reference_data=invoice_payment_reference_data,
        ).to_xero()

        assert payload == {
            "Invoice": {"InvoiceID": "00000000-0000-4000-8000-0000000000inv1"},
            "Account": {"AccountID": "00000000-0000-4000-8000-0000000000b1"},
            "Amount": 50.0,
            "Date": "2026-07-15",
            "CurrencyRate": 1.0,
            "Reference": "PAY-001",
        }

    def test_resolves_parent_by_invoice_id(self, invoice_payment_reference_data):
        record = {
            "invoiceId": "00000000-0000-4000-8000-0000000000inv1",
            "accountName": "Business Bank",
            "amount": 10.0,
            "paymentDate": "2026-07-15",
        }
        payload = InvoicePaymentSchemaMapper(
            record, "InvoicePayments", reference_data=invoice_payment_reference_data
        ).to_xero()

        assert payload["Invoice"]["InvoiceID"] == "00000000-0000-4000-8000-0000000000inv1"

    def test_rejects_accpay_parent(self, invoice_payment_reference_data):
        reference_data = {
            **invoice_payment_reference_data,
            "Invoices": [
                {
                    "InvoiceID": "00000000-0000-4000-8000-0000000000bill1",
                    "InvoiceNumber": "HG-BILL-001",
                    "Type": "ACCPAY",
                }
            ],
        }
        record = {
            "invoiceNumber": "HG-BILL-001",
            "accountName": "Business Bank",
            "amount": 10.0,
            "paymentDate": "2026-07-15",
        }
        with pytest.raises(InvalidPayloadError, match="Expected ACCREC"):
            InvoicePaymentSchemaMapper(
                record, "InvoicePayments", reference_data=reference_data
            ).to_xero()

    def test_rejects_payment_updates(self, invoice_payment_reference_data):
        record = {
            "id": "00000000-0000-4000-8000-0000000000pay1",
            "invoiceNumber": "HG-INV-EXISTING",
            "accountName": "Business Bank",
            "amount": 10.0,
            "paymentDate": "2026-07-15",
        }
        with pytest.raises(InvalidPayloadError, match="not supported"):
            InvoicePaymentSchemaMapper(
                record, "InvoicePayments", reference_data=invoice_payment_reference_data
            ).to_xero()

    def test_rejects_non_payment_account(self, invoice_payment_reference_data):
        record = {
            "invoiceNumber": "HG-INV-EXISTING",
            "accountName": "Sales",
            "amount": 10.0,
            "paymentDate": "2026-07-15",
        }
        with pytest.raises(InvalidPayloadError, match="cannot receive payments"):
            InvoicePaymentSchemaMapper(
                record, "InvoicePayments", reference_data=invoice_payment_reference_data
            ).to_xero()


class TestBillPaymentSchemaMapper:
    def test_maps_bill_payment_to_xero_payload(
        self, bill_payment_record, bill_payment_reference_data
    ):
        payload = BillPaymentSchemaMapper(
            bill_payment_record,
            "BillPayments",
            reference_data=bill_payment_reference_data,
        ).to_xero()

        assert payload == {
            "Invoice": {"InvoiceID": "00000000-0000-4000-8000-0000000000bill1"},
            "Account": {"AccountID": "00000000-0000-4000-8000-0000000000b1"},
            "Amount": 25.0,
            "Date": "2026-07-15",
        }

    def test_rejects_accrec_parent(self, bill_payment_reference_data):
        reference_data = {
            **bill_payment_reference_data,
            "Bills": [
                {
                    "InvoiceID": "00000000-0000-4000-8000-0000000000inv1",
                    "InvoiceNumber": "HG-INV-001",
                    "Type": "ACCREC",
                }
            ],
        }
        record = {
            "billNumber": "HG-INV-001",
            "accountName": "Business Bank",
            "amount": 10.0,
            "paymentDate": "2026-07-15",
        }
        with pytest.raises(InvalidPayloadError, match="Expected ACCPAY"):
            BillPaymentSchemaMapper(
                record, "BillPayments", reference_data=reference_data
            ).to_xero()
