from typing import Dict, Optional

from hotglue_etl_exceptions import InvalidPayloadError

from target_xero_v3.mappers.base_mapper import BaseMapper
from target_xero_v3.mappers.invoice_line_item_schema_mapper import (
    InvoiceLineItemSchemaMapper,
)


class InvoiceSchemaMapper(BaseMapper):
    existing_record_pk_mappings = [
        {"record_field": "id", "xero_field": "InvoiceID", "required_if_present": True},
        {
            "record_field": "invoiceNumber",
            "xero_field": "InvoiceNumber",
            "required_if_present": False,
        },
    ]

    field_mappings = {
        "invoiceNumber": "InvoiceNumber",
        "exchangeRate": "CurrencyRate",
        "status": "Status",
        "description": "Reference",
    }

    def to_xero(self) -> Dict:
        payload = {
            "Type": "ACCREC",
            **self._map_internal_id(),
            **self._map_contact(),
            **self._map_currency_code(),
            **self._map_dates(),
            **self._map_line_items(),
        }
        self._map_fields(payload)
        return payload

    def _map_internal_id(self):
        if self.existing_record:
            return {"InvoiceID": self.existing_record["InvoiceID"]}
        return {}

    def _find_contact(self):
        customers = self.reference_data.get("Customers", [])
        if customer_id := self.record.get("customerId"):
            found = next(
                (
                    contact
                    for contact in customers
                    if str(contact.get("ContactID")) == str(customer_id)
                ),
                None,
            )
            if found:
                return found
            return {"ContactID": customer_id}
        if customer_number := self.record.get("customerNumber"):
            found = next(
                (
                    contact
                    for contact in customers
                    if contact.get("ContactNumber") == customer_number
                ),
                None,
            )
            if found:
                return found
        if customer_name := self.record.get("customerName"):
            found = next(
                (contact for contact in customers if contact.get("Name") == customer_name),
                None,
            )
            if found:
                return found
            return {"Name": customer_name}
        raise InvalidPayloadError("Customer contact is required for invoice")

    def _map_contact(self):
        contact = self._find_contact()
        payload = {}
        if contact_id := contact.get("ContactID"):
            payload["ContactID"] = contact_id
        if name := contact.get("Name"):
            payload["Name"] = name
        return {"Contact": payload}

    def _map_currency_code(self):
        if currency := self.record.get("currency"):
            return {"CurrencyCode": currency}
        if currency_id := self.record.get("currencyId"):
            if code := self._lookup_currency_by_code(currency_id):
                return {"CurrencyCode": code}
        if currency_name := self.record.get("currencyName"):
            if code := self._lookup_currency_code(currency_name):
                return {"CurrencyCode": code}
        return {}

    def _format_date(self, value) -> Optional[str]:
        if not value:
            return None
        return str(value)[:10]

    def _map_dates(self):
        payload = {}
        if date := self._format_date(
            self.record.get("postingDate") or self.record.get("issueDate")
        ):
            payload["Date"] = date
        if due_date := self._format_date(self.record.get("dueDate")):
            payload["DueDate"] = due_date
        return payload

    def _map_line_items(self):
        mapped_lines = []
        for line in self.record.get("lineItems") or []:
            mapped_lines.append(
                InvoiceLineItemSchemaMapper(
                    line, "InvoiceLineItems", reference_data=self.reference_data
                ).to_xero()
            )
        return {"LineItems": mapped_lines} if mapped_lines else {}
