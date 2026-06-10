"""Unit tests for CustomerSchemaMapper."""

import pytest

from target_xero_v3.mappers.base_mapper import RecordNotFound
from target_xero_v3.mappers.customer_schema_mapper import CustomerSchemaMapper


class TestCustomerSchemaMapper:
    def test_maps_new_customer_to_xero_payload(self, customer_record, empty_reference_data):
        payload = CustomerSchemaMapper(
            customer_record, "Customers", reference_data=empty_reference_data
        ).to_xero()

        assert payload["Name"] == "Fake Customer Co (Sample)"
        assert payload["EmailAddress"] == "fake.customer@example.invalid"
        assert payload["Website"] == "https://example.invalid/fake-customer"
        assert payload["DefaultCurrency"] == "USD"
        assert payload["IsCustomer"] is True
        assert payload["IsSupplier"] is False
        assert "ContactID" not in payload

    def test_maps_customer_phone_numbers(self, customer_record, empty_reference_data):
        payload = CustomerSchemaMapper(
            customer_record, "Customers", reference_data=empty_reference_data
        ).to_xero()

        assert payload["Phones"] == [
            {"PhoneType": "MOBILE", "PhoneNumber": "+15555550100"},
            {"PhoneType": "DEFAULT", "PhoneNumber": "+15555550101"},
        ]

    def test_maps_customer_addresses(self, customer_record, empty_reference_data):
        payload = CustomerSchemaMapper(
            customer_record, "Customers", reference_data=empty_reference_data
        ).to_xero()

        assert len(payload["Addresses"]) == 2
        assert payload["Addresses"][0]["AddressType"] == "STREET"
        assert payload["Addresses"][0]["AddressLine1"] == "123 Fake Shipping Lane"
        assert payload["Addresses"][1]["AddressType"] == "POBOX"
        assert payload["Addresses"][1]["AddressLine1"] == "456 Fake Billing Road"

    def test_maps_existing_customer_by_name(self, customer_record, customer_reference_data):
        payload = CustomerSchemaMapper(
            customer_record, "Customers", reference_data=customer_reference_data
        ).to_xero()

        assert payload["ContactID"] == "00000000-0000-4000-8000-0000000000c1"

    def test_maps_existing_customer_by_id(self, customer_reference_data):
        record = {
            "id": "00000000-0000-4000-8000-0000000000c1",
            "companyName": "Fake Renamed Customer (Sample)",
        }
        payload = CustomerSchemaMapper(
            record, "Customers", reference_data=customer_reference_data
        ).to_xero()

        assert payload["ContactID"] == "00000000-0000-4000-8000-0000000000c1"
        assert payload["Name"] == "Fake Renamed Customer (Sample)"

    def test_raises_when_required_id_not_found(self, empty_reference_data):
        record = {"id": "00000000-0000-4000-8000-000000009999", "companyName": "Fake Missing Co"}

        with pytest.raises(RecordNotFound, match="id=00000000-0000-4000-8000-000000009999"):
            CustomerSchemaMapper(
                record, "Customers", reference_data=empty_reference_data
            ).to_xero()

    def test_maps_email_from_email_address_field(self, empty_reference_data):
        record = {
            "companyName": "Fake Alt Customer (Sample)",
            "emailAddress": "fake.alt.customer@example.invalid",
        }
        payload = CustomerSchemaMapper(
            record, "Customers", reference_data=empty_reference_data
        ).to_xero()

        assert payload["EmailAddress"] == "fake.alt.customer@example.invalid"

    def test_maps_contact_name_from_contact_name_splits_first_and_last(self, empty_reference_data):
        record = {
            "contactName": "Fakey McSample",
            "email": "fakey.mcsample@example.invalid",
        }
        payload = CustomerSchemaMapper(
            record, "Customers", reference_data=empty_reference_data
        ).to_xero()

        assert payload["Name"] == "Fakey McSample"
        assert payload["FirstName"] == "Fakey"
        assert payload["LastName"] == "McSample"
