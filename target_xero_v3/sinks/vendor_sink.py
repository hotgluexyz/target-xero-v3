from typing import Dict, List

from hotglue_models_accounting.accounting import Vendor

from target_xero_v3.base_sinks import XeroBatchSink
from target_xero_v3.mappers.vendor_schema_mapper import VendorSchemaMapper


class VendorSink(XeroBatchSink):
    name = "Vendors"
    unified_schema = Vendor
    auto_validate_unified_schema = True

    def get_batch_reference_data(self, records: List) -> Dict:
        existing_contacts = []
        contact_ids = {record["id"] for record in records if record.get("id")}
        vendor_names = {record["vendorName"] for record in records if record.get("vendorName")}

        for contact_id in contact_ids:
            matches = self.xero_client.filter(
                "Contacts", where=f'ContactID==guid"{contact_id}"'
            )
            if matches:
                existing_contacts.extend(matches)

        for vendor_name in vendor_names:
            escaped = vendor_name.replace('"', '\\"')
            matches = self.xero_client.filter(
                "Contacts", where=f'Name=="{escaped}"'
            )
            if matches:
                existing_contacts.extend(matches)

        return {**self._target.reference_data, self.name: existing_contacts}

    def process_batch_record(self, record: dict, index: int, reference_data: dict) -> dict:
        mapped_record = VendorSchemaMapper(
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
