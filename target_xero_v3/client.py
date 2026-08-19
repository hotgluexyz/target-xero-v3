from requests.exceptions import SSLError
import json
from base64 import b64encode
from datetime import datetime, timedelta, timezone
from os.path import join

import jwt
import pytz
import requests
from hotglue_etl_exceptions import InvalidCredentialsError
from hotglue_singer_sdk.exceptions import RetriableAPIError
import backoff


BASE_URL = "https://api.xero.com/api.xro/2.0"
REQUEST_TIMEOUT = 300

CREDENTIAL_ERROR_STATUS_CODES = {401, 403}


def escape_xero_string(value: str) -> str:
    return str(value).replace('"', '\\"')


def update_config_file(config, config_path):
    with open(config_path, "w") as config_file:
        json.dump(config, config_file, indent=2)


def get_token_expiration_time(access_token):
    try:
        decoded_token = jwt.decode(access_token, options={"verify_signature": False})
        return datetime.fromtimestamp(decoded_token["exp"], tz=pytz.UTC)
    except Exception:
        return None


class XeroClient:
    def __init__(self, config, config_path, logger):
        self.config = config
        self.config_path = config_path
        self.logger = logger
        self.tenant_id = config["tenant_id"]
        self.access_token = config["access_token"]
        self.expiration_time = get_token_expiration_time(self.access_token)

    def generate_new_credentials(self):
        header_token = b64encode(
            (self.config["client_id"] + ":" + self.config["client_secret"]).encode(
                "utf-8"
            )
        )
        headers = {
            "Authorization": "Basic " + header_token.decode("utf-8"),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        post_body = {
            "grant_type": "refresh_token",
            "refresh_token": self.config["refresh_token"],
        }
        resp = requests.post(
            "https://identity.xero.com/connect/token",
            headers=headers,
            data=post_body,
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            raise InvalidCredentialsError(
                f"Cannot refresh OAuth token: {self._response_error_message(resp)}"
            )
        resp = resp.json()
        self.config["refresh_token"] = resp["refresh_token"]
        self.config["access_token"] = resp["access_token"]
        update_config_file(self.config, self.config_path)
        self.access_token = resp["access_token"]
        self.expiration_time = get_token_expiration_time(self.access_token)

    def refresh_credentials(self) -> None:
        if (
            self.expiration_time
            and self.expiration_time - timedelta(minutes=5) > datetime.now(timezone.utc)
        ):
            return
        self.generate_new_credentials()

    def filter(self, tap_stream_id, **params):
        resource = tap_stream_id.title().replace("_", "")
        url = join(BASE_URL, resource)
        response = self._make_request(url, "GET", params=params)
        if response.status_code >= 400:
            raise Exception(
                f"Error when making request: GET {url}: {response.status_code} "
                f"{self._response_error_message(response)}"
            )
        body = response.json()
        for key in (resource, f"{resource}s", tap_stream_id):
            if key in body:
                return body[key]
        return []

    def _build_where_clause(self, xero_field, value, filter_type):
        if filter_type == "guid":
            return f'{xero_field}==Guid("{value}")'
        escaped = escape_xero_string(value)
        return f'{xero_field}=="{escaped}"'

    def get_existing_entities_for_records(
        self,
        tap_stream_id,
        records,
        filter_mappings,
        id_field=None,
    ):
        entities = []
        seen = set()
        for mapping in filter_mappings:
            field_from = mapping["field_from"]
            xero_field = mapping["xero_field"]
            filter_type = mapping.get("filter_type", "string")
            values = {
                record.get(field_from)
                for record in records
                if record.get(field_from) is not None
            }
            for value in values:
                where = self._build_where_clause(xero_field, value, filter_type)
                for match in self.filter(tap_stream_id, where=where) or []:
                    entity_key = match.get(id_field) if id_field else None
                    dedupe_key = entity_key or id(match)
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)
                    entities.append(match)
        return entities

    def push(self, tap_stream_id, payload):
        resource = tap_stream_id.title().replace("_", "")
        url = join(BASE_URL, f"{resource}?summarizeErrors=false")
        return self._make_request(url, "POST", data=payload)

    def create_payments(self, payload):
        url = join(BASE_URL, "Payments?summarizeErrors=false")
        return self._make_request(url, "PUT", data=payload)

    def post_manual_journal(self, payload):
        url = join(BASE_URL, "ManualJournals?summarizeErrors=false")
        return self._make_request(url, "POST", data=payload)

    def create_account(self, payload):
        url = join(BASE_URL, "Accounts")
        return self._make_request(url, "PUT", data=payload)

    def update_account(self, account_id, payload):
        url = join(BASE_URL, f"Accounts/{account_id}")
        return self._make_request(url, "POST", data=payload)

    def create_tracking_option(self, tracking_category_id, payload):
        url = join(BASE_URL, f"TrackingCategories/{tracking_category_id}/Options")
        return self._make_request(url, "PUT", data=payload)

    def update_tracking_option(self, tracking_category_id, tracking_option_id, payload):
        url = join(
            BASE_URL,
            f"TrackingCategories/{tracking_category_id}/Options/{tracking_option_id}",
        )
        return self._make_request(url, "POST", data=payload)

    @backoff.on_exception(backoff.expo, (
        RetriableAPIError,
        SSLError,
        ConnectionError,
        TimeoutError
        ), max_tries=5)
    def _make_request(self, url, method, data=None, params=None, headers=None):
        self.refresh_credentials()
        request_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "Xero-tenant-id": self.tenant_id,
        }
        if headers:
            request_headers.update(headers)
        json_data = json.dumps(data) if data else None
        res = requests.request(
            method=method,
            url=url,
            params=params or {},
            headers=request_headers,
            data=json_data,
            timeout=REQUEST_TIMEOUT,
        )
        if res.status_code == 429:
            self._raise_for_rate_limit(res)
        if res.status_code >= 400:
            self.logger.error(
                f"Error when making request: {method} {url}: {res.status_code} {res.reason} {res.text}"
            )
        self._raise_for_credential_errors(res)
        return res

    def _raise_for_rate_limit(self, response):
        problem = response.headers.get("X-Rate-Limit-Problem", "unknown")
        self.logger.warning(
            "Xero rate limit exceeded "
            f"(problem={problem}, retry_after={response.headers.get('Retry-After')}s). "
            f"X-MinLimit-Remaining={response.headers.get('X-MinLimit-Remaining')} "
            f"X-DayLimit-Remaining={response.headers.get('X-DayLimit-Remaining')} "
            f"X-AppMinLimit-Remaining={response.headers.get('X-AppMinLimit-Remaining')}"
        )
        raise RetriableAPIError(self._rate_limit_error_message(response), response)

    def _rate_limit_error_message(self, response):
        problem = response.headers.get("X-Rate-Limit-Problem", "unknown")
        retry_after = response.headers.get("Retry-After")
        day_remaining = response.headers.get("X-DayLimit-Remaining")
        return (
            f"HTTP-error-code: 429, Error: Xero rate limit exceeded "
            f"(problem={problem}, retry_after={retry_after}s, "
            f"day_remaining={day_remaining})"
        )

    def _raise_for_credential_errors(self, response):
        if response.status_code not in CREDENTIAL_ERROR_STATUS_CODES:
            return
        raise InvalidCredentialsError(
            f"HTTP-error-code: {response.status_code}, "
            f"Error: {self._response_error_message(response)}"
        )

    def _validation_error_messages(self, response_json):
        messages = []
        for element in response_json.get("Elements") or []:
            messages.extend(self._validation_errors_from_item(element))
        for key in (
            "Accounts",
            "Contacts",
            "Items",
            "Invoices",
            "Payments",
            "Options",
            "TrackingCategories",
        ):
            for item in response_json.get(key) or []:
                messages.extend(self._validation_errors_from_item(item))
        return messages

    def _validation_errors_from_item(self, item):
        return [
            error["Message"]
            for error in item.get("ValidationErrors", [])
            if error.get("Message")
        ]

    def _response_error_message(self, response):
        try:
            response_json = response.json()
        except Exception:
            response_json = {}
        if validation_messages := self._validation_error_messages(response_json):
            return "; ".join(validation_messages)
        return (
            response_json.get("error_description")
            or response_json.get("error")
            or response_json.get("Detail")
            or response_json.get("Message")
            or response_json.get("Title")
            or response.text
            or response.reason
        )
