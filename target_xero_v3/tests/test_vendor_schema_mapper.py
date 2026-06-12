"""Unit tests for VendorSchemaMapper."""

from target_xero_v3.mappers.vendor_schema_mapper import VendorSchemaMapper


class TestVendorSchemaMapper:
    def test_maps_new_vendor_to_xero_payload(self, vendor_record, empty_reference_data):
        payload = VendorSchemaMapper(
            vendor_record, "Vendors", reference_data=empty_reference_data
        ).to_xero()

        assert payload["Name"] == "Fake Vendor LLC (Sample)"
        assert payload["ContactNumber"] == "FAKE-VEND-NUM-001"
        assert payload["EmailAddress"] == "fake.vendor@example.invalid"
        assert payload["DefaultCurrency"] == "USD"
        assert "Website" not in payload
        assert "ContactID" not in payload

    def test_maps_vendor_phone_numbers(self, vendor_record, empty_reference_data):
        payload = VendorSchemaMapper(
            vendor_record, "Vendors", reference_data=empty_reference_data
        ).to_xero()

        assert payload["Phones"] == [
            {"PhoneType": "DEFAULT", "PhoneNumber": "+15555550200"},
        ]

    def test_maps_vendor_addresses(self, vendor_record, empty_reference_data):
        payload = VendorSchemaMapper(
            vendor_record, "Vendors", reference_data=empty_reference_data
        ).to_xero()

        assert len(payload["Addresses"]) == 2
        assert payload["Addresses"][0]["AddressType"] == "POBOX"
        assert payload["Addresses"][0]["AddressLine1"] == "789 Not A Real Avenue"
        assert payload["Addresses"][0]["AddressLine2"] is None
        assert payload["Addresses"][1]["AddressType"] == "STREET"

    def test_maps_existing_vendor_by_name(self, vendor_record, vendor_reference_data):
        payload = VendorSchemaMapper(
            vendor_record, "Vendors", reference_data=vendor_reference_data
        ).to_xero()

        assert payload["ContactID"] == "00000000-0000-4000-8000-0000000000v1"

    def test_maps_existing_vendor_by_id(self, vendor_reference_data):
        record = {
            "id": "00000000-0000-4000-8000-0000000000v1",
            "vendorName": "Fake Renamed Vendor (Sample)",
        }
        payload = VendorSchemaMapper(
            record, "Vendors", reference_data=vendor_reference_data
        ).to_xero()

        assert payload["ContactID"] == "00000000-0000-4000-8000-0000000000v1"
        assert payload["Name"] == "Fake Renamed Vendor (Sample)"

    def test_omits_contact_id_when_id_not_in_reference(self, empty_reference_data):
        record = {
            "id": "00000000-0000-4000-8000-000000009998",
            "vendorName": "Fake Missing Vendor (Sample)",
        }
        payload = VendorSchemaMapper(
            record, "Vendors", reference_data=empty_reference_data
        ).to_xero()

        assert "ContactID" not in payload
        assert payload["Name"] == "Fake Missing Vendor (Sample)"

    def test_maps_full_name_for_individual_vendor(self, empty_reference_data):
        record = {
            "fullName": "Fakey McVendor",
            "firstName": "Fakey",
            "lastName": "McVendor",
            "email": "fakey.mcvendor@example.invalid",
        }
        payload = VendorSchemaMapper(
            record, "Vendors", reference_data=empty_reference_data
        ).to_xero()

        assert payload["Name"] == "Fakey McVendor"
        assert payload["FirstName"] == "Fakey"
        assert payload["LastName"] == "McVendor"

    def test_maps_name_from_first_and_last_when_vendor_name_and_full_name_absent(
        self, empty_reference_data
    ):
        record = {
            "firstName": "Fakey",
            "lastName": "McVendor",
            "email": "fakey.mcvendor@example.invalid",
        }
        payload = VendorSchemaMapper(
            record, "Vendors", reference_data=empty_reference_data
        ).to_xero()

        assert payload["Name"] == "Fakey McVendor"

    def test_omits_name_when_vendor_name_missing(self, empty_reference_data):
        payload = VendorSchemaMapper(
            {"email": "no.name@example.invalid"},
            "Vendors",
            reference_data=empty_reference_data,
        ).to_xero()

        assert "Name" not in payload
        assert payload["EmailAddress"] == "no.name@example.invalid"

    def test_maps_is_active_to_contact_status(self, empty_reference_data):
        active = VendorSchemaMapper(
            {"vendorName": "Active Fake Vendor", "isActive": True},
            "Vendors",
            reference_data=empty_reference_data,
        ).to_xero()
        archived = VendorSchemaMapper(
            {"vendorName": "Archived Fake Vendor", "isActive": False},
            "Vendors",
            reference_data=empty_reference_data,
        ).to_xero()

        assert active["ContactStatus"] == "ACTIVE"
        assert archived["ContactStatus"] == "ARCHIVED"
