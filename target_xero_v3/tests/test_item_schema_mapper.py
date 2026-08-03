from target_xero_v3.mappers.item_schema_mapper import ItemSchemaMapper


class TestItemSchemaMapper:
    def test_maps_new_item_to_xero_payload(self, item_record, empty_reference_data):
        payload = ItemSchemaMapper(
            item_record, "Items", reference_data=empty_reference_data
        ).to_xero()

        assert payload["Name"] == "Fake Item (Sample)"
        assert payload["Code"] == "FAKE-ITEM-CODE-001"
        assert payload["IsPurchased"] is True
        assert payload["IsSold"] is True
        assert payload["SalesDetails"] == {"AccountCode": "200"}
        assert payload["PurchaseDetails"] == {"AccountCode": "400"}
        assert "ItemID" not in payload

    def test_maps_item_by_display_name(self, empty_reference_data):
        record = {"displayName": "Display Only Item (Sample)"}
        payload = ItemSchemaMapper(
            record, "Items", reference_data=empty_reference_data
        ).to_xero()

        assert payload["Name"] == "Display Only Item (Sample)"

    def test_maps_existing_item_by_name(self, item_record, item_reference_data):
        payload = ItemSchemaMapper(
            item_record, "Items", reference_data=item_reference_data
        ).to_xero()

        assert payload["ItemID"] == "00000000-0000-4000-8000-0000000000i1"

    def test_maps_existing_item_by_id(self, item_reference_data):
        record = {
            "id": "00000000-0000-4000-8000-0000000000i1",
            "name": "Fake Renamed Item (Sample)",
        }
        payload = ItemSchemaMapper(
            record, "Items", reference_data=item_reference_data
        ).to_xero()

        assert payload["ItemID"] == "00000000-0000-4000-8000-0000000000i1"
        assert payload["Name"] == "Fake Renamed Item (Sample)"

    def test_maps_existing_item_by_item_number(self, item_reference_data):
        record = {
            "itemNumber": "FAKE-ITEM-CODE-001",
            "name": "Fake Renamed Item (Sample)",
        }
        payload = ItemSchemaMapper(
            record, "Items", reference_data=item_reference_data
        ).to_xero()

        assert payload["ItemID"] == "00000000-0000-4000-8000-0000000000i1"

    def test_maps_bill_item_only(self, empty_reference_data):
        record = {"name": "Bill Item Only (Sample)", "isBillItem": True}
        payload = ItemSchemaMapper(
            record, "Items", reference_data=empty_reference_data
        ).to_xero()

        assert payload["IsPurchased"] is True
        assert "IsSold" not in payload

    def test_maps_invoice_item_only(self, empty_reference_data):
        record = {"name": "Invoice Item Only (Sample)", "isInvoiceItem": True}
        payload = ItemSchemaMapper(
            record, "Items", reference_data=empty_reference_data
        ).to_xero()

        assert payload["IsSold"] is True
        assert "IsPurchased" not in payload

    def test_maps_category_to_item_flags(self, empty_reference_data):
        for category, expected in (
            ("Purchase", {"IsPurchased": True, "IsSold": False}),
            ("Sale", {"IsPurchased": False, "IsSold": True}),
            ("Resale", {"IsPurchased": True, "IsSold": True}),
        ):
            payload = ItemSchemaMapper(
                {"name": f"Item {category}", "category": category},
                "Items",
                reference_data=empty_reference_data,
            ).to_xero()
            assert payload["IsPurchased"] == expected["IsPurchased"]
            assert payload["IsSold"] == expected["IsSold"]

    def test_explicit_item_flags_override_category(self, empty_reference_data):
        payload = ItemSchemaMapper(
            {
                "name": "Explicit Flags Win",
                "category": "Resale",
                "isBillItem": False,
                "isInvoiceItem": True,
            },
            "Items",
            reference_data=empty_reference_data,
        ).to_xero()

        assert payload == {
            "Name": "Explicit Flags Win",
            "IsPurchased": False,
            "IsSold": True,
        }

    def test_maps_accounts_by_id_and_name(self, empty_reference_data):
        record = {
            "name": "Account Lookup Item (Sample)",
            "accounts": [
                {
                    "accountType": "income",
                    "id": "00000000-0000-4000-8000-0000000000a1",
                },
                {"accountType": "expense", "name": "Advertising"},
                {"accountType": "cogs", "accountNumber": "500"},
            ],
        }
        payload = ItemSchemaMapper(
            record, "Items", reference_data=empty_reference_data
        ).to_xero()

        assert payload["SalesDetails"] == {"AccountCode": "200"}
        assert payload["PurchaseDetails"] == {
            "AccountCode": "400",
            "COGSAccountCode": "500",
        }

    def test_maps_tracked_inventory_accounts(self, empty_reference_data):
        record = {
            "name": "Tracked Item",
            "itemNumber": "BK-IT-TRK-01",
            "accounts": [
                {"accountType": "income", "accountNumber": "4100"},
                {"accountType": "cogs", "accountNumber": "5000"},
                {"accountType": "inventory", "accountNumber": "AZ0004"},
            ],
        }
        payload = ItemSchemaMapper(
            record, "Items", reference_data=empty_reference_data
        ).to_xero()

        assert payload["SalesDetails"] == {"AccountCode": "4100"}
        assert payload["PurchaseDetails"] == {"COGSAccountCode": "5000"}
        assert payload["InventoryAssetAccountCode"] == "AZ0004"

    def test_omits_unmapped_fields(self, empty_reference_data):
        record = {
            "name": "Minimal Item (Sample)",
            "externalId": "ignored",
            "quantityOnHand": 10,
            "type": "Inventory",
            "subsidiaryId": "ignored",
        }
        payload = ItemSchemaMapper(
            record, "Items", reference_data=empty_reference_data
        ).to_xero()

        assert payload == {"Name": "Minimal Item (Sample)"}

    def test_name_lookup_skips_reference_records_missing_name(self, empty_reference_data):
        record = {"name": "Fake Item (Sample)"}
        reference_data = {
            **empty_reference_data,
            "Items": [
                {"ItemID": "00000000-0000-4000-8000-0000000000i2", "Code": "HG-IP01"},
                {"ItemID": "00000000-0000-4000-8000-0000000000i1", "Name": "Fake Item (Sample)"},
            ],
        }
        payload = ItemSchemaMapper(record, "Items", reference_data=reference_data).to_xero()

        assert payload["ItemID"] == "00000000-0000-4000-8000-0000000000i1"
        assert payload["Name"] == "Fake Item (Sample)"
