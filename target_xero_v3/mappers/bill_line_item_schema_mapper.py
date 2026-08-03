from typing import Dict

from target_xero_v3.mappers.xero_line_item_mapper import XeroLineItemMapper


class BillLineItemSchemaMapper(XeroLineItemMapper):
    field_mappings = {
        "description": "Description",
        "taxCode": "TaxType",
        "quantity": "Quantity",
        "unitPrice": "UnitAmount",
        "amount": "LineAmount",
    }

    def to_xero(self) -> Dict:
        payload = {
            **self._map_line_item_id(),
            **self._map_item(),
            **self._map_account(),
            **self._map_tracking(),
        }
        self._map_fields(payload)
        return payload
