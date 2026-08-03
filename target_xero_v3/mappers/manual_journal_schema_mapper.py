from typing import Dict, Optional

from target_xero_v3.mappers.base_mapper import BaseMapper
from target_xero_v3.mappers.manual_journal_line_schema_mapper import (
    ManualJournalLineSchemaMapper,
)


class ManualJournalSchemaMapper(BaseMapper):
    existing_record_pk_mappings = [
        {"record_field": "id", "xero_field": "ManualJournalID", "required_if_present": True},
    ]

    field_mappings = {"description": "Narration"}

    def to_xero(self) -> Dict:
        payload = {
            **self._map_internal_id(),
            **self._map_status(),
            **self._map_date(),
            **self._map_journal_lines(),
        }
        self._map_fields(payload)
        return payload

    def _map_internal_id(self):
        if self.existing_record:
            return {"ManualJournalID": self.existing_record["ManualJournalID"]}
        if journal_id := self.record.get("id"):
            return {"ManualJournalID": journal_id}
        return {}

    def _map_status(self):
        is_draft = self.record.get("isDraft")
        if is_draft is True:
            return {"Status": "DRAFT"}
        if is_draft is False:
            return {"Status": "POSTED"}
        return {}

    def _format_date(self, value) -> Optional[str]:
        if not value:
            return None
        return str(value)[:10]

    def _map_date(self):
        if date := self._format_date(self.record.get("transactionDate")):
            return {"Date": date}
        return {}

    def _map_journal_lines(self):
        mapped_lines = []
        for line in self.record.get("lineItems") or []:
            mapped_lines.append(
                ManualJournalLineSchemaMapper(
                    line, "JournalEntryLineItems", reference_data=self.reference_data
                ).to_xero()
            )
        return {"JournalLines": mapped_lines} if mapped_lines else {}
