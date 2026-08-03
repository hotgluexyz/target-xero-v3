from typing import Dict, List

from hotglue_models_accounting.accounting import Item

from target_xero_v3.base_sinks import XeroBatchSink
from target_xero_v3.mappers.item_schema_mapper import ItemSchemaMapper


class ItemSink(XeroBatchSink):
    name = "Items"
    unified_schema = Item
    auto_validate_unified_schema = True
    endpoint = "Items"
    record_type = "Item"
    id_field = "ItemID"

    def get_batch_reference_data(self, records: List) -> Dict:
        existing_items = []
        item_ids = {record["id"] for record in records if record.get("id")}
        item_codes = {record["itemNumber"] for record in records if record.get("itemNumber")}
        item_names = set()
        for record in records:
            for field in ("name", "displayName"):
                if record.get(field):
                    item_names.add(record[field])

        for item_id in item_ids:
            matches = self.xero_client.filter(
                "Items",
                where=self.xero_client._build_where_clause("ItemID", item_id, "guid"),
            )
            if matches:
                existing_items.extend(matches)

        for item_code in item_codes:
            matches = self.xero_client.filter(
                "Items",
                where=self.xero_client._build_where_clause("Code", item_code, "string"),
            )
            if matches:
                existing_items.extend(matches)

        for item_name in item_names:
            matches = self.xero_client.filter(
                "Items",
                where=self.xero_client._build_where_clause("Name", item_name, "string"),
            )
            if matches:
                existing_items.extend(matches)

        reference_data = {**self._target.reference_data, self.name: existing_items}
        if any(record.get("accounts") for record in records):
            reference_data["Accounts"] = self.xero_client.filter("Accounts") or []
        return reference_data

    def process_batch_record(self, record: dict, index: int, reference_data: dict) -> dict:
        mapped_record = ItemSchemaMapper(
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
