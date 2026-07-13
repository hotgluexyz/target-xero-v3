from unittest.mock import MagicMock

import pytest
from hotglue_etl_exceptions import InvalidPayloadError

from target_xero_v3.sinks.manual_journal_sink import ManualJournalSink


@pytest.fixture
def manual_journal_sink():
    sink = ManualJournalSink.__new__(ManualJournalSink)
    sink.name = ManualJournalSink.name
    sink.stream_name = "JournalEntries"
    sink.endpoint = ManualJournalSink.endpoint
    sink.record_type = ManualJournalSink.record_type
    sink.id_field = ManualJournalSink.id_field
    sink.max_size = ManualJournalSink.max_size
    sink.xero_client = MagicMock()
    sink.logger = MagicMock()
    sink._target = MagicMock(
        tenant_config={"xero": {"dimension_mappings": {"class": "Classes"}}},
        reference_data={"Currencies": [], "Organisation": []},
    )
    return sink


def _batch_record(
    sink,
    *,
    operation="create",
    external_id="FAKE-JOURNAL-EXT-001",
    journal_id=None,
):
    mapped = {
        "Narration": "Sample manual journal",
        "Date": "2026-07-01",
        "Status": "DRAFT",
        "JournalLines": [
            {"AccountCode": "200", "LineAmount": 100.0},
            {"AccountCode": "400", "LineAmount": -100.0},
        ],
        "externalId": external_id,
    }
    if journal_id:
        mapped[sink.id_field] = journal_id
    return {
        "bId": "0",
        "operation": operation,
        sink.record_type: mapped,
    }


class TestManualJournalSink:
    def test_get_batch_reference_data(self, manual_journal_sink, journal_entry_record):
        manual_journal_sink.xero_client.get_existing_entities_for_records.return_value = []
        manual_journal_sink.xero_client.filter.return_value = [
            {"AccountID": "a1", "Code": "200"},
            {"TrackingCategoryID": "tc1", "Name": "Classes", "Options": []},
        ]

        reference_data = manual_journal_sink.get_batch_reference_data([journal_entry_record])

        assert reference_data["Accounts"]
        assert reference_data["TrackingCategories"]
        manual_journal_sink.xero_client.get_existing_entities_for_records.assert_called_once()

    def test_process_batch_record_create(self, manual_journal_sink, journal_entry_record):
        reference_data = {
            "JournalEntries": [],
            "Accounts": [
                {"AccountID": "00000000-0000-4000-8000-0000000000a1", "Code": "200"},
                {"AccountID": "00000000-0000-4000-8000-0000000000a2", "Code": "400"},
            ],
            "tenant_config": manual_journal_sink._target.tenant_config,
            "TrackingCategories": [
                {
                    "TrackingCategoryID": "00000000-0000-4000-8000-0000000000tc1",
                    "Name": "Classes",
                    "Options": [
                        {
                            "TrackingOptionID": "00000000-0000-4000-8000-0000000000cl1",
                            "Name": "Fake Class (Sample)",
                        }
                    ],
                }
            ],
        }
        batch_record = manual_journal_sink.process_batch_record(
            journal_entry_record, 0, reference_data
        )

        assert batch_record["operation"] == "create"
        assert batch_record["ManualJournal"]["Status"] == "DRAFT"
        assert len(batch_record["ManualJournal"]["JournalLines"]) == 2

    def test_process_batch_record_update(self, manual_journal_sink):
        record = {
            "id": "00000000-0000-4000-8000-0000000000mj1",
            "description": "Updated journal",
            "lineItems": [
                {"accountNumber": "200", "debitAmount": 50.0},
                {"accountNumber": "400", "creditAmount": 50.0},
            ],
        }
        reference_data = {
            "JournalEntries": [
                {
                    "ManualJournalID": "00000000-0000-4000-8000-0000000000mj1",
                    "Status": "DRAFT",
                }
            ],
            "Accounts": [
                {"AccountID": "00000000-0000-4000-8000-0000000000a1", "Code": "200"},
                {"AccountID": "00000000-0000-4000-8000-0000000000a2", "Code": "400"},
            ],
            "tenant_config": manual_journal_sink._target.tenant_config,
        }
        batch_record = manual_journal_sink.process_batch_record(record, 0, reference_data)

        assert batch_record["operation"] == "update"
        assert batch_record["ManualJournal"]["ManualJournalID"] == (
            "00000000-0000-4000-8000-0000000000mj1"
        )

    def test_make_batch_request_uses_post(self, manual_journal_sink):
        records = [_batch_record(manual_journal_sink)]
        manual_journal_sink.xero_client.post_manual_journal.return_value = MagicMock()

        manual_journal_sink.make_batch_request(records)

        payload = manual_journal_sink.xero_client.post_manual_journal.call_args[0][0]
        assert "externalId" not in payload["ManualJournals"][0]

    def test_handle_batch_response_success(self, manual_journal_sink):
        records = [_batch_record(manual_journal_sink)]
        response = MagicMock()
        response.json.return_value = {
            "ManualJournals": [
                {
                    "ManualJournalID": "00000000-0000-4000-8000-0000000000mj2",
                    "HasValidationErrors": False,
                }
            ]
        }
        result = manual_journal_sink.handle_batch_response(response, records)

        assert result["state_updates"][0] == {
            "id": "00000000-0000-4000-8000-0000000000mj2",
            "externalId": "FAKE-JOURNAL-EXT-001",
            "success": True,
        }

    def test_handle_batch_response_validation_error(self, manual_journal_sink):
        records = [_batch_record(manual_journal_sink)]
        response = MagicMock()
        response.json.return_value = {
            "ManualJournals": [
                {
                    "ManualJournalID": "00000000-0000-0000-0000-000000000000",
                    "HasValidationErrors": True,
                    "ValidationErrors": [
                        {
                            "Message": (
                                "The total debits (100.00) must equal total credits (50.00)"
                            )
                        }
                    ],
                }
            ]
        }
        result = manual_journal_sink.handle_batch_response(response, records)

        assert result["state_updates"][0]["success"] is False
        assert "total debits" in result["state_updates"][0]["error"]

    def test_raises_when_account_mapping_fails(self, manual_journal_sink):
        record = {
            "externalId": "FAKE-JOURNAL-EXT-002",
            "description": "Bad journal",
            "lineItems": [{"accountName": "Missing Account", "debitAmount": 10.0}],
        }
        reference_data = {
            "JournalEntries": [],
            "Accounts": [],
            "tenant_config": manual_journal_sink._target.tenant_config,
        }
        with pytest.raises(InvalidPayloadError, match="Missing Account"):
            manual_journal_sink.process_batch_record(record, 0, reference_data)
