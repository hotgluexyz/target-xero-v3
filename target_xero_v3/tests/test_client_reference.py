from unittest.mock import MagicMock

import pytest

from target_xero_v3.client import XeroClient


@pytest.fixture
def client():
    return XeroClient(
        {
            "client_id": "fake-client-id",
            "client_secret": "fake-client-secret",
            "refresh_token": "fake-refresh-token",
            "access_token": "fake-access-token",
            "tenant_id": "fake-tenant-id",
        },
        "/tmp/fake-config.json",
        MagicMock(),
    )


class TestGetExistingEntitiesForRecords:
    def test_deduplicates_entities_by_id(self, client):
        client.filter = MagicMock(
            side_effect=[
                [{"InvoiceID": "00000000-0000-4000-8000-000000000001", "InvoiceNumber": "A"}],
                [{"InvoiceID": "00000000-0000-4000-8000-000000000001", "InvoiceNumber": "A"}],
            ]
        )
        records = [
            {"id": "00000000-0000-4000-8000-000000000001"},
            {"invoiceNumber": "A"},
        ]
        filter_mappings = [
            {"field_from": "id", "xero_field": "InvoiceID", "filter_type": "guid"},
            {
                "field_from": "invoiceNumber",
                "xero_field": "InvoiceNumber",
                "filter_type": "string",
            },
        ]

        entities = client.get_existing_entities_for_records(
            "Invoices",
            records,
            filter_mappings,
            id_field="InvoiceID",
        )

        assert entities == [
            {
                "InvoiceID": "00000000-0000-4000-8000-000000000001",
                "InvoiceNumber": "A",
            }
        ]
        assert client.filter.call_count == 2

    def test_builds_guid_and_string_filters(self, client):
        client.filter = MagicMock(return_value=[])
        records = [
            {"vendorId": "00000000-0000-4000-8000-000000000001"},
            {"vendorName": 'Vendor "One"'},
        ]
        filter_mappings = [
            {"field_from": "vendorId", "xero_field": "ContactID", "filter_type": "guid"},
            {"field_from": "vendorName", "xero_field": "Name", "filter_type": "string"},
        ]

        client.get_existing_entities_for_records("Contacts", records, filter_mappings)

        assert client.filter.call_args_list[0].kwargs["where"] == (
            'ContactID==Guid("00000000-0000-4000-8000-000000000001")'
        )
        assert client.filter.call_args_list[1].kwargs["where"] == (
            'Name=="Vendor \\"One\\""'
        )

    def test_builds_guid_where_clause(self, client):
        assert client._build_where_clause("ItemID", "00000000-0000-4000-8000-000000000099", "guid") == (
            'ItemID==Guid("00000000-0000-4000-8000-000000000099")'
        )

    def test_filter_raises_on_query_error(self, client):
        client._make_request = MagicMock(
            return_value=MagicMock(
                status_code=400,
                reason="Bad Request",
                text='{"Type":"QueryParseException","Message": "bad query"}',
                json=MagicMock(
                    return_value={
                        "Type": "QueryParseException",
                        "Message": "bad query",
                    }
                ),
            )
        )

        with pytest.raises(Exception, match="bad query"):
            client.filter("Items", where='ItemID==Guid("00000000-0000-4000-8000-000000000099")')

    def test_skips_invalid_guid_values(self, client):
        client.filter = MagicMock(return_value=[])

        client.get_existing_entities_for_records(
            "Items",
            [{"itemId": "not-a-guid"}],
            [{"field_from": "itemId", "xero_field": "ItemID", "filter_type": "guid"}],
        )

        client.filter.assert_not_called()
