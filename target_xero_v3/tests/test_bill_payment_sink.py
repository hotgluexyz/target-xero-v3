from unittest.mock import MagicMock

import pytest
from hotglue_etl_exceptions import InvalidPayloadError

from target_xero_v3.sinks.bill_payment_sink import BillPaymentSink


@pytest.fixture
def bill_payment_sink():
    sink = BillPaymentSink.__new__(BillPaymentSink)
    sink.name = BillPaymentSink.name
    sink.stream_name = "BillPayments"
    sink.endpoint = BillPaymentSink.endpoint
    sink.record_type = BillPaymentSink.record_type
    sink.id_field = BillPaymentSink.id_field
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
    external_id="FAKE-BILL-PAYMENT-EXT-001",
):
    return {
        "bId": "0",
        "operation": "create",
        sink.record_type: {
            "Invoice": {"InvoiceID": "00000000-0000-4000-8000-0000000000bill1"},
            "Account": {"AccountID": "00000000-0000-4000-8000-0000000000b1"},
            "Amount": 25.0,
            "Date": "2026-07-15",
            "externalId": external_id,
        },
    }


class TestBillPaymentSink:
    def test_get_batch_reference_data(self, bill_payment_sink, bill_payment_record):
        bill_payment_sink.xero_client.get_existing_entities_for_records.return_value = [
            {
                "InvoiceID": "00000000-0000-4000-8000-0000000000bill1",
                "Type": "ACCPAY",
            }
        ]
        bill_payment_sink.xero_client.filter.return_value = [
            {"AccountID": "00000000-0000-4000-8000-0000000000b1", "Type": "BANK"}
        ]

        reference_data = bill_payment_sink.get_batch_reference_data([bill_payment_record])

        assert reference_data["Bills"][0]["Type"] == "ACCPAY"
        bill_payment_sink.xero_client.get_existing_entities_for_records.assert_called_once()

    def test_process_batch_record(self, bill_payment_sink, bill_payment_record):
        reference_data = {
            "Bills": [
                {
                    "InvoiceID": "00000000-0000-4000-8000-0000000000bill1",
                    "InvoiceNumber": "HG-BILL-EXISTING",
                    "Type": "ACCPAY",
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
        batch_record = bill_payment_sink.process_batch_record(
            bill_payment_record, 0, reference_data
        )

        assert batch_record["operation"] == "create"
        assert batch_record["Payment"]["Amount"] == 25.0

    def test_raises_when_payment_id_provided(self, bill_payment_sink):
        record = {
            "id": "00000000-0000-4000-8000-0000000000pay1",
            "billNumber": "HG-BILL-EXISTING",
            "accountName": "Business Bank",
            "amount": 10.0,
            "paymentDate": "2026-07-15",
        }
        reference_data = {
            "Bills": [
                {
                    "InvoiceID": "00000000-0000-4000-8000-0000000000bill1",
                    "InvoiceNumber": "HG-BILL-EXISTING",
                    "Type": "ACCPAY",
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
            bill_payment_sink.process_batch_record(record, 0, reference_data)
