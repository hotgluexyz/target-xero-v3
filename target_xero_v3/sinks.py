"""Xero target sink class, which handles writing streams."""
import json
from datetime import datetime
from typing import Dict, List, Optional

from singer_sdk.plugin_base import PluginBase
from singer_sdk.sinks import BatchSink

from target_xero_v3.client import XeroClient
from target_xero_v3.mapping import UnifiedMapping
import singer

LOGGER = singer.get_logger()
from target_hotglue.client import HotglueSink, HotglueBatchSink


class XeroSink:
    """Xero target sink class."""

    max_size = 1000

    def __init__(
        self,
        target: PluginBase,
        stream_name: str,
        schema: Dict,
        key_properties: Optional[List[str]],
    ) -> None:
        super().__init__(target, stream_name, schema, key_properties)
        # Save config for refresh_token saving
        self.client = None
        self.config_file = target.config_file
        self.all_items = []
        self.acc_list = []
        self.account_codes = []
        self.cat_list = []
        self.tax_list = []
        self.aus_uk_nz = bool(self.config.get("aus_nz_uk"))
        # Default set to true for Tessaract test it more easyily.

    def get_account_status(self, record):
        client = self.get_client()
        # Check if the invoice exists
        try:
            invoice = client.filter(
                "Invoices", invoice_number=record.get("invoiceNumber")
            )
            # Check if it has been approved
            if invoice[0].get("Status") not in ["AUTHORISED", "PAID"]:
                # If status is not 'AUTHORISED' or 'PAID'
                # Return the record to be updated
                return record
            # Else return an empty record
            return None
        except:
            # If the GET fails just pass the record and it will create a new Invoice
            return record

    def get_tax_list(self):
        if not self.tax_list:
            client = self.get_client()
            self.tax_list = {
                i["Name"]: i["TaxType"] for i in client.filter("Tax_Rates")
            }
        return self.tax_list

    def get_accounts_list(self):
        if not self.acc_list:
            client = self.get_client()
            self.acc_list = client.filter("Accounts")
        return self.acc_list

    def get_account_code(self, account_name):
        accounts = self.get_accounts_list()
        # Make sure we don't do lookup on string account code
        account_name = account_name.lower()
        if account_name.isdigit():
            return account_name
        if not self.account_codes:
            codes = {}
            for account in accounts:
                if "Code" in account:
                    codes.update({account["Name"].lower(): account["Code"]})
            self.account_codes = codes
            del codes
        if account_name in self.account_codes:
            return self.account_codes[account_name]
        else:
            return None

    def get_tracking_categories_list(self):
        if not self.cat_list:
            client = self.get_client()
            self.cat_list = client.filter("Tracking_Categories")
        return self.cat_list

    def prepare_accounts_categories(self):
        acc_list = self.get_accounts_list()
        cat_list = self.get_tracking_categories_list()

        # Process accounts
        accounts = {}
        for account in acc_list:
            if account.get("Code") is None:
                continue

            name = account["Name"]
            code = account["Code"]
            acc_ref = {"Name": name, "Code": code}
            accounts[code] = acc_ref
            accounts[name] = acc_ref

        # Process categories
        categories = {}
        for category in cat_list:
            name = category["Name"]
            options = [x["Name"] for x in category["Options"]]

            for option in options:
                categories[option] = {"Name": name, "Option": option}
        return accounts, categories

    def build_lines(self, lines):
        return_lines = []
        accounts, categories = self.prepare_accounts_categories()

        for row in lines:
            posting_type = row["postingType"]
            line_amt = abs(row["amount"])
            if posting_type.lower() == "credit":
                line_amt = -1 * line_amt

            line_item = {"Description": row["description"], "LineAmount": line_amt}

            acct_num = str(row["accountNumber"])
            acct_name = row["accountName"]
            acct_code = accounts.get(acct_num, accounts.get(acct_name, {})).get("Code")

            if acct_code is not None:
                line_item["AccountCode"] = acct_code
            else:
                raise Exception(
                    f"Account is missing on Journal Entry! Name={acct_name} No={acct_num}"
                )

            if row.get("customerName"):
                tracking = categories.get(row.get("customerName"))
                line_item["Tracking"] = [tracking]

            return_lines.append(line_item)
        return return_lines

    def process_journalentries(self, record):
        date = record["transactionDate"]
        date = datetime.strptime(date, "%m/%d/%Y")
        date = date.strftime("%Y-%m-%d")

        # Create the entry
        entry = {
            "Narration": record["id"],
            "Date": date,
            "Status": "POSTED",
        }
        lines = {}
        lines["JournalLines"] = self.build_lines(record["lines"])

        entry.update(lines)
        return entry

    def process_taxrates(self, record):
        # Create the tax_rate
        entry = {
            "Name": record["name"][:50],
            "TaxComponents": [
                {"Name": record["name"][:50], "Rate": str(record["rate"])}
            ],
        }

        if self.aus_uk_nz:
            # "ReportTaxType": record["transType"][:50], # TODO : Allow only with AUS, UK, NZ.
            entry.update({"ReportTaxType": record["transType"][:50]})

        return entry

    def prepare_payload(self, record, stream_name):
        mapping = UnifiedMapping()
        payload = mapping.prepare_payload(record, stream_name, target="xero")

        if stream_name == "contacts":
            for list_field in ["addresses", "phones"]:
                if isinstance(payload.get(list_field), dict):
                    payload.pop(list_field)
        elif stream_name == "items":
            for list_field in ["PurchaseDetails", "SalesDetails"]:
                if not payload.get(list_field):
                    payload.pop(list_field)
        elif stream_name == "invoices":
            client = self.get_client()
            contact_detail = None
            # Do bills need this check to?
            if "customerEmail" in record:
                contact_detail = client.filter(
                    "Contacts",
                    where='EmailAddress=="{}"'.format(record["customerEmail"]),
                )
                if contact_detail:
                    contact_detail = contact_detail[0]
                    payload["Contact"]["ContactID"] = contact_detail["ContactID"]
                else:
                    LOGGER.warning(
                        f"Warning: Contact with email: {record['customerEmail']} not found."
                    )

            # Look for customer using default object only if Email lookup failed
            if "Contact" in payload and contact_detail is None:
                if "customerId" not in payload["Contact"]:
                    # invoices = client.filter("Invoices",IDs='INV-ID')
                    contact_detail = client.filter(
                        "Contacts",
                        where='Name=="{}"'.format(payload["Contact"]["Name"]),
                    )
                    if contact_detail:
                        contact_detail = contact_detail[0]
                        payload["Contact"]["ContactID"] = contact_detail["ContactID"]
                    else:
                        LOGGER.warning(
                            f"Warning: Contact {payload['Contact']['Name']} not found. Skipping."
                        )
                        payload.update({"contact_not_found": True})
                        return payload

                payload["LineItems"] = self.prepare_invoice_lineitems(payload)
            if "Contact" not in payload:
                payload.update({"contact_not_found": True})        
            elif "ContactID" not in payload['Contact']:
                payload.update({"contact_not_found": True})

        elif stream_name == "credit_notes":
            client = self.get_client()
            # invoices = client.filter("Invoices",IDs='INV-ID')
            contact_detail = client.filter(
                "Contacts",
                where='Name=="{}"'.format(payload["customerName"]),
            )
            for i, item in enumerate(payload["LineItems"]):
                account_detail = client.filter(
                    "Accounts",
                    where='Name=="{}"'.format(item["AccountCode"]),
                )
                payload["LineItems"][i]["AccountCode"] = account_detail[0]["Code"]

            if contact_detail:
                contact_detail = contact_detail[0]
                if not payload.get("Contact"):
                    payload["Contact"] = {}
                payload["Contact"]["ContactID"] = contact_detail["ContactID"]

            if payload.get("Date"):
                payload["Date"] = payload["Date"].split("T")[0]

            payload["LineAmountTypes"] = "Exclusive"
            payload["Type"] = "ACCPAYCREDIT"

        return payload

    def prepare_invoice_lineitems(self, payload):
        lineItems = payload["LineItems"]
        items = []
        allItems = self.get_all_items()
        self.tax_list = None
        taxes = self.get_tax_list()
        for lineItem in lineItems:
            itemName = None
            if lineItem.get("ItemCode"):
                itemName = lineItem.get("ItemCode")
                lookup_key = "Code"
            elif lineItem.get("ItemName"):
                itemName = lineItem.get("ItemName")
                lookup_key = "Name"
            if itemName:
                item = self.get_item(itemName, lookup_key)
                lineItem.pop("ItemName", None)
                if item:
                    lineItem["Item"] = {
                        "ItemID": item["ItemID"],
                        "Name": item["Name"],
                        "Code": item["Code"],
                    }
                    lineItem["ItemCode"] = item["Code"]
            if lineItem.get("Description") is None:
                lineItem["Description"] = "Created via API"
            tax_type = lineItem.get("TaxType")
            if taxes is not None:
                if tax_type in taxes.keys() and tax_type is not None:
                    lineItem["TaxType"] = taxes[tax_type]
            if "AccountCode" in lineItem:
                # check if we need to lookup account code
                if isinstance(lineItem["AccountCode"], str):
                    lineItem["AccountCode"] = self.get_account_code(
                        lineItem["AccountCode"]
                    )

            tracking_items = []
            client = self.get_client()
            if "classId" not in lineItem:
                tracking_detail = None
                if "className" in lineItem:
                    tracking_detail = client.filter(
                        "TrackingCategories",
                        where='Name=="{}"'.format(lineItem["className"]),
                    )
                if tracking_detail:
                    tracking_detail = tracking_detail[0]
                    del tracking_detail["Status"]
                    del tracking_detail["Options"]
                    tracking_items.append(tracking_detail)
            else:
                if "classId" in lineItem and "className" in lineItem:
                    tracking_items.append(
                        {
                            "TrackingCategoryID": lineItem.get("classId"),
                            "Name": lineItem.get("className"),
                        }
                    )

            if len(tracking_items) > 0:
                lineItem["Tracking"] = tracking_items
            #Delete tracking keys from base item    
            if "classId" in lineItem:
                del lineItem["classId"]
            if "className" in lineItem:
                del lineItem["className"]
            items.append(lineItem)
        return items

    def get_item(self, lookupValue, key="Name"):
        return_item = {}
        for item in self.all_items:
            if item[key] == lookupValue:
                return_item = item
                break
        return return_item

    def get_all_items(self):
        if not self.all_items:
            client = self.get_client()
            self.all_items = client.filter("Items")
        return self.all_items

    def get_client(self):
        if self.client is None:
            self.client = XeroClient(dict(self.config), self.config_file)
            # Refresh the credentials if the access_token is invalid
            self.client.refresh_credentials()
        return self.client


