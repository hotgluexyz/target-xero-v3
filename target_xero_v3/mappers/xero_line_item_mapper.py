from typing import Dict, Optional

from hotglue_etl_exceptions import InvalidPayloadError

from target_xero_v3.mappers.base_mapper import BaseMapper

DIMENSION_FIELDS = (
    ("class", "classId", "className"),
    ("location", "locationId", "locationName"),
    ("department", "departmentId", "departmentName"),
)


class XeroLineItemMapper(BaseMapper):
    field_mappings: Dict[str, str] = {}

    def _map_line_item_id(self):
        if line_item_id := self.record.get("id"):
            return {"LineItemID": line_item_id}
        return {}

    def _find_item(self):
        items = self.reference_data.get("Items", [])
        if item_id := self.record.get("itemId"):
            found = next(
                (item for item in items if str(item.get("ItemID")) == str(item_id)),
                None,
            )
            if found:
                return found
        if item_number := self.record.get("itemNumber"):
            found = next(
                (item for item in items if item.get("Code") == item_number),
                None,
            )
            if found:
                return found
        if item_name := self.record.get("itemName"):
            return next(
                (item for item in items if item.get("Name") == item_name),
                None,
            )
        return None

    def _map_item(self):
        if item_code := self.record.get("itemNumber"):
            return {"ItemCode": item_code}
        found_item = self._find_item()
        if found_item and found_item.get("Code"):
            return {"ItemCode": found_item["Code"]}
        if self.record.get("itemId") or self.record.get("itemName"):
            item_id = self.record.get("itemId")
            item_name = self.record.get("itemName")
            raise InvalidPayloadError(
                f"Item with Id={item_id} / Name={item_name} could not be found"
            )
        return {}

    def _find_account_by_id(self, account_id: str):
        return next(
            (
                account
                for account in self.reference_data.get("Accounts", [])
                if str(account.get("AccountID")) == str(account_id)
            ),
            None,
        )

    def _find_account_by_name(self, account_name: str):
        return next(
            (
                account
                for account in self.reference_data.get("Accounts", [])
                if account.get("Name") == account_name
            ),
            None,
        )

    def _map_account(self):
        if account_number := self.record.get("accountNumber"):
            return {"AccountCode": account_number}
        if account_id := self.record.get("accountId"):
            found = self._find_account_by_id(account_id)
            if found and found.get("Code"):
                return {"AccountCode": found["Code"]}
            raise InvalidPayloadError(f"Account with Id={account_id} could not be found")
        if account_name := self.record.get("accountName"):
            found = self._find_account_by_name(account_name)
            if found and found.get("Code"):
                return {"AccountCode": found["Code"]}
            raise InvalidPayloadError(f"Account '{account_name}' could not be found")
        return {}

    def _dimension_mappings(self):
        return (
            self.reference_data.get("tenant_config", {})
            .get("xero", {})
            .get("dimension_mappings", {})
        )

    def _find_tracking_option(
        self, category: dict, option_id: Optional[str], option_name: Optional[str]
    ):
        options = category.get("Options") or []
        if option_id:
            found = next(
                (
                    option
                    for option in options
                    if str(option.get("TrackingOptionID")) == str(option_id)
                ),
                None,
            )
            if found:
                return found
        if option_name:
            return next(
                (option for option in options if option.get("Name") == option_name),
                None,
            )
        return None

    def _tracking_entry(self, category: dict, option: dict):
        return {
            "TrackingCategoryID": category["TrackingCategoryID"],
            "Name": category.get("Name"),
            "Option": option.get("Name"),
            "TrackingOptionID": option.get("TrackingOptionID"),
        }

    def _map_tracking(self):
        tracking = []
        categories = self.reference_data.get("TrackingCategories", [])
        dimension_mappings = self._dimension_mappings()
        for dim_key, id_field, name_field in DIMENSION_FIELDS:
            category_name = dimension_mappings.get(dim_key)
            if not category_name:
                continue
            option_id = self.record.get(id_field)
            option_name = self.record.get(name_field)
            if not option_id and not option_name:
                continue
            category = next(
                (entry for entry in categories if entry.get("Name") == category_name),
                None,
            )
            if not category:
                raise InvalidPayloadError(
                    f"Tracking category '{category_name}' not found"
                )
            option = self._find_tracking_option(category, option_id, option_name)
            if not option:
                raise InvalidPayloadError(
                    f"Tracking option Id={option_id} / Name={option_name} not found "
                    f"in category '{category_name}'"
                )
            tracking.append(self._tracking_entry(category, option))
        return {"Tracking": tracking} if tracking else {}
