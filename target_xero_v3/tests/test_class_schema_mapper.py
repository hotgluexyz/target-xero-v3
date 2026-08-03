from target_xero_v3.mappers.class_schema_mapper import ClassSchemaMapper


class TestClassSchemaMapper:
    def test_maps_new_class_to_xero_payload(self, class_record, empty_reference_data):
        payload = ClassSchemaMapper(
            class_record, "Classes", reference_data=empty_reference_data
        ).to_xero()

        assert payload["Name"] == "Fake Class (Sample)"
        assert payload["Status"] == "ACTIVE"
        assert "TrackingOptionID" not in payload

    def test_maps_class_by_fullname(self, empty_reference_data):
        record = {"fullname": "Fake Class Fullname Only (Sample)", "isActive": False}
        payload = ClassSchemaMapper(
            record, "Classes", reference_data=empty_reference_data
        ).to_xero()

        assert payload["Name"] == "Fake Class Fullname Only (Sample)"
        assert payload["Status"] == "ARCHIVED"

    def test_maps_existing_class_by_name(self, class_record, class_reference_data):
        payload = ClassSchemaMapper(
            class_record, "Classes", reference_data=class_reference_data
        ).to_xero()

        assert payload["TrackingOptionID"] == "00000000-0000-4000-8000-0000000000cl1"

    def test_maps_existing_class_by_id(self, class_reference_data):
        record = {
            "id": "00000000-0000-4000-8000-0000000000cl1",
            "name": "Fake Renamed Class (Sample)",
        }
        payload = ClassSchemaMapper(
            record, "Classes", reference_data=class_reference_data
        ).to_xero()

        assert payload["TrackingOptionID"] == "00000000-0000-4000-8000-0000000000cl1"
        assert payload["Name"] == "Fake Renamed Class (Sample)"

    def test_omits_unmapped_fields(self, empty_reference_data):
        record = {
            "name": "Minimal Class (Sample)",
            "externalId": "ignored",
            "classNumber": "ignored",
            "description": "ignored",
            "parentId": "ignored",
            "subsidiaryId": "ignored",
        }
        payload = ClassSchemaMapper(
            record, "Classes", reference_data=empty_reference_data
        ).to_xero()

        assert payload == {"Name": "Minimal Class (Sample)"}
