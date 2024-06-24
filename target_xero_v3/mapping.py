import json
import os
from cgitb import lookup
from datetime import datetime

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


class UnifiedMapping:
    def __init__(self) -> None:
        pass

    def read_json_file(self, filename):
        # read file
        with open(os.path.join(__location__, f"{filename}"), "r") as filetoread:
            data = filetoread.read()

        # parse file
        content = json.loads(data)

        return content

    def map_custom_fields(self, payload, fields):
        # Populate custom fields.
        for key, val in fields:
            payload[key] = val
        return payload

    def map_xero_dict(self, record, mapping, payload,key=""):
        lookup_keys = mapping.keys()
        for lookup_key in lookup_keys:
            val = record.get(lookup_key, "")
            if val:
                payload[mapping[lookup_key]] = val
        if key:
            return {key: payload}
        return payload

    def map_xero_list(
        self, addresses_rows, address_mapping, payload, type="addresses", target="xero"
    ):
        if isinstance(addresses_rows, str):
            addresses_rows = json.loads(addresses_rows)
        if isinstance(addresses_rows, list):
            address_list = []
            for addresses in addresses_rows:
                address = {}
                for key in address_mapping.keys():
                    if key in addresses:
                        address[address_mapping[key]] = addresses[key]
                address = self.filter_ignore_keys(address)
                address_list.append(address)

            payload[type] = address_list
        else:
            address = {}
            for key in address_mapping.keys():
                if key in addresses_rows:
                    address[address_mapping[key]] = addresses_rows[key]
            if type == "Addresses":
                address = self.filter_ignore_keys(address)
                payload[type] = [address]
            else:
                payload[type] = address
        return payload

    # Modify this function and use recursion to support nested mapping
    def prepare_payload(self, record, endpoint="contact", target="xero"):
        mapping = self.read_json_file(f"mapping_{target}.json")
        ignore = mapping["ignore"]
        mapping = mapping[endpoint]
        payload = {}
        payload_return = {}
        lookup_keys = mapping.keys()
        for lookup_key in lookup_keys:
            if lookup_key == "addresses" and target == "xero":
                payload = self.map_xero_list(
                    record.get(lookup_key, {}), mapping[lookup_key], payload
                )
            elif lookup_key == "phoneNumbers" and target == "xero":
                payload = self.map_xero_list(
                    record.get(lookup_key, {}), mapping[lookup_key], payload, "phones"
                )
            elif lookup_key == "lineItems" and target == "xero":
                payload = self.map_xero_list(
                    record.get(lookup_key, []),
                    mapping[lookup_key],
                    payload,
                    type="LineItems",
                )
                #@TODO look into why this change was here.
                # if endpoint == "credit_notes":
                #     payload["LineItems"] = [payload["LineItems"]]
            elif lookup_key == "address" and target == "xero":
                payload = self.map_xero_list(
                    record.get(lookup_key, []),
                    mapping[lookup_key],
                    payload,
                    "Addresses",
                )
            elif lookup_key == "billItem" and target == "xero":
                payload = self.map_xero_list(
                    record.get(lookup_key, []),
                    mapping[lookup_key],
                    payload,
                    "PurchaseDetails",
                )
            elif lookup_key == "invoiceItem" and target == "xero":
                payload = self.map_xero_list(
                    record.get(lookup_key, []),
                    mapping[lookup_key],
                    payload,
                    "SalesDetails",
                )
            elif lookup_key == "contact" and target == "xero":
                if endpoint == "bills":
                    row = {"vendorName": record.get("vendorName")}
                else:
                    row = {"customerName": record.get("customerName")}

                if "customerId" in record:
                    row.update({"customerId": record["customerId"]})
                payload = self.map_xero_list(
                    row, mapping[lookup_key], payload, "Contact"
                )
            elif lookup_key == "customerRef" and target == "xero":
                payload = self.map_xero_dict(
                    record.get(lookup_key, {}), mapping[lookup_key], payload, "Contact"
                )

            elif lookup_key == "custom_fields":
                # handle custom fields
                payload = self.map_custom_fields(payload, mapping[lookup_key])
            else:
                val = record.get(lookup_key, "")
                if isinstance(val, datetime):
                    val = val.strftime("%Y-%m-%d")
                if val:
                    payload[mapping[lookup_key]] = val

        # Need name for Opportunity
        if endpoint == "oppurtunity" or endpoint == "account":
            ignore.remove("Name")

        # inject special fields of shopify product before returning payload
        if target == "shopify" and endpoint == "products":
            payload = self.inject_sopify_product_fields(record, payload, mapping)

        # filter ignored keys
        payload = self.filter_ignore_keys(payload)
        return payload

    def filter_ignore_keys(self, payload, target="xero"):
        payload_return = {}
        mapping = self.read_json_file(f"mapping_{target}.json")
        ignore = mapping["ignore"]
        # filter ignored keys
        for key in payload.keys():
            if key not in ignore:
                payload_return[key] = payload[key]
        return payload_return