class CustomerSink(XeroSink, HotglueBatchSink):
    endpoint = "Contacts"
    name = "Customers"
    stream_endpoint = "contacts"
    isCustomer = True
    isSupplier = False

    def transform_customer_payload(self, payload, record):
        for list_field in ["addresses", "phones"]:
            if isinstance(payload.get(list_field), dict):
                payload[list_field] = [payload[list_field]]
        payload["IsCustomer"] = self.isCustomer
        payload["IsSupplier"] = self.isSupplier
        # We need to set address type
        if payload.get("addresses"):
            for address in payload.get("addresses"):
                # lets default to Street type for now.
                address.update({"AddressType": "STREET"})
        if payload.get("phones"):
            for phone in payload.get("phones"):
                # lets default to Street type for now.
                if phone:
                    phone.update({"PhoneType": phone.get("PhoneType").upper()})
        # Populate Contact Name
        if record.get("contactName") and not payload.get("FirstName"):
            contact_name = record.get("contactName").split()
            last_name = contact_name[1] if len(contact_name) == 2 else None
            payload.update({"FirstName": contact_name[0], "LastName": last_name})

        return payload

    def process_batch_record(self, record: dict, context: dict) -> dict:
        mapping = UnifiedMapping()
        payload = mapping.prepare_payload(record, self.stream_endpoint, target="xero")
        payload = self.transform_customer_payload(payload, record)
        return payload

    def handle_batch_response(self, response) -> dict:
        state = {}
        results = []
        try:
            response = response.json()
            if "Contacts" in response:
                for res in response["Contacts"]:
                    # Xero is not returning which contact was updated/new so all valid entries are success.
                    if res["HasValidationErrors"]:
                        results.append({"success": False})
                    else:
                        results.append({"success": True, "id": res.get("ContactID")})
            elif "Type" in response:
                if response["Type"] == "ValidationException":
                    results.append({"success": False})
        except Exception as e:
            self.logger.info(f"error: {e}")
        return {"state_updates": results}

    def make_batch_request(self, records: List[dict]):
        client = self.get_client()
        rec = {self.endpoint: records}
        self.logger.info(f"Processing {self.stream_name}\n")
        res = client.push(self.endpoint, rec)
        try:
            contact_ids = [contact["ContactID"] for contact in res.json()["Contacts"]]
            self.logger.info("Customers batch uploaded with ids", str(contact_ids))
            return res
        except:
            self.update_state({"error_response": res.json()})
            return

    def process_batch(self, context: dict) -> None:
        if not self.latest_state:
            self.init_state()

        raw_records = context["records"]

        records = list(
            map(lambda e: self.process_batch_record(e[1], e[0]), enumerate(raw_records))
        )

        response = self.make_batch_request(records)

        result = self.handle_batch_response(response)

        for state in result.get("state_updates", list()):
            self.update_state(state)


