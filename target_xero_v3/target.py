"""Xero target class."""

from typing import List

from singer_sdk import typing as th
from target_hotglue.target import TargetHotglue


from target_xero_v3.sinks import (
    CustomerSink,
    TaxRatesSink,
    ItemsSink,
    InvoicesSink,
    BillsSink,
    JournalEntriesSink,
    CreditNotesSink,
    QuotesSink,
    VendorsSink,
    BankTransactionSink,
    BillPaymentsSink,
    InvoicePaymentsSink
)


class TargetXero(TargetHotglue):
    """Sample target for Xero."""

    # Written only after Customers/Vendors batches have been flushed to Xero.
    _TRANSACTION_STREAMS = frozenset(
        {
            "invoices",
            "bills",
            "creditnotes",
            "quotes",
            "banktransactions",
            "billpayments",
            "invoicepayments",
        }
    )

    SINK_TYPES = [
        CustomerSink,
        VendorsSink,
        TaxRatesSink,
        ItemsSink,
        InvoicesSink,
        BillsSink,
        JournalEntriesSink,
        CreditNotesSink,
        QuotesSink,
        BankTransactionSink,
        BillPaymentsSink,
        InvoicePaymentsSink
    ]
    name = "target-xero-v3"

    def __init__(
        self,
        config=None,
        parse_env_config: bool = False,
        validate_config: bool = True,
        state: str = None,
    ) -> None:
        self.config_file = config[0]
        super().__init__(
            config=config,
            parse_env_config=parse_env_config,
            validate_config=validate_config,
        )
        # Process one stream at once.
        self._max_parallelism = 1
        self.contacts_cache: List[dict] = []
        self._deferred_transactions: List[dict] = []

    config_jsonschema = th.PropertiesList(
        th.Property("client_id", th.StringType, required=True),
        th.Property("client_secret", th.StringType, required=True),
        th.Property("refresh_token", th.StringType, required=True),
        th.Property("access_token", th.StringType, required=True),
        th.Property("tenant_id", th.StringType, required=True),
    ).to_dict()

    def _process_record_message(self, message_dict: dict) -> None:
        if message_dict["stream"].lower() in self._TRANSACTION_STREAMS:
            self._deferred_transactions.append(message_dict)
            return
        TargetHotglue._process_record_message(self, message_dict)

    def _process_endofpipe(self) -> None:
        # Flush customers/vendors (and other reference streams) before transactions.
        self.drain_all(is_endofpipe=False)
        deferred = self._deferred_transactions
        self._deferred_transactions = []
        for message_dict in deferred:
            TargetHotglue._process_record_message(self, message_dict)
        self.drain_all(is_endofpipe=True)


if __name__ == "__main__":
    TargetXero.cli()
