"""Xero target class."""

from typing import List, Optional, Union

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

    config_jsonschema = th.PropertiesList(
        th.Property("client_id", th.StringType, required=True),
        th.Property("client_secret", th.StringType, required=True),
        th.Property("refresh_token", th.StringType, required=True),
        th.Property("access_token", th.StringType, required=True),
        th.Property("tenant_id", th.StringType, required=True),
    ).to_dict()


if __name__ == "__main__":
    TargetXero.cli()
