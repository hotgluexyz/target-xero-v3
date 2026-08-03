from typing import Dict

from target_xero_v3.mappers.base_mapper import BaseMapper


class ClassSchemaMapper(BaseMapper):
    existing_record_pk_mappings = [
        {"record_field": "id", "xero_field": "TrackingOptionID", "required_if_present": True},
        {"record_field": "name", "xero_field": "Name", "required_if_present": False},
        {"record_field": "fullname", "xero_field": "Name", "required_if_present": False},
    ]

    def to_xero(self) -> Dict:
        return {
            **self._map_internal_id(),
            **self._map_name("name", "fullname"),
            **self._map_status(),
        }

    def _map_internal_id(self):
        if self.existing_record:
            return {"TrackingOptionID": self.existing_record["TrackingOptionID"]}
        return {}

    def _map_status(self):
        is_active = self.record.get("isActive")
        if is_active is None:
            return {}
        return {"Status": "ACTIVE" if is_active else "ARCHIVED"}
