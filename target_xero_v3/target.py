"""Xero target class."""

from hotglue_singer_sdk import typing as th
from hotglue_singer_sdk.helpers.capabilities import AlertingLevel
from hotglue_singer_sdk.target_sdk.target import TargetHotglue

from target_xero_v3.client import XeroClient
from target_xero_v3.sinks.customer_sink import CustomerSink
from target_xero_v3.sinks.vendor_sink import VendorSink


class TargetXero(TargetHotglue):
    """Xero target class."""

    name = "target-xero-v3"
    alerting_level = AlertingLevel.ERROR
    MAX_PARALLELISM = 1

    config_jsonschema = th.PropertiesList(
        th.Property("client_id", th.StringType, required=True),
        th.Property("client_secret", th.StringType, required=True),
        th.Property("refresh_token", th.StringType, required=True),
        th.Property("access_token", th.StringType, required=True),
        th.Property("tenant_id", th.StringType, required=True),
    ).to_dict()

    SINK_TYPES = [
        CustomerSink,
        VendorSink,
    ]

    def __init__(
        self,
        config=None,
        parse_env_config: bool = False,
        validate_config: bool = True,
        state: str = None,
    ) -> None:
        super().__init__(
            config=config,
            parse_env_config=parse_env_config,
            validate_config=validate_config,
            state=state,
        )
        self.config_file = self._config_file_path
        self.xero_client = self.get_xero_client()
        self.reference_data = self.get_reference_data()

    def get_xero_client(self):
        return XeroClient(dict(self.config), self.config_file, self.logger)

    def get_reference_data(self):
        self.logger.info("Reading data from API...")
        return {
            "Currencies": self.xero_client.filter("Currencies") or [],
            "Organisation": self.xero_client.filter("Organisation") or [],
        }


if __name__ == "__main__":
    TargetXero.cli()
