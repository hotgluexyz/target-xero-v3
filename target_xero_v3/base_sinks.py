from copy import deepcopy
from typing import Dict, List, Optional

from hotglue_etl_exceptions import InvalidCredentialsError, InvalidPayloadError
from hotglue_singer_sdk.plugin_base import PluginBase
from hotglue_singer_sdk.target_sdk.client import HotglueBatchSink

from target_xero_v3.client import XeroClient


class XeroBatchSink(HotglueBatchSink):
    max_size = 30
    id_field: str

    def __init__(
        self,
        target: PluginBase,
        stream_name: str,
        schema: Dict,
        key_properties: Optional[List[str]],
    ) -> None:
        super().__init__(target, stream_name, schema, key_properties)
        self.xero_client: XeroClient = target.xero_client

    def get_batch_reference_data(self, records: List) -> dict:
        return self._target.reference_data

    def process_batch(self, context: dict) -> None:
        if not self.latest_state:
            self.init_state()

        raw_records = context.get("records", [])
        try:
            reference_data = self.get_batch_reference_data(raw_records)
            records = []
            for index, raw_record in enumerate(raw_records):
                try:
                    record = self.process_batch_record(raw_record, index, reference_data)
                    records.append(record)
                except Exception as e:
                    state = {"success": False, "error": str(e)}
                    if isinstance(e, InvalidPayloadError):
                        state["hg_error_class"] = InvalidPayloadError.__name__
                    if record_id := raw_record.get("id"):
                        state["id"] = str(record_id)
                    if external_id := raw_record.get("externalId"):
                        state["externalId"] = external_id
                    self.update_state(state)

            if not records:
                return

            response = self.make_batch_request(records)
            result = self.handle_batch_response(response, records)
            for i, state_update in enumerate(result.get("state_updates", [])):
                self.update_state(state_update, record=records[i].get(self.record_type))
        except InvalidCredentialsError as e:
            self._write_credential_error_state(raw_records, str(e))
            raise

    def _write_credential_error_state(self, raw_records: List[dict], error: str) -> None:
        for raw_record in raw_records:
            state = {
                "success": False,
                "error": error,
                "hg_error_class": InvalidCredentialsError.__name__,
            }
            if record_id := raw_record.get("id"):
                state["id"] = str(record_id)
            if external_id := raw_record.get("externalId"):
                state["externalId"] = external_id
            self.update_state(state)
        target_state = self._target._latest_state
        if not target_state:
            self._target._latest_state = self.latest_state
            return
        target_state.setdefault("bookmarks", {})
        target_state.setdefault("summary", {})
        target_state["bookmarks"][self.name] = self.latest_state["bookmarks"][self.name]
        target_state["summary"][self.name] = self.latest_state["summary"][self.name]

    def make_batch_request(self, records: List[Dict]):
        payload_records = []
        for record in records:
            mapped = deepcopy(record[self.record_type])
            mapped.pop("externalId", None)
            payload_records.append(mapped)
        self.logger.info(f"Processing {self.stream_name}")
        return self.xero_client.push(self.endpoint, {self.endpoint: payload_records})

    def handle_batch_response(self, response, records):
        state_updates = []
        items = response.json().get(self.endpoint, [])
        for i, item in enumerate(items):
            record_payload = records[i] if i < len(records) else {}
            external_id = record_payload.get(self.record_type, {}).get("externalId")
            if item.get("HasValidationErrors"):
                state_updates.append(
                    {
                        "success": False,
                        "externalId": external_id,
                        "error": "; ".join(
                            error["Message"]
                            for error in item.get("ValidationErrors", [])
                        ),
                        "hg_error_class": InvalidPayloadError.__name__,
                    }
                )
            else:
                state = {
                    "id": item.get(self.id_field),
                    "externalId": external_id,
                    "success": True,
                }
                if record_payload.get("operation") == "update":
                    state["is_updated"] = True
                state_updates.append(state)

        return {"state_updates": state_updates}
