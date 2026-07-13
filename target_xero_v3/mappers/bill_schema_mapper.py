from typing import Dict, Optional

from hotglue_etl_exceptions import InvalidPayloadError

from target_xero_v3.mappers.base_mapper import BaseMapper
from target_xero_v3.mappers.bill_line_item_schema_mapper import BillLineItemSchemaMapper


class BillSchemaMapper(BaseMapper):
    existing_record_pk_mappings = [
        {"record_field": "id", "xero_field": "InvoiceID", "required_if_present": True},
        {
            "record_field": "billNumber",
            "xero_field": "InvoiceNumber",
            "required_if_present": False,
        },
    ]

    field_mappings = {
        "billNumber": "InvoiceNumber",
        "exchangeRate": "CurrencyRate",
        "description": "Reference",
    }

    def to_xero(self) -> Dict:
        payload = {
            "Type": "ACCPAY",
            **self._map_internal_id(),
            **self._map_contact(),
            **self._map_currency_code(),
            **self._map_status(),
            **self._map_line_amount_types(),
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
        vendors = self.reference_data.get("Vendors", [])
        if vendor_id := self.record.get("vendorId"):
            found = next(
                (
                    contact
                    for contact in vendors
                    if str(contact.get("ContactID")) == str(vendor_id)
                ),
                None,
            )
            if found:
                return found
            return {"ContactID": vendor_id}
        if vendor_number := self.record.get("vendorNumber"):
            found = next(
                (
                    contact
                    for contact in vendors
                    if contact.get("ContactNumber") == vendor_number
                ),
                None,
            )
            if found:
                return found
        if vendor_name := self.record.get("vendorName"):
            found = next(
                (contact for contact in vendors if contact.get("Name") == vendor_name),
                None,
            )
            if found:
                return found
            return {"Name": vendor_name}
        raise InvalidPayloadError("Vendor contact is required for bill")

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

    def _map_status(self):
        if status := self.record.get("status"):
            return {"Status": status}
        is_draft = self.record.get("isDraft")
        if is_draft is True:
            return {"Status": "DRAFT"}
        if is_draft is False:
            return {"Status": "AUTHORISED"}
        return {}

    def _map_line_amount_types(self):
        tax_included = self.record.get("taxIncluded")
        if tax_included is None:
            return {}
        return {"LineAmountTypes": "Inclusive" if tax_included else "Exclusive"}

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
        for line in (self.record.get("lineItems") or []) + (
            self.record.get("expenses") or []
        ):
            mapped_lines.append(
                BillLineItemSchemaMapper(
                    line, "BillLineItems", reference_data=self.reference_data
                ).to_xero()
            )
        return {"LineItems": mapped_lines} if mapped_lines else {}
