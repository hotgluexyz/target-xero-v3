from typing import Dict

from target_xero_v3.mappers.xero_line_item_mapper import XeroLineItemMapper


class ManualJournalLineSchemaMapper(XeroLineItemMapper):
    field_mappings = {
        "description": "Description",
        "taxCode": "TaxType",
    }

    def to_xero(self) -> Dict:
        payload = {
            **self._map_account(),
            **self._map_line_amount(),
            **self._map_tracking(),
        }
        self._map_fields(payload)
        return payload

    def _map_line_amount(self):
        if (debit := self.record.get("debitAmount")) is not None:
            return {"LineAmount": debit}
        if (credit := self.record.get("creditAmount")) is not None:
            return {"LineAmount": -credit}
        return {}
