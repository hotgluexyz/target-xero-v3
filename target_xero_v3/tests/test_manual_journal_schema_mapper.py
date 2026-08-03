import pytest
from hotglue_etl_exceptions import InvalidPayloadError

from target_xero_v3.mappers.manual_journal_line_schema_mapper import (
    ManualJournalLineSchemaMapper,
)
from target_xero_v3.mappers.manual_journal_schema_mapper import ManualJournalSchemaMapper


class TestManualJournalLineSchemaMapper:
    def test_maps_debit_line(self, empty_reference_data):
        payload = ManualJournalLineSchemaMapper(
            {
                "description": "Debit line",
                "accountNumber": "200",
                "debitAmount": 100.0,
            },
            "JournalEntryLineItems",
            reference_data=empty_reference_data,
        ).to_xero()

        assert payload == {
            "AccountCode": "200",
            "LineAmount": 100.0,
            "Description": "Debit line",
        }

    def test_maps_credit_line(self, empty_reference_data):
        payload = ManualJournalLineSchemaMapper(
            {
                "description": "Credit line",
                "accountNumber": "400",
                "creditAmount": 75.0,
                "taxCode": "NONE",
            },
            "JournalEntryLineItems",
            reference_data=empty_reference_data,
        ).to_xero()

        assert payload == {
            "AccountCode": "400",
            "LineAmount": -75.0,
            "Description": "Credit line",
            "TaxType": "NONE",
        }

    def test_maps_tracking(self, empty_reference_data):
        payload = ManualJournalLineSchemaMapper(
            {
                "accountNumber": "200",
                "debitAmount": 10.0,
                "className": "Fake Class (Sample)",
            },
            "JournalEntryLineItems",
            reference_data=empty_reference_data,
        ).to_xero()

        assert payload["Tracking"][0]["Name"] == "Classes"


class TestManualJournalSchemaMapper:
    def test_maps_new_journal(self, journal_entry_record, empty_reference_data):
        payload = ManualJournalSchemaMapper(
            journal_entry_record,
            "JournalEntries",
            reference_data=empty_reference_data,
        ).to_xero()

        assert payload["Narration"] == "Sample manual journal"
        assert payload["Date"] == "2026-07-01"
        assert payload["Status"] == "DRAFT"
        assert payload["JournalLines"][0]["LineAmount"] == 100.0
        assert payload["JournalLines"][1]["LineAmount"] == -100.0

    def test_maps_existing_journal_by_id(self, journal_reference_data):
        record = {
            "id": "00000000-0000-4000-8000-0000000000mj1",
            "description": "Updated journal",
            "isDraft": False,
            "lineItems": [
                {"accountNumber": "200", "debitAmount": 50.0},
                {"accountNumber": "400", "creditAmount": 50.0},
            ],
        }
        payload = ManualJournalSchemaMapper(
            record, "JournalEntries", reference_data=journal_reference_data
        ).to_xero()

        assert payload["ManualJournalID"] == "00000000-0000-4000-8000-0000000000mj1"
        assert payload["Status"] == "POSTED"

    def test_raises_when_account_not_found(self, empty_reference_data):
        record = {
            "description": "Bad journal",
            "lineItems": [{"accountName": "Missing Account", "debitAmount": 10.0}],
        }
        with pytest.raises(InvalidPayloadError, match="Missing Account"):
            ManualJournalSchemaMapper(
                record, "JournalEntries", reference_data=empty_reference_data
            ).to_xero()
