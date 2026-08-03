from typing import Dict, List

from hotglue_models_accounting.accounting import BillPayment

from target_xero_v3.mappers.bill_payment_schema_mapper import BillPaymentSchemaMapper
from target_xero_v3.sinks.payment_reference import (
    BILL_PARENT_FILTER_MAPPINGS,
    build_payment_reference_data,
)
from target_xero_v3.sinks.payment_sink import PaymentBatchSink


class BillPaymentSink(PaymentBatchSink):
    name = "BillPayments"
    unified_schema = BillPayment
    auto_validate_unified_schema = True

    def get_batch_reference_data(self, records: List) -> Dict:
        return build_payment_reference_data(
            self.xero_client,
            self._target,
            records,
            parent_filter_mappings=BILL_PARENT_FILTER_MAPPINGS,
            parent_reference_key="Bills",
        )

    def map_record(self, record: dict, reference_data: dict) -> dict:
        return BillPaymentSchemaMapper(
            record, self.name, reference_data=reference_data
        ).to_xero()
