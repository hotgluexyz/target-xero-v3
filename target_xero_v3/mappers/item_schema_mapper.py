from typing import Dict, Optional

from target_xero_v3.mappers.base_mapper import BaseMapper

ACCOUNT_TYPE_FIELDS = {
    "income": ("SalesDetails", "AccountCode"),
    "expense": ("PurchaseDetails", "AccountCode"),
    "cogs": ("PurchaseDetails", "COGSAccountCode"),
}

CATEGORY_FLAGS = {
    "purchase": {"IsPurchased": True, "IsSold": False},
    "sale": {"IsPurchased": False, "IsSold": True},
    "resale": {"IsPurchased": True, "IsSold": True},
}


class ItemSchemaMapper(BaseMapper):
    existing_record_pk_mappings = [
        {"record_field": "id", "xero_field": "ItemID", "required_if_present": True},
        {"record_field": "itemNumber", "xero_field": "Code", "required_if_present": False},
        {"record_field": "name", "xero_field": "Name", "required_if_present": False},
        {"record_field": "displayName", "xero_field": "Name", "required_if_present": False},
    ]

    field_mappings = {
        "itemNumber": "Code",
    }

    def to_xero(self) -> Dict:
        payload = {
            **self._map_internal_id(),
            **self._map_name("name", "displayName"),
            **self._map_item_flags(),
            **self._map_accounts(),
        }
        self._map_fields(payload)
        return payload

    def _map_internal_id(self):
        if self.existing_record:
            return {"ItemID": self.existing_record["ItemID"]}
        return {}

    def _map_item_flags(self):
        payload = {}
        if self.record.get("isBillItem") is not None:
            payload["IsPurchased"] = self.record["isBillItem"]
        if self.record.get("isInvoiceItem") is not None:
            payload["IsSold"] = self.record["isInvoiceItem"]
        if "IsPurchased" not in payload and "IsSold" not in payload:
            category = self.record.get("category")
            if category and (flags := CATEGORY_FLAGS.get(category.casefold())):
                payload.update(flags)
        return payload

    def _resolve_account_code(self, item_account: dict) -> Optional[str]:
        if account_number := item_account.get("accountNumber"):
            return account_number
        accounts = self.reference_data.get("Accounts", [])
        if account_id := item_account.get("id"):
            for account in accounts:
                if str(account.get("AccountID")) == str(account_id):
                    return account.get("Code")
                if str(account.get("Code")) == str(account_id):
                    return account.get("Code")
        if name := item_account.get("name"):
            for account in accounts:
                if account.get("Name") == name:
                    return account.get("Code")
        return None

    def _map_accounts(self):
        details = {"SalesDetails": {}, "PurchaseDetails": {}}
        for item_account in self.record.get("accounts") or []:
            account_type = (item_account.get("accountType") or "").casefold()
            mapping = ACCOUNT_TYPE_FIELDS.get(account_type)
            code = self._resolve_account_code(item_account)
            if not mapping or not code:
                continue
            section, field = mapping
            details[section][field] = code

        payload = {}
        if details["SalesDetails"]:
            payload["SalesDetails"] = details["SalesDetails"]
        if details["PurchaseDetails"]:
            payload["PurchaseDetails"] = details["PurchaseDetails"]
        return payload
