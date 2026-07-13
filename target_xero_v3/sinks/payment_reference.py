from typing import Dict, List

INVOICE_PARENT_FILTER_MAPPINGS = [
    {"field_from": "invoiceId", "xero_field": "InvoiceID", "filter_type": "guid"},
    {"field_from": "invoiceNumber", "xero_field": "InvoiceNumber", "filter_type": "string"},
]

BILL_PARENT_FILTER_MAPPINGS = [
    {"field_from": "billId", "xero_field": "InvoiceID", "filter_type": "guid"},
    {"field_from": "billNumber", "xero_field": "InvoiceNumber", "filter_type": "string"},
]


def build_payment_reference_data(
    xero_client,
    target,
    records: List[dict],
    *,
    parent_filter_mappings: List[dict],
    parent_reference_key: str,
) -> Dict:
    needs_accounts = any(
        record.get("accountId") or record.get("accountName") for record in records
    )
    return {
        **target.reference_data,
        parent_reference_key: xero_client.get_existing_entities_for_records(
            "Invoices",
            records,
            parent_filter_mappings,
            id_field="InvoiceID",
        ),
        "Accounts": (xero_client.filter("Accounts") or []) if needs_accounts else [],
    }