class XeroRecordSink(XeroSink, HotglueSink):
    def upsert_record(self, record: dict, context: dict):
        id = None
        client = self.get_client()
        state_updates = dict()
        response = client.push(self.endpoint, record)
        self.log_request_response(record, response)
        if response.status_code in [200]:
            state_updates["success"] = True
            id = response.json().get("Id")
        elif response.status_code == 400:
            state_updates["success"] = False
            state_updates["error"] = response.json()
        return id, response.ok, state_updates

    def log_request_response(self, record, response):
        self.logger.info(f"Sending payload for stream {self.name}: {record}")
        self.logger.info(f"Response: {response.text}")


class TaxRatesSink(XeroRecordSink):
    endpoint = "TaxRates"
    name = "TaxRates"
    stream_endpoint = "contacts"

    def preprocess_record(self, record: dict, context: dict) -> dict:
        taxes = self.get_tax_list()
        entry = self.process_taxrates(record)
        if not entry["Name"] in taxes.keys():
            context["records"].append(entry)
        return entry


class ItemsSink(XeroRecordSink):
    endpoint = "Items"
    name = "Items"
    stream_endpoint = "items"

    def preprocess_record(self, record: dict, context: dict) -> dict:
        mapping = UnifiedMapping()
        payload = mapping.prepare_payload(record, self.stream_endpoint)
        if not payload.get("Code"):
            payload["Code"] = payload.get("Name")
        for list_field in ["PurchaseDetails", "SalesDetails"]:
            if not payload.get(list_field):
                payload.pop(list_field)
        return payload


