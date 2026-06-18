from typing import Dict

from target_xero_v3.mappers.base_mapper import BaseMapper


class CustomerSchemaMapper(BaseMapper):
    existing_record_pk_mappings = [
        {"record_field": "id", "xero_field": "ContactID", "required_if_present": True},
        {"record_field": "companyName", "xero_field": "Name", "required_if_present": False},
        {"record_field": "fullName", "xero_field": "Name", "required_if_present": False},
    ]

    field_mappings = {
        "customerNumber": "ContactNumber",
        "firstName": "FirstName",
        "lastName": "LastName",
        "taxCode": "AccountsReceivableTaxType",
    }

    def to_xero(self) -> Dict:
        payload = {
            **self._map_internal_id(),
            **self._map_name("companyName", "fullName"),
            **self._map_email(),
            **self._map_currency(),
            **self._map_phones(),
            **self._map_addresses(),
            **self._map_contact_status(),
        }
        self._map_fields(payload)
        return payload
