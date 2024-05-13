"""Xero target class."""

import copy
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
    
    def _process_record_message(self, message_dict: dict) -> None:
        """Process a RECORD message."""
        self._assert_line_requires(message_dict, requires={"stream", "record"})

        stream_name = message_dict["stream"]
        for stream_map in self.mapper.stream_maps[stream_name]:
            # new_schema = helpers._float_to_decimal(new_schema)
            raw_record = copy.copy(message_dict["record"])
            transformed_record = stream_map.transform(raw_record)
            if transformed_record is None:
                # Record was filtered out by the map transform
                continue

            sink = self.get_sink(stream_map.stream_alias, record=transformed_record)
            context = sink._get_context(transformed_record)
            if sink.include_sdc_metadata_properties:
                sink._add_sdc_metadata_to_record(
                    transformed_record, message_dict, context
                )
            else:
                sink._remove_sdc_metadata_from_record(transformed_record)

            sink._validate_and_parse(transformed_record)

            sink.tally_record_read()
            transformed_record = sink.preprocess_record(transformed_record, context)
            sink.process_record(transformed_record, context)
            sink._after_process_record(context)

            if sink.is_full or stream_name=="Customers":
                self.logger.info(
                    f"Target sink for '{sink.stream_name}' is full. Draining..."
                )
                self.drain_one(sink)

            self._latest_state = sink.latest_state    

if __name__ == "__main__":
    TargetXero.cli()
