from typing import Dict, List

from hotglue_models_accounting.accounting import InvoicePayment

from target_xero_v3.mappers.invoice_payment_schema_mapper import InvoicePaymentSchemaMapper
from target_xero_v3.sinks.payment_reference import (
    INVOICE_PARENT_FILTER_MAPPINGS,
    build_payment_reference_data,
)
from target_xero_v3.sinks.payment_sink import PaymentBatchSink


class InvoicePaymentSink(PaymentBatchSink):
    name = "InvoicePayments"
    unified_schema = InvoicePayment
    auto_validate_unified_schema = True

    def get_batch_reference_data(self, records: List) -> Dict:
        return build_payment_reference_data(
            self.xero_client,
            self._target,
            records,
            parent_filter_mappings=INVOICE_PARENT_FILTER_MAPPINGS,
            parent_reference_key="Invoices",
        )

    def map_record(self, record: dict, reference_data: dict) -> dict:
        return InvoicePaymentSchemaMapper(
            record, self.name, reference_data=reference_data
        ).to_xero()
