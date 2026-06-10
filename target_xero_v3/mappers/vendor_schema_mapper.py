from typing import Dict

from target_xero_v3.mappers.base_mapper import BaseMapper


class VendorSchemaMapper(BaseMapper):
    existing_record_pk_mappings = [
        {"record_field": "id", "xero_field": "ContactID", "required_if_present": True},
        {"record_field": "vendorName", "xero_field": "Name", "required_if_present": False},
        {"record_field": "fullName", "xero_field": "Name", "required_if_present": False},
    ]

    field_mappings = {
        "vendorNumber": "AccountNumber",
        "firstName": "FirstName",
        "lastName": "LastName",
    }

    def _map_name(self):
        name = self.record.get("vendorName") or self.record.get("fullName")
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

    def to_xero(self) -> Dict:
        payload = {
            **self._map_internal_id(),
            **self._map_name(),
            **self._map_email(),
            **self._map_currency(),
            **self._map_phones(),
            **self._map_addresses(),
            **self._map_contact_status(),
            "IsCustomer": False,
            "IsSupplier": True,
        }
        self._map_fields(payload)
        return payload
