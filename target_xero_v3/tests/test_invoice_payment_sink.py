from unittest.mock import MagicMock

import pytest
from hotglue_etl_exceptions import InvalidPayloadError

from target_xero_v3.sinks.invoice_payment_sink import InvoicePaymentSink


@pytest.fixture
def invoice_payment_sink():
    sink = InvoicePaymentSink.__new__(InvoicePaymentSink)
    sink.name = InvoicePaymentSink.name
    sink.stream_name = "InvoicePayments"
    sink.endpoint = InvoicePaymentSink.endpoint
    sink.record_type = InvoicePaymentSink.record_type
    sink.id_field = InvoicePaymentSink.id_field
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
    external_id="FAKE-INVOICE-PAYMENT-EXT-001",
    payment_id=None,
):
    mapped = {
        "Invoice": {"InvoiceID": "00000000-0000-4000-8000-0000000000inv1"},
        "Account": {"AccountID": "00000000-0000-4000-8000-0000000000b1"},
        "Amount": 50.0,
        "Date": "2026-07-15",
        "externalId": external_id,
    }
    if payment_id:
        mapped[sink.id_field] = payment_id
    return {
        "bId": "0",
        "operation": "create",
        sink.record_type: mapped,
    }


class TestInvoicePaymentSink:
    def test_get_batch_reference_data(self, invoice_payment_sink, invoice_payment_record):
        invoice_payment_sink.xero_client.get_existing_entities_for_records.return_value = [
            {
                "InvoiceID": "00000000-0000-4000-8000-0000000000inv1",
                "Type": "ACCREC",
            }
        ]
        invoice_payment_sink.xero_client.filter.return_value = [
            {"AccountID": "00000000-0000-4000-8000-0000000000b1", "Type": "BANK"}
        ]

        reference_data = invoice_payment_sink.get_batch_reference_data([invoice_payment_record])

        assert reference_data["Invoices"][0]["Type"] == "ACCREC"
        assert reference_data["Accounts"][0]["Type"] == "BANK"
        invoice_payment_sink.xero_client.get_existing_entities_for_records.assert_called_once()

    def test_process_batch_record(self, invoice_payment_sink, invoice_payment_record):
        reference_data = {
            "Invoices": [
                {
                    "InvoiceID": "00000000-0000-4000-8000-0000000000inv1",
                    "InvoiceNumber": "HG-INV-EXISTING",
                    "Type": "ACCREC",
                }
            ],
            "Accounts": [
                {
                    "AccountID": "00000000-0000-4000-8000-0000000000b1",
                    "Name": "Business Bank",
                    "Type": "BANK",
                }
            ],
        }
        batch_record = invoice_payment_sink.process_batch_record(
            invoice_payment_record, 0, reference_data
        )

        assert batch_record["operation"] == "create"
        assert batch_record["Payment"]["Amount"] == 50.0
        assert batch_record["Payment"]["externalId"] == "FAKE-INVOICE-PAYMENT-EXT-001"

    def test_make_batch_request_uses_put(self, invoice_payment_sink):
        records = [_batch_record(invoice_payment_sink)]
        invoice_payment_sink.xero_client.create_payments.return_value = MagicMock()

        invoice_payment_sink.make_batch_request(records)

        payload = invoice_payment_sink.xero_client.create_payments.call_args[0][0]
        assert "externalId" not in payload["Payments"][0]

    def test_handle_batch_response_success(self, invoice_payment_sink):
        records = [_batch_record(invoice_payment_sink)]
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "Payments": [
                {
                    "PaymentID": "00000000-0000-4000-8000-0000000000pay1",
                    "HasValidationErrors": False,
                }
            ]
        }
        result = invoice_payment_sink.handle_batch_response(response, records)

        assert result["state_updates"][0] == {
            "id": "00000000-0000-4000-8000-0000000000pay1",
            "externalId": "FAKE-INVOICE-PAYMENT-EXT-001",
            "success": True,
        }

    def test_handle_batch_response_validation_error(self, invoice_payment_sink):
        records = [_batch_record(invoice_payment_sink)]
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "Payments": [
                {
                    "PaymentID": "00000000-0000-0000-0000-000000000000",
                    "HasValidationErrors": True,
                    "ValidationErrors": [{"Message": "Payment amount exceeds amount outstanding"}],
                }
            ]
        }
        result = invoice_payment_sink.handle_batch_response(response, records)

        assert result["state_updates"][0]["success"] is False
        assert "amount outstanding" in result["state_updates"][0]["error"]

    def test_raises_when_payment_id_provided(self, invoice_payment_sink):
        record = {
            "id": "00000000-0000-4000-8000-0000000000pay1",
            "invoiceNumber": "HG-INV-EXISTING",
            "accountName": "Business Bank",
            "amount": 10.0,
            "paymentDate": "2026-07-15",
        }
        reference_data = {
            "Invoices": [
                {
                    "InvoiceID": "00000000-0000-4000-8000-0000000000inv1",
                    "InvoiceNumber": "HG-INV-EXISTING",
                    "Type": "ACCREC",
                }
            ],
            "Accounts": [
                {
                    "AccountID": "00000000-0000-4000-8000-0000000000b1",
                    "Name": "Business Bank",
                    "Type": "BANK",
                }
            ],
        }
        with pytest.raises(InvalidPayloadError, match="not supported"):
            invoice_payment_sink.process_batch_record(record, 0, reference_data)
