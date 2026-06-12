from typing import Dict, List


ADDRESS_TYPE_MAP = {
    "billing": "POBOX",
    "shipping": "STREET",
}

PHONE_TYPE_MAP = {
    "primary": "DEFAULT",
    "mobile": "MOBILE",
    "ddi": "DDI",
    "fax": "FAX",
    "unknown": "DEFAULT",
}


class BaseMapper:
    existing_record_pk_mappings: List[dict] = []
    field_mappings: Dict[str, str] = {}

    def __init__(self, record, sink_name, reference_data) -> None:
        self.record = record
        self.sink_name = sink_name
        self.reference_data = reference_data
        self.existing_record = self._find_existing_record(
            self.reference_data.get(self.sink_name, [])
        )

    def _find_existing_record(self, reference_list):
        for mapping in self.existing_record_pk_mappings:
            record_id = self.record.get(mapping["record_field"])
            if not record_id:
                continue
            found_record = next(
                (
                    xero_record
                    for xero_record in reference_list
                    if str(xero_record[mapping["xero_field"]]) == str(record_id)
                ),
                None,
            )
            if found_record:
                return found_record
        return None

    def _map_internal_id(self):
        if self.existing_record:
            return {"ContactID": self.existing_record["ContactID"]}
        return {}

    def _map_fields(self, payload):
        for record_key, payload_key in self.field_mappings.items():
            if record_key in self.record and self.record.get(record_key) is not None:
                payload[payload_key] = self.record.get(record_key)

    def _get_email(self):
        return self.record.get("email") or self.record.get("emailAddress")

    def _map_email(self):
        email = self._get_email()
        if email:
            return {"EmailAddress": email}
        return {}

    def _lookup_currency_code(self, currency_name):
        normalized_name = currency_name.casefold()
        for currency in self.reference_data.get("Currencies", []):
            description = currency.get("Description")
            if description and description.casefold() == normalized_name:
                return currency.get("Code")
        return None

    def _lookup_currency_by_code(self, currency_code):
        for currency in self.reference_data.get("Currencies", []):
            if str(currency.get("Code")) == str(currency_code):
                return currency.get("Code")
        return None

    def _get_base_currency(self):
        organisations = self.reference_data.get("Organisation", [])
        if organisations:
            return organisations[0].get("BaseCurrency")
        return None

    def _map_currency(self):
        if currency := self.record.get("currency"):
            return {"DefaultCurrency": currency}
        if currency_id := self.record.get("currencyId"):
            if code := self._lookup_currency_by_code(currency_id):
                return {"DefaultCurrency": code}
        if currency_name := self.record.get("currencyName"):
            if code := self._lookup_currency_code(currency_name):
                return {"DefaultCurrency": code}
        if base_currency := self._get_base_currency():
            return {"DefaultCurrency": base_currency}
        return {}

    def _map_phones(self):
        phones = []
        for phone in self.record.get("phoneNumbers") or []:
            phone_number = phone.get("phoneNumber") or phone.get("number")
            if not phone_number:
                continue
            phone_type = phone.get("type") or "unknown"
            phones.append(
                {
                    "PhoneType": PHONE_TYPE_MAP.get(phone_type.lower(), phone_type.upper()),
                    "PhoneNumber": phone_number,
                }
            )
        return {"Phones": phones} if phones else {}

    def _map_addresses(self):
        addresses = []
        for address in self.record.get("addresses") or []:
            address_type = address.get("addressType") or "shipping"
            addresses.append(
                {
                    "AddressType": ADDRESS_TYPE_MAP.get(
                        address_type.lower(), address_type.upper()
                    ),
                    "AddressLine1": address.get("line1"),
                    "AddressLine2": address.get("line2"),
                    "AddressLine3": address.get("line3"),
                    "City": address.get("city"),
                    "Region": address.get("state"),
                    "PostalCode": address.get("postalCode"),
                    "Country": address.get("country"),
                }
            )
        return {"Addresses": addresses} if addresses else {}

    def _map_name(self, *name_fields):
        name = next(
            (self.record[field] for field in name_fields if self.record.get(field)),
            None,
        )
        if not name:
            parts = [self.record.get("firstName"), self.record.get("lastName")]
            name = " ".join(part for part in parts if part)
        if name:
            return {"Name": name}
        return {}

    def _map_contact_status(self):
        is_active = self.record.get("isActive")
        if is_active is None:
            return {}
        return {"ContactStatus": "ACTIVE" if is_active else "ARCHIVED"}
