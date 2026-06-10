"""Unit tests for VendorSchemaMapper."""

import pytest

from target_xero_v3.mappers.base_mapper import RecordNotFound
from target_xero_v3.mappers.vendor_schema_mapper import VendorSchemaMapper


class TestVendorSchemaMapper:
    def test_maps_new_vendor_to_xero_payload(self, vendor_record, empty_reference_data):
        payload = VendorSchemaMapper(
            vendor_record, "Vendors", reference_data=empty_reference_data
        ).to_xero()

        assert payload["Name"] == "Fake Vendor LLC (Sample)"
        assert payload["EmailAddress"] == "fake.vendor@example.invalid"
        assert payload["Website"] == "https://example.invalid/fake-vendor"
        assert payload["DefaultCurrency"] == "USD"
        assert payload["IsCustomer"] is False
        assert payload["IsSupplier"] is True
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

    def test_raises_when_required_id_not_found(self, empty_reference_data):
        record = {
            "id": "00000000-0000-4000-8000-000000009998",
            "vendorName": "Fake Missing Vendor (Sample)",
        }

        with pytest.raises(RecordNotFound, match="id=00000000-0000-4000-8000-000000009998"):
            VendorSchemaMapper(
                record, "Vendors", reference_data=empty_reference_data
            ).to_xero()

    def test_uses_vendor_name_when_company_name_absent(self, empty_reference_data):
        record = {
            "vendorName": "Fake Solo Vendor (Sample)",
            "email": "fake.solo.vendor@example.invalid",
        }
        payload = VendorSchemaMapper(
            record, "Vendors", reference_data=empty_reference_data
        ).to_xero()

        assert payload["Name"] == "Fake Solo Vendor (Sample)"
