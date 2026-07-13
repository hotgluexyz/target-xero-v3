from copy import deepcopy
from typing import Dict, List

from hotglue_etl_exceptions import InvalidPayloadError
from hotglue_models_accounting.accounting import Class

from target_xero_v3.base_sinks import XeroBatchSink
from target_xero_v3.mappers.class_schema_mapper import ClassSchemaMapper


class ClassSink(XeroBatchSink):
    name = "Classes"
    unified_schema = Class
    auto_validate_unified_schema = True
    endpoint = "TrackingCategories"
    record_type = "Option"
    id_field = "TrackingOptionID"

    def _tracking_category_name(self):
        return (
            self._target.tenant_config.get("xero", {})
            .get("dimension_mappings", {})
            .get("class", "CLASS")
        )

    def get_batch_reference_data(self, records: List) -> Dict:
        category_name = self._tracking_category_name()
        categories = self.xero_client.filter(
            "TrackingCategories", includeArchived=True
        ) or []
        tracking_category = next(
            (category for category in categories if category.get("Name") == category_name),
            None,
        )
        existing_options = []
        if tracking_category:
            existing_options = tracking_category.get("Options") or []
        return {
            **self._target.reference_data,
            "TrackingCategory": tracking_category,
            self.name: existing_options,
        }

    def process_batch_record(self, record: dict, index: int, reference_data: dict) -> dict:
        tracking_category = reference_data.get("TrackingCategory")
        if not tracking_category:
            raise InvalidPayloadError(
                f"Tracking category '{self._tracking_category_name()}' not found"
            )
        mapped_record = ClassSchemaMapper(
            record, self.name, reference_data=reference_data
        ).to_xero()
        if record.get("externalId"):
            mapped_record["externalId"] = record["externalId"]
        operation_type = "update" if self.id_field in mapped_record else "create"
        return {
            "bId": str(index),
            "operation": operation_type,
            "trackingCategoryId": tracking_category["TrackingCategoryID"],
            self.record_type: mapped_record,
        }

    def make_batch_request(self, records: List[Dict]):
        self.logger.info(f"Processing {self.stream_name}")
        responses = []
        for record in records:
            category_id = record["trackingCategoryId"]
            mapped = deepcopy(record[self.record_type])
            mapped.pop("externalId", None)
            option_id = mapped.pop("TrackingOptionID", None)
            if option_id:
                responses.append(
                    self.xero_client.update_tracking_option(
                        category_id, option_id, mapped
                    )
                )
            else:
                responses.append(
                    self.xero_client.create_tracking_option(category_id, mapped)
                )
        return responses

    def handle_batch_response(self, responses, records):
        state_updates = []
        for i, response in enumerate(responses):
            record_payload = records[i] if i < len(records) else {}
            external_id = record_payload.get(self.record_type, {}).get("externalId")
            if response.status_code >= 400:
                state_updates.append(
                    {
                        "success": False,
                        "externalId": external_id,
                        "error": self.xero_client._response_error_message(response),
                        "hg_error_class": InvalidPayloadError.__name__,
                    }
                )
                continue
            body = response.json()
            name = record_payload.get(self.record_type, {}).get("Name")
            option = next(
                (o for o in body.get("Options") or [] if name and o.get("Name") == name),
                None,
            )
            if not option:
                options = body.get("Options") or []
                option = options[-1] if options else body
            state_updates.append(
                self._state_update_from_item(option, record_payload, external_id)
            )
        return {"state_updates": state_updates}
