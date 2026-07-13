from copy import deepcopy
from typing import Dict, List

from hotglue_models_accounting.accounting import JournalEntry

from target_xero_v3.base_sinks import XeroBatchSink
from target_xero_v3.mappers.manual_journal_schema_mapper import ManualJournalSchemaMapper
from target_xero_v3.sinks.manual_journal_reference import build_manual_journal_reference_data


class ManualJournalSink(XeroBatchSink):
    name = "JournalEntries"
    unified_schema = JournalEntry
    auto_validate_unified_schema = True
    endpoint = "ManualJournals"
    record_type = "ManualJournal"
    id_field = "ManualJournalID"
    max_size = 1

    def get_batch_reference_data(self, records: List) -> Dict:
        return build_manual_journal_reference_data(
            self.xero_client,
            self._target,
            records,
        )

    def make_batch_request(self, records: List[Dict]):
        payload_records = []
        for record in records:
            mapped = deepcopy(record[self.record_type])
            mapped.pop("externalId", None)
            payload_records.append(mapped)
        self.logger.info(f"Processing {self.stream_name}")
        return self.xero_client.post_manual_journal({"ManualJournals": payload_records})

    def process_batch_record(self, record: dict, index: int, reference_data: dict) -> dict:
        mapped_record = ManualJournalSchemaMapper(
            record, self.name, reference_data=reference_data
        ).to_xero()
        if record.get("externalId"):
            mapped_record["externalId"] = record["externalId"]
        operation_type = "update" if self.id_field in mapped_record else "create"
        return {
            "bId": str(index),
            "operation": operation_type,
            self.record_type: mapped_record,
        }
