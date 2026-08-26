import importlib.util
import json
import ssl
import sys
from email.message import Message
from pathlib import Path

import pytest

VALIDATOR_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "validate_material_urls.py"
)
SPEC = importlib.util.spec_from_file_location("material_url_validator", VALIDATOR_PATH)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)


def fetch_result(url: str = "https://cloud.mail.ru/public/8T3Q/9BJxCpvZT"):
    return validator.FetchResult(
        url=url,
        status="broken",
        reason_code="empty_html",
        reason="empty",
        attempts=1,
        elapsed_ms=10,
        checked_at="2026-08-26T00:00:00+00:00",
        http_status=200,
    )


def response_headers(content_type: str) -> Message:
    headers = Message()
    headers["Content-Type"] = content_type
    return headers


def verify(result):
    return validator.verify_cloud_mail_public_file(
        result,
        timeout=1,
        max_bytes=512 * 1024,
        ssl_context=ssl.create_default_context(),
    )


def test_cloud_mail_public_pdf_is_verified(monkeypatch):
    dispatcher_url = "https://cloud.mail.ru/api/v2/dispatcher"
    broker_url = "https://cloclo60.cloud.mail.ru/public/token/g/no"
    final_url = "https://cloclo60.datacloudmail.ru/public/get/signed/tasks.pdf"
    dispatcher_body = json.dumps(
        {"body": {"weblink_get": [{"count": 1, "url": broker_url}]}}
    ).encode()
    calls = []

    def fake_fetch(url, *_args):
        calls.append(url)
        if url == dispatcher_url:
            return (
                200,
                dispatcher_url,
                response_headers("application/json"),
                dispatcher_body,
                [],
            )
        assert url == f"{broker_url}/8T3Q/9BJxCpvZT"
        return (
            200,
            final_url,
            response_headers("application/octet-stream"),
            b"%PDF-1.7\nverified",
            [],
        )

    monkeypatch.setattr(validator, "fetch_once", fake_fetch)

    verified = verify(fetch_result())

    assert verified is not None
    assert verified.status == "ok"
    assert verified.reason_code == "public_file_verified"
    assert verified.verification_url == final_url
    assert calls == [dispatcher_url, f"{broker_url}/8T3Q/9BJxCpvZT"]


def test_cloud_mail_rejects_untrusted_download_broker(monkeypatch):
    dispatcher_body = json.dumps(
        {"body": {"weblink_get": [{"url": "https://attacker.example/file"}]}}
    ).encode()

    def fake_fetch(_url, *_args):
        return (
            200,
            "https://cloud.mail.ru/api/v2/dispatcher",
            response_headers("application/json"),
            dispatcher_body,
            [],
        )

    monkeypatch.setattr(validator, "fetch_once", fake_fetch)

    assert verify(fetch_result()) is None


def test_cloud_mail_rejects_download_without_document_signature(monkeypatch):
    broker_url = "https://cloclo60.cloud.mail.ru/public/token/g/no"
    dispatcher_body = json.dumps(
        {"body": {"weblink_get": [{"url": broker_url}]}}
    ).encode()
    responses = iter(
        [
            (
                200,
                "https://cloud.mail.ru/api/v2/dispatcher",
                response_headers("application/json"),
                dispatcher_body,
                [],
            ),
            (
                200,
                "https://cloclo60.datacloudmail.ru/public/get/signed/file.txt",
                response_headers("text/plain"),
                b"not a document",
                [],
            ),
        ]
    )
    monkeypatch.setattr(validator, "fetch_once", lambda *_args: next(responses))

    assert verify(fetch_result()) is None


@pytest.mark.parametrize(
    "url",
    [
        "https://cloud.mail.ru/public/only-one-part",
        "https://cloud.mail.ru/not-public/8T3Q/9BJxCpvZT",
        "https://example.org/public/8T3Q/9BJxCpvZT",
    ],
)
def test_cloud_mail_rejects_malformed_share_url(monkeypatch, url):
    def unexpected_fetch(*_args):
        raise AssertionError("malformed URL must not trigger a network request")

    monkeypatch.setattr(validator, "fetch_once", unexpected_fetch)

    assert verify(fetch_result(url)) is None
