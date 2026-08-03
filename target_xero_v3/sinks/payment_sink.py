from copy import deepcopy
from typing import Dict, List

from target_xero_v3.base_sinks import XeroBatchSink


class PaymentBatchSink(XeroBatchSink):
    endpoint = "Payments"
    record_type = "Payment"
    id_field = "PaymentID"

    def make_batch_request(self, records: List[Dict]):
        payload_records = []
        for record in records:
            mapped = deepcopy(record[self.record_type])
            mapped.pop("externalId", None)
            payload_records.append(mapped)
        self.logger.info(f"Processing {self.stream_name}")
        return self.xero_client.create_payments({"Payments": payload_records})

    def process_batch_record(self, record: dict, index: int, reference_data: dict) -> dict:
        mapped_record = self.map_record(record, reference_data)
        if record.get("externalId"):
            mapped_record["externalId"] = record["externalId"]
        return {
            "bId": str(index),
            "operation": "create",
            self.record_type: mapped_record,
        }

    def map_record(self, record: dict, reference_data: dict) -> dict:
        raise NotImplementedError
