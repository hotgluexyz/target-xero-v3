from typing import Dict, List

from target_xero_v3.sinks.transaction_reference import collect_line_item_refs

JOURNAL_FILTER_MAPPINGS = [
    {"field_from": "id", "xero_field": "ManualJournalID", "filter_type": "guid"},
]


def build_manual_journal_reference_data(
    xero_client,
    target,
    records: List[dict],
) -> Dict:
    line_refs, needs_tracking = collect_line_item_refs(records, ("lineItems",))
    needs_accounts = bool(
        line_refs["account_ids"] or line_refs["account_codes"] or line_refs["account_names"]
    )
    reference_data = {
        **target.reference_data,
        "JournalEntries": xero_client.get_existing_entities_for_records(
            "ManualJournals",
            records,
            JOURNAL_FILTER_MAPPINGS,
            id_field="ManualJournalID",
        ),
        "Accounts": (xero_client.filter("Accounts") or []) if needs_accounts else [],
        "tenant_config": target.tenant_config,
    }
    if needs_tracking:
        reference_data["TrackingCategories"] = (
            xero_client.filter("TrackingCategories", includeArchived=True) or []
        )
    return reference_data
