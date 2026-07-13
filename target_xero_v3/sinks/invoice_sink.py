from typing import Dict, List, Tuple

from hotglue_models_accounting.accounting import Invoice

from target_xero_v3.base_sinks import XeroBatchSink
from target_xero_v3.mappers.invoice_schema_mapper import InvoiceSchemaMapper

DIMENSION_LINE_FIELDS = (
    ("class", "classId", "className"),
    ("location", "locationId", "locationName"),
    ("department", "departmentId", "departmentName"),
)


class InvoiceSink(XeroBatchSink):
    name = "Invoices"
    unified_schema = Invoice
    auto_validate_unified_schema = True
    endpoint = "Invoices"
    record_type = "Invoice"
    id_field = "InvoiceID"

    def get_batch_reference_data(self, records: List) -> Dict:
        line_refs, needs_tracking = self._collect_line_item_refs(records)
        reference_data = {
            **self._target.reference_data,
            self.name: self._fetch_invoices(records),
            "Customers": self._fetch_customers(records),
            "Items": self._fetch_items(line_refs),
            "Accounts": self._fetch_accounts(line_refs),
            "tenant_config": self._target.tenant_config,
        }
        if needs_tracking:
            reference_data["TrackingCategories"] = (
                self.xero_client.filter("TrackingCategories", includeArchived=True)
                or []
            )
        return reference_data

    def _fetch_invoices(self, records: List) -> List:
        existing_invoices = []
        for invoice_id in {record["id"] for record in records if record.get("id")}:
            matches = self.xero_client.filter(
                "Invoices", where=f'InvoiceID==guid"{invoice_id}"'
            )
            if matches:
                existing_invoices.extend(matches)
        for invoice_number in {
            record["invoiceNumber"] for record in records if record.get("invoiceNumber")
        }:
            escaped = invoice_number.replace('"', '\\"')
            matches = self.xero_client.filter(
                "Invoices", where=f'InvoiceNumber=="{escaped}"'
            )
            if matches:
                existing_invoices.extend(matches)
        return existing_invoices

    def _fetch_customers(self, records: List) -> List:
        customers = []
        for customer_id in {
            record["customerId"] for record in records if record.get("customerId")
        }:
            matches = self.xero_client.filter(
                "Contacts", where=f'ContactID==guid"{customer_id}"'
            )
            if matches:
                customers.extend(matches)
        for customer_number in {
            record["customerNumber"] for record in records if record.get("customerNumber")
        }:
            escaped = customer_number.replace('"', '\\"')
            matches = self.xero_client.filter(
                "Contacts", where=f'ContactNumber=="{escaped}"'
            )
            if matches:
                customers.extend(matches)
        for customer_name in {
            record["customerName"] for record in records if record.get("customerName")
        }:
            escaped = customer_name.replace('"', '\\"')
            matches = self.xero_client.filter(
                "Contacts", where=f'Name=="{escaped}"'
            )
            if matches:
                customers.extend(matches)
        return customers

    def _collect_line_item_refs(self, records: List) -> Tuple[dict, bool]:
        refs = {
            "item_ids": set(),
            "item_codes": set(),
            "item_names": set(),
            "account_ids": set(),
            "account_codes": set(),
            "account_names": set(),
        }
        needs_tracking = False
        for record in records:
            for line in record.get("lineItems") or []:
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
                if any(line.get(field) for _, id_field, name_field in DIMENSION_LINE_FIELDS for field in (id_field, name_field)):
                    needs_tracking = True
        return refs, needs_tracking

    def _fetch_items(self, refs: dict) -> List:
        items = []
        for item_id in refs["item_ids"]:
            matches = self.xero_client.filter(
                "Items", where=f'ItemID==guid"{item_id}"'
            )
            if matches:
                items.extend(matches)
        for item_code in refs["item_codes"]:
            escaped = item_code.replace('"', '\\"')
            matches = self.xero_client.filter("Items", where=f'Code=="{escaped}"')
            if matches:
                items.extend(matches)
        for item_name in refs["item_names"]:
            escaped = item_name.replace('"', '\\"')
            matches = self.xero_client.filter("Items", where=f'Name=="{escaped}"')
            if matches:
                items.extend(matches)
        return items

    def _fetch_accounts(self, refs: dict) -> List:
        if refs["account_ids"] or refs["account_codes"] or refs["account_names"]:
            return self.xero_client.filter("Accounts") or []
        return []

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
