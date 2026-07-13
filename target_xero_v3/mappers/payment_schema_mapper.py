from typing import Dict, Optional

from hotglue_etl_exceptions import InvalidPayloadError

from target_xero_v3.mappers.base_mapper import BaseMapper


class PaymentSchemaMapper(BaseMapper):
    parent_id_field: str
    parent_number_field: str
    parent_reference_key: str
    required_invoice_type: str

    def to_xero(self) -> Dict:
        if self.record.get("id"):
            raise InvalidPayloadError("Payment updates are not supported")
        payload = {
            **self._map_invoice(),
            **self._map_account(),
            **self._map_amount(),
            **self._map_date(),
            **self._map_currency_rate(),
            **self._map_reference(),
        }
        return payload

    def _find_parent(self):
        parents = self.reference_data.get(self.parent_reference_key, [])
        if parent_id := self.record.get(self.parent_id_field):
            found = next(
                (
                    parent
                    for parent in parents
                    if str(parent.get("InvoiceID")) == str(parent_id)
                ),
                None,
            )
            if found:
                self._validate_parent_type(found)
                return found
            raise InvalidPayloadError(
                f"{self.required_invoice_type} document with Id={parent_id} could not be found"
            )
        if parent_number := self.record.get(self.parent_number_field):
            found = next(
                (
                    parent
                    for parent in parents
                    if parent.get("InvoiceNumber") == parent_number
                ),
                None,
            )
            if found:
                self._validate_parent_type(found)
                return found
            raise InvalidPayloadError(
                f"{self.required_invoice_type} document with Number={parent_number} could not be found"
            )
        raise InvalidPayloadError(
            f"{self.parent_id_field} or {self.parent_number_field} is required for payment"
        )

    def _validate_parent_type(self, parent: dict):
        if parent.get("Type") != self.required_invoice_type:
            raise InvalidPayloadError(
                f"Expected {self.required_invoice_type} document, got {parent.get('Type')}"
            )

    def _map_invoice(self):
        parent = self._find_parent()
        return {"Invoice": {"InvoiceID": parent["InvoiceID"]}}

    def _find_payment_account(self):
        if account_id := self.record.get("accountId"):
            return self._find_account_by_id(account_id)
        if account_name := self.record.get("accountName"):
            return self._find_account_by_name(account_name)
        return None

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

    def _is_payment_account(self, account: dict) -> bool:
        return account.get("Type") == "BANK" or account.get("EnablePaymentsToAccount") is True

    def _map_account(self):
        account = self._find_payment_account()
        if not account:
            raise InvalidPayloadError("Payment account is required")
        if not self._is_payment_account(account):
            raise InvalidPayloadError(
                f"Account '{account.get('Name')}' cannot receive payments"
            )
        return {"Account": {"AccountID": account["AccountID"]}}

    def _map_amount(self):
        if (amount := self.record.get("amount")) is None:
            raise InvalidPayloadError("Payment amount is required")
        return {"Amount": amount}

    def _format_date(self, value) -> Optional[str]:
        if not value:
            return None
        return str(value)[:10]

    def _map_date(self):
        if date := self._format_date(self.record.get("paymentDate")):
            return {"Date": date}
        raise InvalidPayloadError("Payment date is required")

    def _map_currency_rate(self):
        if (exchange_rate := self.record.get("exchangeRate")) is not None:
            return {"CurrencyRate": exchange_rate}
        return {}

    def _map_reference(self):
        for field in ("paymentNumber", "transactionNumber"):
            if reference := self.record.get(field):
                return {"Reference": reference}
        return {}
