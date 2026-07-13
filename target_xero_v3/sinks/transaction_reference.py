from typing import Dict, Iterable, List, Optional, Tuple

DIMENSION_LINE_FIELDS = (
    ("class", "classId", "className"),
    ("location", "locationId", "locationName"),
    ("department", "departmentId", "departmentName"),
)

LINE_ITEM_FILTER_MAPPINGS = [
    {"field_from": "itemId", "xero_field": "ItemID", "filter_type": "guid"},
    {"field_from": "itemNumber", "xero_field": "Code", "filter_type": "string"},
    {"field_from": "itemName", "xero_field": "Name", "filter_type": "string"},
]


def iter_transaction_lines(records: Iterable[dict], nested_keys: Tuple[str, ...]) -> Iterable[dict]:
    for record in records:
        for nested_key in nested_keys:
            for line in record.get(nested_key) or []:
                yield line


def collect_line_item_refs(
    records: List[dict], nested_keys: Tuple[str, ...] = ("lineItems",)
) -> Tuple[dict, bool]:
    refs = {
        "item_ids": set(),
        "item_codes": set(),
        "item_names": set(),
        "account_ids": set(),
        "account_codes": set(),
        "account_names": set(),
    }
    needs_tracking = False
    for line in iter_transaction_lines(records, nested_keys):
        if line.get("itemId"):
            refs["item_ids"].add(line["itemId"])
        if line.get("itemNumber"):
            refs["item_codes"].add(line["itemNumber"])
        if line.get("itemName"):
            refs["item_names"].add(line["itemName"])
        if line.get("accountId"):
            refs["account_ids"].add(line["accountId"])
        if line.get("accountNumber"):
            refs["account_codes"].add(line["accountNumber"])
        if line.get("accountName"):
            refs["account_names"].add(line["accountName"])
        if any(
            line.get(field)
            for _, id_field, name_field in DIMENSION_LINE_FIELDS
            for field in (id_field, name_field)
        ):
            needs_tracking = True
    return refs, needs_tracking


def line_item_records(refs: dict) -> List[dict]:
    records = []
    for item_id in refs["item_ids"]:
        records.append({"itemId": item_id})
    for item_code in refs["item_codes"]:
        records.append({"itemNumber": item_code})
    for item_name in refs["item_names"]:
        records.append({"itemName": item_name})
    return records


def build_transaction_reference_data(
    xero_client,
    target,
    records: List[dict],
    *,
    entity_stream: str,
    entity_filter_mappings: List[dict],
    entity_id_field: str,
    contact_filter_mappings: List[dict],
    contact_key: str,
    nested_keys: Tuple[str, ...] = ("lineItems",),
    entity_reference_key: Optional[str] = None,
) -> Dict:
    line_refs, needs_tracking = collect_line_item_refs(records, nested_keys)
    reference_key = entity_reference_key or entity_stream
    reference_data = {
        **target.reference_data,
        reference_key: xero_client.get_existing_entities_for_records(
            entity_stream,
            records,
            entity_filter_mappings,
            id_field=entity_id_field,
        ),
        contact_key: xero_client.get_existing_entities_for_records(
            "Contacts",
            records,
            contact_filter_mappings,
            id_field="ContactID",
        ),
        "Items": xero_client.get_existing_entities_for_records(
            "Items",
            line_item_records(line_refs),
            LINE_ITEM_FILTER_MAPPINGS,
            id_field="ItemID",
        ),
        "Accounts": (
            xero_client.filter("Accounts") or []
            if line_refs["account_ids"] or line_refs["account_codes"] or line_refs["account_names"]
            else []
        ),
        "tenant_config": target.tenant_config,
    }
    if needs_tracking:
        reference_data["TrackingCategories"] = (
            xero_client.filter("TrackingCategories", includeArchived=True) or []
        )
    return reference_data
