from typing import Dict

from target_xero_v3.mappers.base_mapper import BaseMapper


class VendorSchemaMapper(BaseMapper):
    existing_record_pk_mappings = [
        {"record_field": "id", "xero_field": "ContactID", "required_if_present": True},
        {"record_field": "vendorName", "xero_field": "Name", "required_if_present": False},
    ]

    field_mappings = {
        "firstName": "FirstName",
        "lastName": "LastName",
    }

    def to_xero(self) -> Dict:
        payload = {
            **self._map_internal_id(),
            **self._map_contact_name(),
            **self._map_email(),
            **self._map_website(),
            **self._map_currency(),
            **self._map_phones(),
            **self._map_addresses(),
            "IsCustomer": False,
            "IsSupplier": True,
        }
        self._map_fields(payload)
        self._map_person_name(payload)
        return payload
