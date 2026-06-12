import json
from base64 import b64encode
from datetime import datetime, timedelta, timezone
from os.path import join

import jwt
import pytz
import requests
from hotglue_etl_exceptions import InvalidCredentialsError
from hotglue_singer_sdk.exceptions import RetriableAPIError


BASE_URL = "https://api.xero.com/api.xro/2.0"
REQUEST_TIMEOUT = 300

CREDENTIAL_ERROR_STATUS_CODES = {401, 403}


def update_config_file(config, config_path):
    with open(config_path, "w") as config_file:
        json.dump(config, config_file, indent=2)


def get_token_expiration_time(access_token):
    try:
        decoded_token = jwt.decode(access_token, options={"verify_signature": False})
        return datetime.fromtimestamp(decoded_token["exp"], tz=pytz.UTC)
    except Exception as e:
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
            return []
        body = response.json()
        for key in (resource, f"{resource}s", tap_stream_id):
            if key in body:
                return body[key]
        return []

    def push(self, tap_stream_id, payload):
        resource = tap_stream_id.title().replace("_", "")
        url = join(BASE_URL, f"{resource}?summarizeErrors=false")
        return self._make_request(url, "POST", data=payload)

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

    def _response_error_message(self, response):
        try:
            response_json = response.json()
        except Exception:
            response_json = {}
        return (
            response_json.get("error_description")
            or response_json.get("error")
            or response_json.get("Detail")
            or response_json.get("Message")
            or response_json.get("Title")
            or response.text
            or response.reason
        )
