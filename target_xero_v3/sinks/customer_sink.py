from typing import Dict, List

from hotglue_models_accounting.accounting import Customer

from target_xero_v3.base_sinks import XeroBatchSink
from target_xero_v3.mappers.customer_schema_mapper import CustomerSchemaMapper


class CustomerSink(XeroBatchSink):
    name = "Customers"
    unified_schema = Customer
    auto_validate_unified_schema = False

    def get_batch_reference_data(self, records: List) -> Dict:
        existing_contacts = []
        contact_ids = {record["id"] for record in records if record.get("id")}
        contact_names = set()
        for record in records:
            for field in ("companyName", "customerName", "fullName", "contactName"):
                if record.get(field):
                    contact_names.add(record[field])

        for contact_id in contact_ids:
            matches = self.xero_client.filter(
                "Contacts", where=f'ContactID==guid"{contact_id}"'
            )
            if matches:
                existing_contacts.extend(matches)

        for contact_name in contact_names:
            escaped = contact_name.replace('"', '\\"')
            matches = self.xero_client.filter(
                "Contacts", where=f'Name=="{escaped}"'
            )
            if matches:
                existing_contacts.extend(matches)

        return {**self._target.reference_data, self.name: existing_contacts}

    def process_batch_record(self, record: dict, index: int, reference_data: dict) -> dict:
        mapped_record = CustomerSchemaMapper(
            record, self.name, reference_data=reference_data
        ).to_xero()
        if record.get("externalId"):
            mapped_record["externalId"] = record["externalId"]
        operation_type = "update" if "ContactID" in mapped_record else "create"
        return {
            "bId": str(index),
            "operation": operation_type,
            self.record_type: mapped_record,
        }
