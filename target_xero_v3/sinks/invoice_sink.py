from typing import Dict, List

from hotglue_models_accounting.accounting import Invoice

from target_xero_v3.base_sinks import XeroBatchSink
from target_xero_v3.mappers.invoice_schema_mapper import InvoiceSchemaMapper
from target_xero_v3.sinks.transaction_reference import build_transaction_reference_data

INVOICE_FILTER_MAPPINGS = [
    {"field_from": "id", "xero_field": "InvoiceID", "filter_type": "guid"},
    {"field_from": "invoiceNumber", "xero_field": "InvoiceNumber", "filter_type": "string"},
]

CUSTOMER_FILTER_MAPPINGS = [
    {"field_from": "customerId", "xero_field": "ContactID", "filter_type": "guid"},
    {"field_from": "customerNumber", "xero_field": "ContactNumber", "filter_type": "string"},
    {"field_from": "customerName", "xero_field": "Name", "filter_type": "string"},
]


class InvoiceSink(XeroBatchSink):
    name = "Invoices"
    unified_schema = Invoice
    auto_validate_unified_schema = True
    endpoint = "Invoices"
    record_type = "Invoice"
    id_field = "InvoiceID"

    def get_batch_reference_data(self, records: List) -> Dict:
        return build_transaction_reference_data(
            self.xero_client,
            self._target,
            records,
            entity_stream=self.name,
            entity_filter_mappings=INVOICE_FILTER_MAPPINGS,
            entity_id_field=self.id_field,
            contact_filter_mappings=CUSTOMER_FILTER_MAPPINGS,
            contact_key="Customers",
        )

    def process_batch_record(self, record: dict, index: int, reference_data: dict) -> dict:
        mapped_record = InvoiceSchemaMapper(
            record, self.name, reference_data=reference_data
        ).to_xero()
        if record.get("externalId"):
            mapped_record["externalId"] = record["externalId"]
        operation_type = "update" if self.id_field in mapped_record else "create"
        return {
            "bId": str(index),
            "operation": operation_type,
            self.record_type: mapped_record,
        }