class JournalEntriesSink(XeroRecordSink):
    endpoint = "Manual_Journals"
    name = "JournalEntries"

    def preprocess_record(self, record: dict, context: dict) -> dict:
        payload = self.process_journalentries(record)
        return payload


class InvoicesSink(XeroRecordSink):
    endpoint = "Invoices"
    name = "Invoices"
    stream_endpoint = "invoices"

    def preprocess_record(self, record: dict, context: dict) -> dict:
        invoice_number = record.get("invoiceNumber")
        record = self.get_account_status(record)
        if record:
            invoice = self.prepare_payload(record, self.stream_endpoint)
            if invoice is not None:
                invoice["Type"] = self.config.get("invoice_type", "ACCREC")
            return invoice
        return {"id": invoice_number}

    def upsert_record(self, record: dict, context: dict):
        state_updates = dict()
        if record:
            id = None
            client = self.get_client()
            # If contact is not found don't process it but let the target create payload's hash
            if "contact_not_found" in record:
                state_updates["success"] = False
                state_updates[
                    "message"
                ] = f"Contact for invoice {record['InvoiceNumber']} not found."
                return None, False, state_updates

            response = client.push(self.endpoint, record)
            self.log_request_response(record, response)
            if response.status_code in [200]:
                state_updates["success"] = True
                id = response.json().get("Id")
            elif response.status_code == 400:
                state_updates["success"] = False
                state_updates["message"] = response.text
            return id, response.ok, state_updates
        return record.get("id"), True, state_updates


class BillsSink(XeroRecordSink):
    endpoint = "Invoices"
    name = "Bills"
    stream_endpoint = "bills"

    def preprocess_record(self, record: dict, context: dict) -> dict:
        record = self.get_account_status(record)
        if record:
            invoice = self.prepare_payload(record, self.stream_endpoint)
            if invoice is not None:
                invoice["Type"] = self.config.get("invoice_type", "ACCPAY")
        return invoice


class JournalEntriesSink(XeroRecordSink):
    endpoint = "Manual_Journals"
    name = "JournalEntries"

    def preprocess_record(self, record: dict, context: dict) -> dict:
        entry = self.process_journalentries(record)
        return entry


class CreditNotesSink(XeroRecordSink):
    endpoint = "CreditNotes"
    name = "CreditNotes"
    stream_endpoint = "credit_notes"

    def preprocess_record(self, record: dict, context: dict) -> dict:
        item = self.prepare_payload(record, self.stream_endpoint)
        return item


class QuotesSink(XeroRecordSink):
    endpoint = "Quotes"
    name = "Quotes"
    stream_endpoint = "quotes"

    def preprocess_record(self, record: dict, context: dict) -> dict:
        item = self.prepare_payload(record, self.stream_endpoint)
        return item


class VendorsSink(CustomerSink):
    name = "Vendors"
    isSupplier = True

    def process_batch_record(self, record: dict, context: dict) -> dict:
        if record.get("vendorName"):
            record.update({"customerName": record.get("vendorName")})
        mapping = UnifiedMapping()
        payload = mapping.prepare_payload(record, self.stream_endpoint, target="xero")
        payload = self.transform_customer_payload(payload, record)
        return payload
