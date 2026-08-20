from copy import deepcopy
from typing import Dict, List

from hotglue_etl_exceptions import InvalidPayloadError
from hotglue_models_accounting.accounting import Account

from target_xero_v3.base_sinks import XeroBatchSink
from target_xero_v3.mappers.account_schema_mapper import AccountSchemaMapper


class AccountSink(XeroBatchSink):
    name = "Accounts"
    unified_schema = Account
    auto_validate_unified_schema = True
    endpoint = "Accounts"
    record_type = "Account"
    id_field = "AccountID"

    FILTER_MAPPINGS = [
        {"field_from": "id", "xero_field": "AccountID", "filter_type": "guid"},
        {"field_from": "accountNumber", "xero_field": "Code", "filter_type": "string"},
        {"field_from": "name", "xero_field": "Name", "filter_type": "string"},
    ]

    def get_batch_reference_data(self, records: List) -> Dict:
        fetched = self.xero_client.get_existing_entities_for_records(
            "Accounts",
            records,
            self.FILTER_MAPPINGS,
            id_field="AccountID",
        )
        deduped_accounts = {}
        for account in self._target.reference_data.get(self.name, []):
            account_id = account.get("AccountID")
            if account_id:
                deduped_accounts[account_id] = account
        for account in fetched:
            account_id = account.get("AccountID")
            if account_id:
                deduped_accounts[account_id] = account
        return {
            **self._target.reference_data,
            self.name: list(deduped_accounts.values()),
        }

    def process_batch_record(self, record: dict, index: int, reference_data: dict) -> dict:
        mapped_record = AccountSchemaMapper(
            record, self.name, reference_data=reference_data
        ).to_xero()
        if record.get("externalId"):
            mapped_record["externalId"] = record["externalId"]
        operation_type = "update" if self.id_field in mapped_record else "create"
        reference_data_account_status = self._reference_data_account_status(
            mapped_record.get(self.id_field), reference_data
        )
        if operation_type == "update":
            self._validate_archived_account_field_update(mapped_record, reference_data_account_status)
        return {
            "bId": str(index),
            "operation": operation_type,
            "reference_data_account_status": reference_data_account_status,
            self.record_type: mapped_record,
        }

    def _reference_data_account_status(self, account_id, reference_data):
        if not account_id:
            return None
        reference_data_account = next(
            (
                account
                for account in reference_data.get(self.name, [])
                if str(account.get("AccountID")) == str(account_id)
            ),
            None,
        )
        if reference_data_account:
            return reference_data_account.get("Status")
        return None

    def _field_payload(self, mapped_record):
        return {
            key: value
            for key, value in mapped_record.items()
            if key not in (self.id_field, "Status", "externalId")
        }

    def _validate_archived_account_field_update(self, mapped_record, reference_data_account_status):
        "We can only update fields of a non archived account."
        if reference_data_account_status != "ARCHIVED":
            return
        # account is archived, so we can only update fields if we are activating it too
        if self._field_payload(mapped_record) and mapped_record.get("Status") != "ACTIVE":
            # in the case we try to update the account without activating it too, we raise an error
            raise InvalidPayloadError(
                "Xero cannot update fields on an archived account. "
                "Set isActive=true to reactivate it before changing fields."
            )

    def make_batch_request(self, records: List[Dict]):
        self.logger.info(f"Processing {self.stream_name}")
        responses = []
        for record in records:
            mapped = deepcopy(record[self.record_type])
            mapped.pop("externalId", None)
            account_id = mapped.pop("AccountID", None)
            if account_id:
                responses.append(
                    self._update_account(
                        account_id, mapped, record.get("reference_data_account_status")
                    )
                )
            else:
                mapped.pop("Status", None)
                responses.append(self.xero_client.create_account(mapped))
        return responses

    def _update_account(self, account_id, mapped, existing_status):
        desired_status = mapped.pop("Status", None)
        fields = mapped

        #activate account and update fields
        if existing_status == "ARCHIVED" and fields \
            and desired_status == "ACTIVE": 
            # this last condition is just to make the code understandable, it will always be true when we get here
            # we already failed the case where we try to update and archived account without activating it too
            response = self.xero_client.update_account(
                account_id, {"Status": desired_status}
            )
            if response.status_code >= 400:
                return response

            return self.xero_client.update_account(account_id, fields)

        # update fields and archive account if necessary
        if fields:
            response = self.xero_client.update_account(account_id, fields)
            if response.status_code >= 400:
                return response
            # since we are able to update the fields, it means the account was active
            # we can archive it if we want to
            if desired_status == "ARCHIVED":
                return self.xero_client.update_account(
                    account_id, {"Status": desired_status}
                )
            return response

        if desired_status == existing_status:
            # case where the status match and no extra fields to update
            # no need to do anything, just mark as existing and move to the next one
            return None
        if desired_status:
            return self.xero_client.update_account(
                account_id, {"Status": desired_status}
            )

        # we should never get here, but just in case
        raise InvalidPayloadError("No account fields or status to update.")

    def handle_batch_response(self, responses, records):
        state_updates = []
        for i, response in enumerate(responses):
            record_payload = records[i] if i < len(records) else {}
            mapped = record_payload.get(self.record_type) or {}
            external_id = mapped.get("externalId")
            if response is None:
                state_updates.append(
                    {
                        "id": mapped.get(self.id_field),
                        "externalId": external_id,
                        "success": True,
                        "existing": True,
                    }
                )
                continue
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
            accounts = body.get("Accounts") or []
            account = accounts[0] if accounts else body
            state_updates.append(
                self._state_update_from_item(account, record_payload, external_id)
            )
        return {"state_updates": state_updates}
