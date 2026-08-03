from typing import Dict, List

from hotglue_models_accounting.accounting import Bill

from target_xero_v3.base_sinks import XeroBatchSink
from target_xero_v3.mappers.bill_schema_mapper import BillSchemaMapper
from target_xero_v3.sinks.transaction_reference import build_transaction_reference_data

BILL_FILTER_MAPPINGS = [
    {"field_from": "id", "xero_field": "InvoiceID", "filter_type": "guid"},
    {"field_from": "billNumber", "xero_field": "InvoiceNumber", "filter_type": "string"},
]

VENDOR_FILTER_MAPPINGS = [
    {"field_from": "vendorId", "xero_field": "ContactID", "filter_type": "guid"},
    {"field_from": "vendorNumber", "xero_field": "ContactNumber", "filter_type": "string"},
    {"field_from": "vendorName", "xero_field": "Name", "filter_type": "string"},
]


class BillSink(XeroBatchSink):
    name = "Bills"
    unified_schema = Bill
    auto_validate_unified_schema = True
    endpoint = "Invoices"
    record_type = "Invoice"
    id_field = "InvoiceID"

    def get_batch_reference_data(self, records: List) -> Dict:
        return build_transaction_reference_data(
            self.xero_client,
            self._target,
            records,
            entity_stream="Invoices",
            entity_reference_key=self.name,
            entity_filter_mappings=BILL_FILTER_MAPPINGS,
            entity_id_field=self.id_field,
            contact_filter_mappings=VENDOR_FILTER_MAPPINGS,
            contact_key="Vendors",
            nested_keys=("lineItems", "expenses"),
        )

    def process_batch_record(self, record: dict, index: int, reference_data: dict) -> dict:
        mapped_record = BillSchemaMapper(
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
