import json
from copy import deepcopy
from typing import Dict, List, Optional

from hotglue_singer_sdk.plugin_base import PluginBase
from hotglue_singer_sdk.target_sdk.client import HotglueBatchSink

from target_xero_v3.client import XeroClient


class XeroBatchSink(HotglueBatchSink):
    max_size = 30
    endpoint = "Contacts"
    record_type = "Contact"

    def __init__(
        self,
        target: PluginBase,
        stream_name: str,
        schema: Dict,
        key_properties: Optional[List[str]],
    ) -> None:
        super().__init__(target, stream_name, schema, key_properties)
        self.xero_client: XeroClient = target.xero_client
        self.reference_data = self._target.reference_data

    def get_batch_reference_data(self, records: List) -> dict:
        return self._target.reference_data

    def process_batch(self, context: dict) -> None:
        if not self.latest_state:
            self.init_state()

        raw_records = context.get("records", [])
        reference_data = self.get_batch_reference_data(raw_records)
        records = []
        for index, raw_record in enumerate(raw_records):
            try:
                record = self.process_batch_record(raw_record, index, reference_data)
                records.append(record)
            except Exception as e:
                state = {"success": False, "error": str(e)}
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

    def make_batch_request(self, records: List[Dict]):
        request_contacts = []
        for record in records:
            contact = deepcopy(record[self.record_type])
            contact.pop("externalId", None)
            request_contacts.append(contact)
        self.logger.info(f"Processing {self.stream_name}")
        return self.xero_client.push(self.endpoint, {self.endpoint: request_contacts})

    def handle_batch_response(self, response, records):
        state_updates = []
        if not response or response.status_code not in [200]:
            error = response.text if response else "No response"
            for record in records:
                state_updates.append(
                    {
                        "success": False,
                        "externalId": record.get(self.record_type, {}).get("externalId"),
                        "error": error,
                    }
                )
            return {"state_updates": state_updates}

        contacts = response.json().get("Contacts", [])
        for i, contact in enumerate(contacts):
            record_payload = records[i] if i < len(records) else {}
            external_id = record_payload.get(self.record_type, {}).get("externalId")
            if contact.get("HasValidationErrors"):
                state_updates.append(
                    {
                        "success": False,
                        "externalId": external_id,
                        "error": json.dumps(contact.get("ValidationErrors", [])),
                    }
                )
            else:
                state = {
                    "id": contact.get("ContactID"),
                    "externalId": external_id,
                    "success": True,
                }
                if record_payload.get("operation") == "update":
                    state["is_updated"] = True
                state_updates.append(state)

        return {"state_updates": state_updates}
