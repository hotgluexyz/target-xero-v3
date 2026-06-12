from unittest.mock import MagicMock, patch

import pytest
from hotglue_etl_exceptions import InvalidCredentialsError
from hotglue_singer_sdk.exceptions import RetriableAPIError

from target_xero_v3.client import REQUEST_TIMEOUT, XeroClient


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


class TestCredentialErrors:
    def test_raises_invalid_credentials_error_on_401(self, client):
        response = MagicMock()
        response.status_code = 401
        response.json.return_value = {"Detail": "TokenExpired"}
        response.text = '{"Detail":"TokenExpired"}'
        response.reason = "Unauthorized"

        with pytest.raises(InvalidCredentialsError, match="TokenExpired"):
            client._raise_for_credential_errors(response)

    def test_raises_invalid_credentials_error_on_403(self, client):
        response = MagicMock()
        response.status_code = 403
        response.json.return_value = {"Detail": "AuthenticationUnsuccessful"}
        response.text = '{"Detail":"AuthenticationUnsuccessful"}'
        response.reason = "Forbidden"

        with pytest.raises(InvalidCredentialsError, match="AuthenticationUnsuccessful"):
            client._raise_for_credential_errors(response)

    def test_ignores_non_credential_errors(self, client):
        response = MagicMock()
        response.status_code = 400

        client._raise_for_credential_errors(response)

    @patch.object(XeroClient, "refresh_credentials")
    @patch("target_xero_v3.client.requests.request")
    def test_make_request_raises_on_403(self, mock_request, _refresh, client):
        mock_request.return_value = MagicMock(
            status_code=403,
            reason="Forbidden",
            text='{"Detail":"AuthenticationUnsuccessful"}',
            json=MagicMock(return_value={"Detail": "AuthenticationUnsuccessful"}),
        )

        with pytest.raises(InvalidCredentialsError, match="AuthenticationUnsuccessful"):
            client._make_request("https://api.xero.com/api.xro/2.0/Contacts", "GET")

    @patch("target_xero_v3.client.requests.post")
    def test_generate_new_credentials_raises_on_oauth_failure(self, mock_post, client):
        mock_post.return_value = MagicMock(
            status_code=400,
            reason="Bad Request",
            text='{"error":"invalid_grant"}',
        )

        with pytest.raises(InvalidCredentialsError, match="Cannot refresh OAuth token"):
            client.generate_new_credentials()


class TestRequestTimeouts:
    @patch.object(XeroClient, "refresh_credentials")
    @patch("target_xero_v3.client.requests.request")
    def test_make_request_uses_timeout(self, mock_request, _refresh, client):
        mock_request.return_value = MagicMock(status_code=200, reason="OK", text="{}", headers={})

        client._make_request("https://api.xero.com/api.xro/2.0/Contacts", "GET")

        assert mock_request.call_args.kwargs["timeout"] == REQUEST_TIMEOUT

    @patch("target_xero_v3.client.requests.post")
    def test_token_refresh_uses_timeout(self, mock_post, client):
        mock_post.return_value = MagicMock(
            status_code=400,
            reason="Bad Request",
            text='{"error":"invalid_grant"}',
        )

        with pytest.raises(InvalidCredentialsError):
            client.generate_new_credentials()

        assert mock_post.call_args.kwargs["timeout"] == REQUEST_TIMEOUT


class TestRateLimits:
    def test_raises_retriable_error_on_429(self, client):
        response = MagicMock(
            status_code=429,
            headers={
                "Retry-After": "30",
                "X-Rate-Limit-Problem": "minute",
                "X-DayLimit-Remaining": "100",
            },
        )

        with pytest.raises(RetriableAPIError, match="problem=minute") as exc_info:
            client._raise_for_rate_limit(response)

        assert exc_info.value.response is response

    @patch.object(XeroClient, "refresh_credentials")
    @patch("target_xero_v3.client.requests.request")
    def test_make_request_raises_retriable_error_on_429(
        self, mock_request, _refresh, client
    ):
        mock_request.return_value = MagicMock(
            status_code=429,
            headers={
                "Retry-After": "30",
                "X-Rate-Limit-Problem": "day",
                "X-DayLimit-Remaining": "0",
            },
            reason="Too Many Requests",
            text="",
        )

        with pytest.raises(RetriableAPIError, match="problem=day"):
            client._make_request("https://api.xero.com/api.xro/2.0/Contacts", "GET")

        mock_request.assert_called_once()
