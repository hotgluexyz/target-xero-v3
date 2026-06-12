"""Unit tests for CustomerSchemaMapper."""

from target_xero_v3.mappers.customer_schema_mapper import CustomerSchemaMapper


class TestCustomerSchemaMapper:
    def test_maps_new_customer_to_xero_payload(self, customer_record, empty_reference_data):
        payload = CustomerSchemaMapper(
            customer_record, "Customers", reference_data=empty_reference_data
        ).to_xero()

        assert payload["Name"] == "Fake Customer Co (Sample)"
        assert payload["ContactNumber"] == "FAKE-CUST-NUM-001"
        assert payload["EmailAddress"] == "fake.customer@example.invalid"
        assert payload["DefaultCurrency"] == "USD"
        assert "Website" not in payload
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

    def test_omits_contact_id_when_id_not_in_reference(self, empty_reference_data):
        record = {"id": "00000000-0000-4000-8000-000000009999", "companyName": "Fake Missing Co"}
        payload = CustomerSchemaMapper(
            record, "Customers", reference_data=empty_reference_data
        ).to_xero()

        assert "ContactID" not in payload
        assert payload["Name"] == "Fake Missing Co"

    def test_maps_full_name_for_individual_customer(self, empty_reference_data):
        record = {
            "fullName": "Fakey McSample",
            "firstName": "Fakey",
            "lastName": "McSample",
            "email": "fakey.mcsample@example.invalid",
        }
        payload = CustomerSchemaMapper(
            record, "Customers", reference_data=empty_reference_data
        ).to_xero()

        assert payload["Name"] == "Fakey McSample"
        assert payload["FirstName"] == "Fakey"
        assert payload["LastName"] == "McSample"

    def test_maps_name_from_first_and_last_when_company_and_full_name_absent(self, empty_reference_data):
        record = {
            "firstName": "Fakey",
            "lastName": "McSample",
            "email": "fakey.mcsample@example.invalid",
        }
        payload = CustomerSchemaMapper(
            record, "Customers", reference_data=empty_reference_data
        ).to_xero()

        assert payload["Name"] == "Fakey McSample"

    def test_maps_tax_code(self, empty_reference_data):
        record = {"companyName": "Fake Tax Customer", "taxCode": "OUTPUT"}
        payload = CustomerSchemaMapper(
            record, "Customers", reference_data=empty_reference_data
        ).to_xero()

        assert payload["AccountsReceivableTaxType"] == "OUTPUT"

    def test_maps_currency_from_currency_name(self, empty_reference_data):
        record = {
            "companyName": "Fake Currency Name Customer",
            "currencyName": "United States Dollar",
        }
        payload = CustomerSchemaMapper(
            record, "Customers", reference_data=empty_reference_data
        ).to_xero()

        assert payload["DefaultCurrency"] == "USD"

    def test_maps_currency_from_base_currency_when_currency_fields_absent(
        self, empty_reference_data
    ):
        record = {"companyName": "Fake Base Currency Customer"}
        payload = CustomerSchemaMapper(
            record, "Customers", reference_data=empty_reference_data
        ).to_xero()

        assert payload["DefaultCurrency"] == "USD"

    def test_maps_currency_from_currency_id(self, empty_reference_data):
        record = {
            "companyName": "Fake Currency Id Customer",
            "currencyId": "USD",
        }
        payload = CustomerSchemaMapper(
            record, "Customers", reference_data=empty_reference_data
        ).to_xero()

        assert payload["DefaultCurrency"] == "USD"

    def test_prefers_currency_over_currency_name(self, empty_reference_data):
        record = {
            "companyName": "Fake Currency Priority Customer",
            "currency": "EUR",
            "currencyName": "United States Dollar",
        }
        payload = CustomerSchemaMapper(
            record, "Customers", reference_data=empty_reference_data
        ).to_xero()

        assert payload["DefaultCurrency"] == "EUR"

    def test_omits_name_when_customer_name_missing(self, empty_reference_data):
        payload = CustomerSchemaMapper(
            {"email": "no.name@example.invalid"},
            "Customers",
            reference_data=empty_reference_data,
        ).to_xero()

        assert "Name" not in payload
        assert payload["EmailAddress"] == "no.name@example.invalid"

    def test_maps_is_active_to_contact_status(self, empty_reference_data):
        active = CustomerSchemaMapper(
            {"companyName": "Active Fake Co", "isActive": True},
            "Customers",
            reference_data=empty_reference_data,
        ).to_xero()
        archived = CustomerSchemaMapper(
            {"companyName": "Archived Fake Co", "isActive": False},
            "Customers",
            reference_data=empty_reference_data,
        ).to_xero()

        assert active["ContactStatus"] == "ACTIVE"
        assert archived["ContactStatus"] == "ARCHIVED"
