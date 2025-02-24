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

    def prepare_trackings_using_custom_fields(self, customFields):
        """
        Prepares Xero-compatible Tracking Categories from customFields.

        Args:
            customFields (list): A list of custom fields to be mapped to Xero tracking categories.

        Returns:
            list: A list of tracking categories formatted for Xero.
        """
        # Ensure customFields is a list, return empty list if not
        if not isinstance(customFields, list):
            return []

        # Using list comprehension for cleaner and more Pythonic mapping
        return [
            {"Name": field.get("name"), "Option": field.get("value")}
            for field in customFields
            if field.get("name") and field.get("value")
        ]

    def map_xero_list(
        self, rows, mapping, payload, type="addresses", target="xero"
    ):
        """
        Maps a list of records to Xero-compatible structures.

        Args:
            rows (list or str): Input data rows to be mapped.
            mapping (dict): Mapping configuration for the target type.
            payload (dict): The output payload to be populated.
            type (str): The type of items being mapped (e.g., 'addresses', 'LineItems').
            target (str): The target system, default is 'xero'.

        Returns:
            dict: The updated payload with mapped items.
        """
        # Convert string to JSON if necessary
        if isinstance(rows, str):
            rows = json.loads(rows)
        
        # If rows is a list, process each item in the list
        if isinstance(rows, list):
            items = []
            for row in rows:
                record = {}
                for key in mapping.keys():
                    if key not in row:
                        continue

                    if type == 'LineItems' and key == 'customFields':
                        record['Tracking'] = self.prepare_trackings_using_custom_fields(row[key])
                    else:
                        record[mapping[key]] = row[key]
                record = self.filter_ignore_keys(record)
                items.append(record)

            payload[type] = items

        # If rows is a single dictionary, process it accordingly
        elif isinstance(rows, dict):
            record = {
                mapping[key]: rows[key]
                for key in mapping
                if key in rows
            }

            if type == "Addresses":
                payload[type] = [self.filter_ignore_keys(record)]
            else:
                payload[type] = self.filter_ignore_keys(record)
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
        ignore_keys = self.read_json_file(f"mapping_{target}.json").get("ignore", [])
        return {key: value for key, value in payload.items() if key not in ignore_keys}
