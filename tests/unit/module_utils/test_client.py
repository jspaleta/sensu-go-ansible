# -*- coding: utf-8 -*-
# Copyright: (c) 2019, XLAB Steampunk <steampunk@xlab.si>
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest

from ansible_collections.sensu.sensu_go.plugins.module_utils import (
    client, errors, http
)


class TestAuthHeader:
    def test_using_valid_token(self, mocker):
        request = mocker.patch.object(http, "request")
        request.return_value = http.Response(200, '{"access_token": "token"}')

        c = client.Client("http://example.com/", "user", "pass", None)

        assert dict(Authorization="Bearer token") == c.auth_header
        assert 1 == request.call_count
        assert ("GET", "http://example.com/auth") == request.call_args[0]
        assert "user" == request.call_args[1]["url_username"]
        assert "pass" == request.call_args[1]["url_password"]

    def test_cache_auth_headers_with_token(self, mocker):
        request = mocker.patch.object(http, "request")
        request.return_value = http.Response(200, '{"access_token": "token"}')

        c = client.Client("http://example.com/", "user", "pass", None)
        for i in range(5):
            c.auth_header

        assert 1 == request.call_count

    def test_login_failure_token_bad_status(self, mocker):
        request = mocker.patch.object(http, "request")
        request.return_value = http.Response(500, '{"access_token": "token"}')

        with pytest.raises(errors.SensuError, match="500"):
            client.Client(
                "http://example.com/", "user", "pass", None,
            ).auth_header

    def test_login_failure_token_bad_json(self, mocker):
        request = mocker.patch.object(http, "request")
        request.return_value = http.Response(200, "{ not a json }")

        with pytest.raises(errors.SensuError, match="JSON"):
            client.Client(
                "http://example.com/", "user", "pass", None,
            ).auth_header

    def test_login_failure_token_missing_token(self, mocker):
        request = mocker.patch.object(http, "request")
        request.return_value = http.Response(200, '{"access_bla": "token"}')

        with pytest.raises(errors.SensuError, match="token"):
            client.Client(
                "http://example.com/", "user", "pass", None,
            ).auth_header


class TestRequest:
    def test_request_payload_token(self, mocker):
        request = mocker.patch.object(http, "request")
        request.side_effect = (
            http.Response(200, '{"access_token": "token"}'),
            http.Response(200, "data"),
        )

        client.Client("http://example.com/", "user", "pass", None).request(
            "PUT", "/path", dict(some="payload"),
        )

        request.assert_called_with(
            "PUT", "http://example.com/path",
            payload=dict(some="payload"),
            headers=dict(Authorization="Bearer token"),
        )

    def test_request_payload_api_key(self, mocker):
        request = mocker.patch.object(http, "request")
        request.return_value = http.Response(200, "data")

        client.Client("http://example.com/", None, None, "key").request(
            "PUT", "/path", dict(some="payload"),
        )

        request.assert_called_once_with(
            "PUT", "http://example.com/path",
            payload=dict(some="payload"),
            headers=dict(Authorization="Key key"),
        )

    def test_request_no_payload_token(self, mocker):
        request = mocker.patch.object(http, "request")
        request.side_effect = (
            http.Response(200, '{"access_token": "token"}'),
            http.Response(200, "data"),
        )

        client.Client("http://example.com/", "user", "pass", None).request(
            "PUT", "/path",
        )

        request.assert_called_with(
            "PUT", "http://example.com/path", payload=None,
            headers=dict(Authorization="Bearer token"),
        )

    def test_request_no_payload_api_key(self, mocker):
        request = mocker.patch.object(http, "request")
        request.return_value = http.Response(200, "data")

        client.Client("http://example.com/", "u", "p", "key").request(
            "PUT", "/path",
        )

        request.assert_called_once_with(
            "PUT", "http://example.com/path", payload=None,
            headers=dict(Authorization="Key key"),
        )

    @pytest.mark.parametrize("status", [401, 403])
    def test_request_bad_credentials(self, status, mocker):
        request = mocker.patch.object(http, "request")
        request.return_value = http.Response(status, "data")

        with pytest.raises(errors.SensuError, match="credentials"):
            client.Client("http://example.com/", None, None, "key").request(
                "PUT", "/path", dict(some="payload"),
            )

        request.assert_called_once_with(
            "PUT", "http://example.com/path",
            payload=dict(some="payload"),
            headers=dict(Authorization="Key key"),
        )


class TestGet:
    def test_get(self, mocker):
        c = client.Client("http://example.com/", "user", "pass", None)
        c.request = mocker.Mock()

        c.get("/path")

        c.request.assert_called_with("GET", "/path")


class TestPut:
    def test_put(self, mocker):
        c = client.Client("http://example.com/", "user", "pass", None)
        c.request = mocker.Mock()

        c.put("/path", {})

        c.request.assert_called_with("PUT", "/path", {})


class TestDelete:
    def test_delete(self, mocker):
        c = client.Client("http://example.com/", "user", "pass", None)
        c.request = mocker.Mock()

        c.delete("/path")

        c.request.assert_called_with("DELETE", "/path")


class TestValidateAuthData:
    def test_valid_creds(self, mocker):
        request = mocker.patch.object(http, "request")
        request.return_value = http.Response(200, None)
        c = client.Client("http://example.com/", "user", "pass", None)

        result = c.validate_auth_data("check_user", "check_pass")

        assert result
        assert 1 == request.call_count
        assert ("GET", "http://example.com/auth/test") == request.call_args[0]
        assert "check_user" == request.call_args[1]["url_username"]
        assert "check_pass" == request.call_args[1]["url_password"]

    def test_invalid_creds(self, mocker):
        request = mocker.patch.object(http, "request")
        request.return_value = http.Response(401, None)
        c = client.Client("http://example.com/", "user", "pass", None)

        result = c.validate_auth_data("check_user", "check_pass")

        assert not result
        assert 1 == request.call_count
        assert ("GET", "http://example.com/auth/test") == request.call_args[0]
        assert "check_user" == request.call_args[1]["url_username"]
        assert "check_pass" == request.call_args[1]["url_password"]

    def test_broken_backend(self, mocker):
        request = mocker.patch.object(http, "request")
        request.return_value = http.Response(500, None)
        c = client.Client("http://example.com/", "user", "pass", None)

        with pytest.raises(errors.SensuError, match="500"):
            c.validate_auth_data("check_user", "check_pass")
