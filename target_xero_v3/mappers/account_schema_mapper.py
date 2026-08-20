from typing import Dict, Optional

from hotglue_etl_exceptions import InvalidPayloadError

from target_xero_v3.mappers.base_mapper import BaseMapper


class AccountSchemaMapper(BaseMapper):
    """Map unified Account records to Xero Account payloads.

    Xero uses Code as the unique chart key.

    unified category must be a Xero Account.Type value (e.g. EXPENSE, BANK).
    """

    existing_record_pk_mappings = [
        {"record_field": "id", "xero_field": "AccountID", "required_if_present": True},
        {"record_field": "accountNumber", "xero_field": "Code", "required_if_present": False},
        {"record_field": "name", "xero_field": "Name", "required_if_present": False},
    ]

    field_mappings = {
        "name": "Name",
        "description": "Description",
        "accountNumber": "Code",
    }

    def to_xero(self) -> Dict:
        self._validate_parent_not_supported()
        existing = self._map_existing_by_id_or_code()
        payload = {**existing}
        self._validate_create_required(payload)
        self._map_status(payload)
        self._map_type(payload)
        self._map_account_currency(payload)
        self._map_fields(payload)
        return payload

    def _validate_parent_not_supported(self):
        if self.record.get("parentId") or self.record.get("parentName"):
            raise InvalidPayloadError(
                "Xero does not support parent accounts. Remove parentId and parentName."
            )

    def _map_existing_by_id_or_code(self):
        if record_id := self.record.get("id"):
            found = self._find_account_by_id(str(record_id))
            if found:
                return {"AccountID": found["AccountID"]}
            raise InvalidPayloadError(
                f"Record id={record_id} not found in Xero. Skipping it"
            )

        if account_code := self.record.get("accountNumber"):
            found = self._find_account_by_code(str(account_code))
            if found:
                return {"AccountID": found["AccountID"]}

        if account_name := self.record.get("name"):
            matches = [
                account
                for account in self.reference_data.get(self.sink_name, [])
                if account.get("Name") == account_name
            ]
            if len(matches) > 1:
                codes = ", ".join(sorted(account.get("Code", "?") for account in matches))
                raise InvalidPayloadError(
                    f"name={account_name} is ambiguous in Xero; it matches multiple "
                    f"accounts (codes: {codes}). Provide accountNumber or id to disambiguate."
                )
            if matches:
                return {"AccountID": matches[0]["AccountID"]}

        return {}

    def _find_account_by_id(self, account_id: str):
        return next(
            (
                account
                for account in self.reference_data.get(self.sink_name, [])
                if str(account.get("AccountID")) == account_id
            ),
            None,
        )

    def _find_account_by_code(self, account_code: str):
        return next(
            (
                account
                for account in self.reference_data.get(self.sink_name, [])
                if str(account.get("Code")) == account_code
            ),
            None,
        )

    def _validate_create_required(self, payload):
        if payload.get("AccountID") is not None:
            return
        missing = []
        if not self._resolve_type():
            missing.append("category")
        if not self.record.get("accountNumber"):
            missing.append("accountNumber")
        if not self.record.get("name"):
            missing.append("name")
        if missing:
            raise InvalidPayloadError(
                f"{', '.join(missing)} required when creating a new Account."
            )

    def _xero_type_from_category(self, category: Optional[str]) -> Optional[str]:
        if not category:
            return None
        return category.strip().upper().replace(" ", "")

    def _resolve_type(self) -> Optional[str]:
        if self.record.get("isBankAccount") is True:
            return "BANK"
        return self._xero_type_from_category(self.record.get("category"))

    def _map_type(self, payload):
        if account_type := self._resolve_type():
            payload["Type"] = account_type

    def _map_status(self, payload):
        is_active = self.record.get("isActive")
        if payload.get("AccountID") is None:
            if is_active is False:
                raise InvalidPayloadError(
                    "Invalid value isActive=False when creating a new Account. "
                    "Only existing Accounts can be de-activated."
                )
            return
        if is_active is not None:
            payload["Status"] = "ACTIVE" if is_active else "ARCHIVED"

    def _map_account_currency(self, payload):
        account_type = payload.get("Type") or self._resolve_type()
        if account_type != "BANK":
            return
        if currency := self.record.get("currency"):
            payload["CurrencyCode"] = currency
            return
        if currency_id := self.record.get("currencyId"):
            if code := self._lookup_currency_by_code(currency_id):
                payload["CurrencyCode"] = code
                return
        if currency_name := self.record.get("currencyName"):
            if code := self._lookup_currency_code(currency_name):
                payload["CurrencyCode"] = code
