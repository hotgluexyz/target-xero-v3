"""Xero target class."""

from singer_sdk import typing as th
from singer_sdk.sinks import BatchSink
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
        self._current_stream = None

    config_jsonschema = th.PropertiesList(
        th.Property("client_id", th.StringType, required=True),
        th.Property("client_secret", th.StringType, required=True),
        th.Property("refresh_token", th.StringType, required=True),
        th.Property("access_token", th.StringType, required=True),
        th.Property("tenant_id", th.StringType, required=True),
    ).to_dict()

    def _drain_other_batch_sinks(self, current_stream: str) -> None:
        """Post open customer/vendor batches before another stream is written."""
        for name, sink in list(self._sinks_active.items()):
            if name == current_stream or not isinstance(sink, BatchSink):
                continue
            self.drain_one(sink)

    def _process_record_message(self, message_dict: dict) -> None:
        stream_name = message_dict["stream"]
        if stream_name != self._current_stream:
            self._drain_other_batch_sinks(stream_name)
            self._current_stream = stream_name
        TargetHotglue._process_record_message(self, message_dict)


if __name__ == "__main__":
    TargetXero.cli()
