#!/usr/bin/env python3
"""Audit every material URL from the seed catalog with real HTTP GET requests.

The validator deliberately deduplicates URLs and processes URLs from the same
host sequentially.  This makes a full audit reproducible without sending a
burst of requests to an organiser's website.
"""

from __future__ import annotations

import argparse
import codecs
import hashlib
import json
import os
import re
import ssl
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from email.message import Message
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

try:
    import certifi
except ImportError:  # pragma: no cover - the operating system CA store remains available
    certifi = None

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "data" / "seed" / "catalog.json"
DEFAULT_JSON_REPORT = ROOT / "research" / "material_link_audit.json"
DEFAULT_MARKDOWN_REPORT = ROOT / "research" / "material_link_audit.md"


def detect_ca_bundle() -> Path | None:
    """Find a real trust store without ever falling back to insecure TLS."""
    candidates = [
        Path(os.environ["SSL_CERT_FILE"]) if os.environ.get("SSL_CERT_FILE") else None,
        Path(certifi.where()) if certifi else None,
        Path("/etc/ssl/cert.pem"),
        Path("/etc/ssl/certs/ca-certificates.crt"),
        Path("/etc/pki/tls/certs/ca-bundle.crt"),
        Path("/opt/homebrew/etc/ca-certificates/cert.pem"),
    ]
    return next((path for path in candidates if path and path.is_file()), None)


DEFAULT_CA_BUNDLE = detect_ca_bundle()

USER_AGENT = (
    "Mozilla/5.0 (compatible; OlympiadCalendarMaterialValidator/1.0; "
    "+https://github.com/olympiad-calendar)"
)
TRANSIENT_HTTP_STATUSES = {408, 425, 429, 500, 502, 503, 504}
BLOCKED_HTTP_STATUSES = {401, 403, 407, 423, 425, 429, 451}
HTML_CONTENT_TYPES = {"application/xhtml+xml", "text/html"}
MATERIAL_PATTERNS = (
    r"\bархив\w*",
    r"\bзадани\w*",
    r"\bзадач\w*",
    r"\bрешени\w*",
    r"\bразбор\w*",
    r"\bматериал\w*",
    r"\bолимпиад\w*",
    r"\bтур\w*",
    r"\barchive\b",
    r"\btask(?:s)?\b",
    r"\bproblem(?:s)?\b",
    r"\bsolution(?:s)?\b",
    r"\bmaterial(?:s)?\b",
    r"\bcontest\b",
)
SOFT_ERROR_PATTERNS = (
    r"\b404\b.{0,80}\b(?:not found|не найден)",
    r"\b(?:not found|page not found)\b",
    r"\bстраниц[аы]\s+не\s+найден[аы]?\b",
    r"\bтакой\s+страницы\s+нет\b",
    r"\bссылка\s+(?:недействительна|устарела)\b",
    r"\bfile\s+not\s+found\b",
)
CHALLENGE_PATTERNS = (
    r"\bcloudflare\b",
    r"\bcaptcha\b",
    r"\baccess denied\b",
    r"\bдоступ запрещ[её]н\b",
    r"\bпровер(?:яем|ка)\s+(?:ваш|что вы)\b",
    r"\bverify you are human\b",
    r"\battention required\b",
)
JAVASCRIPT_PATTERNS = (
    r"you need to enable javascript",
    r"please enable javascript",
    r"javascript (?:is )?required",
    r"включите javascript",
    r"требуется javascript",
)


class PageInspector(HTMLParser):
    """Collect a small, script-free representation of an HTML response."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._title_depth = 0
        self.text_parts: list[str] = []
        self.title_parts: list[str] = []
        self.link_targets: list[str] = []
        self.script_count = 0
        self.has_app_mount = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.casefold()
        attributes = {key.casefold(): value or "" for key, value in attrs}
        if lowered in {"script", "style", "svg", "template"}:
            self._ignored_depth += 1
        if lowered == "script":
            self.script_count += 1
        if lowered == "title":
            self._title_depth += 1
        if lowered == "a" and attributes.get("href"):
            self.link_targets.append(attributes["href"])
        element_id = attributes.get("id", "").casefold()
        if element_id in {"app", "root", "__next", "svelte", "app-root"}:
            self.has_app_mount = True

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.casefold()
        if lowered in {"script", "style", "svg", "template"} and self._ignored_depth:
            self._ignored_depth -= 1
        if lowered == "title" and self._title_depth:
            self._title_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._title_depth:
            self.title_parts.append(data)
        if not self._ignored_depth:
            normalized = re.sub(r"\s+", " ", data).strip()
            if normalized:
                self.text_parts.append(normalized)

    @property
    def text(self) -> str:
        return " ".join(self.text_parts)

    @property
    def title(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.title_parts)).strip()


class TrackingRedirectHandler(HTTPRedirectHandler):
    def __init__(self) -> None:
        super().__init__()
        self.chain: list[dict[str, Any]] = []

    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Message,
        newurl: str,
    ) -> Request | None:
        self.chain.append({"status": code, "from": req.full_url, "to": newurl})
        return super().redirect_request(req, fp, code, msg, headers, newurl)


@dataclass
class FetchResult:
    url: str
    status: str
    reason_code: str
    reason: str
    attempts: int
    elapsed_ms: int
    checked_at: str
    http_status: int | None = None
    final_url: str | None = None
    redirects: list[dict[str, Any]] = field(default_factory=list)
    content_type: str | None = None
    content_length_header: int | None = None
    bytes_sampled: int = 0
    sample_sha256: str | None = None
    page_title: str | None = None
    visible_text_length: int | None = None
    link_count: int | None = None
    script_count: int | None = None
    content_match: str | None = None
    verification_url: str | None = None
    verification_http_status: int | None = None
    verification_evidence: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def header_content_type(headers: Message) -> str:
    return (headers.get_content_type() or "application/octet-stream").casefold()


def header_content_length(headers: Message) -> int | None:
    raw = headers.get("Content-Length")
    try:
        return int(raw) if raw is not None else None
    except ValueError:
        return None


def decode_body(body: bytes, headers: Message) -> str:
    declared = headers.get_content_charset()
    meta_match = re.search(
        br"charset\s*=\s*[\"']?\s*([A-Za-z0-9._-]+)", body[:8192], flags=re.IGNORECASE
    )
    meta_encoding = meta_match.group(1).decode("ascii") if meta_match else None
    if meta_encoding:
        try:
            codecs.lookup(meta_encoding)
        except LookupError:
            meta_encoding = None
    encodings = [
        encoding
        for encoding in [declared, meta_encoding, "utf-8", "cp1251", "koi8-r"]
        if encoding
    ]
    for encoding in dict.fromkeys(encodings):
        try:
            return body.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", errors="replace")


def classify_response(
    *,
    url: str,
    status_code: int,
    final_url: str,
    headers: Message,
    body: bytes,
    attempts: int,
    elapsed_ms: int,
    checked_at: str,
    redirects: list[dict[str, Any]],
) -> FetchResult:
    content_type = header_content_type(headers)
    content_length = header_content_length(headers)
    base = {
        "url": url,
        "attempts": attempts,
        "elapsed_ms": elapsed_ms,
        "checked_at": checked_at,
        "http_status": status_code,
        "final_url": final_url,
        "redirects": redirects,
        "content_type": content_type,
        "content_length_header": content_length,
        "bytes_sampled": len(body),
        "sample_sha256": hashlib.sha256(body).hexdigest() if body else None,
    }

    if status_code in BLOCKED_HTTP_STATUSES:
        return FetchResult(
            status="inconclusive",
            reason_code="http_access_blocked",
            reason=f"Сервер ответил HTTP {status_code}; автоматическая проверка заблокирована.",
            **base,
        )
    if status_code >= 400:
        return FetchResult(
            status="broken",
            reason_code="http_error",
            reason=f"Сервер ответил HTTP {status_code}.",
            **base,
        )
    if status_code in {204, 205} or not body.strip() or content_length == 0:
        return FetchResult(
            status="broken",
            reason_code="empty_response",
            reason="Успешный HTTP-ответ не содержит данных.",
            **base,
        )

    is_pdf = body.startswith(b"%PDF-")
    is_zip = body.startswith((b"PK\x03\x04", b"PK\x05\x06"))
    is_probably_html = content_type in HTML_CONTENT_TYPES or body.lstrip().lower().startswith(
        (b"<!doctype html", b"<html")
    )
    if not is_probably_html:
        if not (is_pdf or is_zip):
            return FetchResult(
                status="inconclusive",
                reason_code="unsupported_download",
                reason=(
                    "Ответ непустой, но не распознан как HTML, PDF или ZIP; "
                    "нужна ручная проверка формата."
                ),
                content_match="unknown",
                **base,
            )
        return FetchResult(
            status="ok",
            reason_code="download_nonempty",
            reason="Ссылка возвращает непустой PDF- или ZIP-файл с корректной сигнатурой.",
            content_match="binary_document",
            **base,
        )

    decoded = decode_body(body, headers)
    inspector = PageInspector()
    # HTMLParser accepts a document truncated at max_bytes; its partial output is
    # sufficient for empty/error/JavaScript-shell classification.
    inspector.feed(decoded)
    visible_text = normalize_space(inspector.text)
    combined = f"{inspector.title} {visible_text} {' '.join(inspector.link_targets)}".casefold()
    html_lower = decoded.casefold()
    extra = {
        "page_title": inspector.title or None,
        "visible_text_length": len(visible_text),
        "link_count": len(inspector.link_targets),
        "script_count": inspector.script_count,
    }

    if any(
        re.search(pattern, combined, flags=re.IGNORECASE | re.DOTALL)
        for pattern in CHALLENGE_PATTERNS
    ):
        return FetchResult(
            status="inconclusive",
            reason_code="browser_challenge",
            reason="Получена страница проверки доступа/CAPTCHA; нужен ручной браузер.",
            content_match="unknown",
            **extra,
            **base,
        )
    if any(
        re.search(pattern, combined, flags=re.IGNORECASE | re.DOTALL)
        for pattern in SOFT_ERROR_PATTERNS
    ):
        return FetchResult(
            status="broken",
            reason_code="soft_error_page",
            reason="HTTP 200 содержит сообщение о ненайденной странице или файле.",
            content_match="error_page",
            **extra,
            **base,
        )

    explicit_js_notice = any(
        re.search(pattern, f"{combined} {html_lower}", flags=re.IGNORECASE)
        for pattern in JAVASCRIPT_PATTERNS
    )
    sparse_app_shell = (
        inspector.script_count > 0
        and (inspector.has_app_mount or "webpack" in html_lower or "__next" in html_lower)
        and len(visible_text) < 180
        and len(inspector.link_targets) < 3
    )
    javascript_notice_blocks_content = (
        explicit_js_notice and len(visible_text) < 180 and len(inspector.link_targets) < 3
    )
    if javascript_notice_blocks_content or sparse_app_shell:
        return FetchResult(
            status="inconclusive",
            reason_code="javascript_required",
            reason="GET вернул оболочку JavaScript-приложения без проверяемого содержимого.",
            content_match="unknown",
            **extra,
            **base,
        )
    if len(visible_text) < 40 and len(inspector.link_targets) == 0:
        return FetchResult(
            status="broken",
            reason_code="empty_html",
            reason="HTML-страница практически не содержит текста или ссылок.",
            content_match="empty",
            **extra,
            **base,
        )

    material_match = any(
        re.search(pattern, combined, flags=re.IGNORECASE) for pattern in MATERIAL_PATTERNS
    )
    if not material_match:
        return FetchResult(
            status="inconclusive",
            reason_code="html_without_material_signals",
            reason=(
                "HTML-страница открывается, но в тексте и ссылках не найдены признаки "
                "олимпиадных заданий, решений или подготовки."
            ),
            content_match="generic_or_unclear",
            **extra,
            **base,
        )
    return FetchResult(
        status="ok",
        reason_code="html_nonempty",
        reason="HTML-страница открывается и содержит проверяемое содержимое.",
        content_match="likely_material",
        **extra,
        **base,
    )


def fetch_once(
    url: str,
    timeout: float,
    max_bytes: int,
    ssl_context: ssl.SSLContext,
) -> tuple[int, str, Message, bytes, list[dict[str, Any]]]:
    redirect_handler = TrackingRedirectHandler()
    opener = build_opener(redirect_handler, HTTPSHandler(context=ssl_context))
    request = Request(
        url,
        method="GET",
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/pdf,application/zip,*/*;q=0.8",
            "Accept-Language": "ru,en;q=0.7",
            "Cache-Control": "no-cache",
        },
    )
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read(max_bytes)
            return (
                response.status,
                response.geturl(),
                response.headers,
                body,
                redirect_handler.chain,
            )
    except HTTPError as error:
        body = error.read(max_bytes)
        return error.code, error.geturl(), error.headers, body, redirect_handler.chain


def nested_file_paths(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    result: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "file" and isinstance(item.get("url"), str):
            result.append(item["url"])
        result.extend(nested_file_paths(item.get("items")))
    return result


def verify_v_olymp_material_page(
    result: FetchResult,
    *,
    timeout: float,
    max_bytes: int,
    ssl_context: ssl.SSLContext,
) -> FetchResult | None:
    """Verify the official V-olymp JS page through its public first-party API."""
    parsed = urlsplit(result.url)
    if parsed.hostname != "v-olymp.ru" or parsed.path.rstrip("/") != "/prev-materials":
        return None
    slug = (parse_qs(parsed.query).get("slug") or [""])[0].strip()
    if not slug:
        return None

    api_base = "https://back.v-olymp.ru/wp-json/custom/v2"
    list_url = f"{api_base}/prev-materials/list"
    api_url = f"{api_base}/prev-materials?" + urlencode(
        {"slug": slug, "page": 1, "limit": 100}
    )
    try:
        list_status, _, list_headers, list_body, _ = fetch_once(
            list_url, timeout, max_bytes, ssl_context
        )
        available = (
            json.loads(decode_body(list_body, list_headers)) if list_status == 200 else None
        )
        status_code, _, headers, body, _ = fetch_once(
            api_url, timeout, max_bytes, ssl_context
        )
        payload = json.loads(decode_body(body, headers)) if status_code == 200 else None
    except (TimeoutError, ssl.SSLError, URLError, OSError, json.JSONDecodeError):
        return None
    listed_slugs = {
        item.get("slug") for item in available or [] if isinstance(item, dict)
    }
    if slug not in listed_slugs or not isinstance(payload, dict):
        return None
    total_count = payload.get("total_count")
    file_paths = nested_file_paths(payload.get("data"))
    if not isinstance(total_count, int) or total_count < 1 or not file_paths:
        return None

    preferred_file = next(
        (
            path
            for path in file_paths
            if path.casefold().endswith((".pdf", ".zip", ".docx", ".xlsx", ".pptx"))
        ),
        file_paths[0],
    )
    download_url = f"{api_base}/prev-materials/download?" + urlencode(
        {"file": preferred_file}
    )
    try:
        download_status, _, _, download_body, _ = fetch_once(
            download_url, timeout, max_bytes, ssl_context
        )
    except (TimeoutError, ssl.SSLError, URLError, OSError):
        return None
    valid_magic = download_body.startswith(
        (b"%PDF-", b"PK\x03\x04", b"PK\x05\x06")
    )
    if download_status != 200 or not valid_magic:
        return None

    return replace(
        result,
        status="ok",
        reason_code="official_api_materials",
        reason=(
            "JavaScript-страница открывается, а её официальный API возвращает "
            f"{total_count} элементов и {len(file_paths)} файлов; один файл "
            "дополнительно открыт и распознан как PDF/ZIP."
        ),
        content_match="verified_material_api",
        verification_url=api_url,
        verification_http_status=download_status,
        verification_evidence=(
            f"listed=true; total_count={total_count}; files={len(file_paths)}; "
            f"sample={preferred_file}; sample_magic=PDF/ZIP"
        ),
    )


def verify_cloud_mail_public_file(
    result: FetchResult,
    *,
    timeout: float,
    max_bytes: int,
    ssl_context: ssl.SSLContext,
) -> FetchResult | None:
    """Verify a Cloud Mail share by resolving and opening its public file."""
    parsed = urlsplit(result.url)
    if parsed.hostname != "cloud.mail.ru" or not parsed.path.startswith("/public/"):
        return None
    weblink = parsed.path.removeprefix("/public/").strip("/")
    if not weblink or len(weblink.split("/")) != 2:
        return None

    dispatcher_url = "https://cloud.mail.ru/api/v2/dispatcher"
    try:
        dispatcher_status, _, dispatcher_headers, dispatcher_body, _ = fetch_once(
            dispatcher_url, timeout, max_bytes, ssl_context
        )
        dispatcher = (
            json.loads(decode_body(dispatcher_body, dispatcher_headers))
            if dispatcher_status == 200
            else None
        )
        candidates = (dispatcher or {}).get("body", {}).get("weblink_get", [])
        download_prefix = next(
            (
                candidate.get("url")
                for candidate in candidates
                if isinstance(candidate, dict) and isinstance(candidate.get("url"), str)
            ),
            None,
        )
        prefix_host = urlsplit(download_prefix or "").hostname or ""
        if (
            not download_prefix
            or not download_prefix.startswith("https://")
            or not prefix_host.endswith(".cloud.mail.ru")
        ):
            return None
        download_url = f"{download_prefix.rstrip('/')}/{weblink}"
        download_status, download_final_url, _, download_body, _ = fetch_once(
            download_url, timeout, max_bytes, ssl_context
        )
    except (
        TimeoutError,
        ssl.SSLError,
        URLError,
        OSError,
        json.JSONDecodeError,
        AttributeError,
    ):
        return None

    valid_magic = download_body.startswith(
        (b"%PDF-", b"PK\x03\x04", b"PK\x05\x06")
    )
    if download_status != 200 or not valid_magic:
        return None

    return replace(
        result,
        status="ok",
        reason_code="public_file_verified",
        reason=(
            "Публичная страница Облака Mail открывается, а её файловый endpoint "
            "возвращает документ с корректной PDF/ZIP-сигнатурой."
        ),
        content_match="verified_public_file",
        verification_url=download_final_url,
        verification_http_status=download_status,
        verification_evidence=(
            f"dispatcher_status={dispatcher_status}; sample_magic=PDF/ZIP; "
            f"bytes_sampled={len(download_body)}"
        ),
    )


def audit_url(
    url: str,
    *,
    timeout: float,
    max_bytes: int,
    retries: int,
    retry_delay: float,
    ssl_context: ssl.SSLContext,
) -> FetchResult:
    started = time.monotonic()
    checked_at = datetime.now(UTC).isoformat(timespec="seconds")
    last_transport_error: Exception | None = None
    attempts = 0
    for attempt in range(1, retries + 2):
        attempts = attempt
        try:
            status_code, final_url, headers, body, redirects = fetch_once(
                url, timeout, max_bytes, ssl_context
            )
            if status_code in TRANSIENT_HTTP_STATUSES and attempt <= retries:
                time.sleep(retry_delay * attempt)
                continue
            elapsed_ms = round((time.monotonic() - started) * 1000)
            result = classify_response(
                url=url,
                status_code=status_code,
                final_url=final_url,
                headers=headers,
                body=body,
                attempts=attempts,
                elapsed_ms=elapsed_ms,
                checked_at=checked_at,
                redirects=redirects,
            )
            cloud_mail_verified = verify_cloud_mail_public_file(
                result,
                timeout=timeout,
                max_bytes=max_bytes,
                ssl_context=ssl_context,
            )
            if cloud_mail_verified:
                return cloud_mail_verified
            if result.reason_code == "javascript_required":
                api_verified = verify_v_olymp_material_page(
                    result,
                    timeout=timeout,
                    max_bytes=max_bytes,
                    ssl_context=ssl_context,
                )
                if api_verified:
                    return api_verified
            return result
        except (TimeoutError, ssl.SSLError, URLError, OSError) as error:
            last_transport_error = error
            if attempt <= retries:
                time.sleep(retry_delay * attempt)

    elapsed_ms = round((time.monotonic() - started) * 1000)
    error_name = type(last_transport_error).__name__ if last_transport_error else "unknown"
    error_text = normalize_space(str(last_transport_error or "unknown transport error"))[:300]
    return FetchResult(
        url=url,
        status="inconclusive",
        reason_code="transport_error",
        reason=f"После {attempts} попыток GET не завершился: {error_name}: {error_text}",
        attempts=attempts,
        elapsed_ms=elapsed_ms,
        checked_at=checked_at,
    )


def load_materials(catalog_path: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    raw = catalog_path.read_bytes()
    catalog = json.loads(raw)
    records = catalog.get("records") if isinstance(catalog, dict) else catalog
    if not isinstance(records, list):
        raise TypeError("Catalog must be a list or an object containing a records list")

    occurrences_by_url: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        for material in record.get("materials") or []:
            url = (material.get("url") or "").strip()
            if not url:
                continue
            occurrences_by_url[url].append(
                {
                    "olympiad_slug": record.get("slug"),
                    "olympiad_name": record.get("name"),
                    "profile": record.get("profile"),
                    "material_title": material.get("title"),
                    "material_type": material.get("material_type"),
                    "material_year": material.get("year"),
                    "is_official": material.get("is_official"),
                }
            )
    metadata = {
        "catalog_sha256": hashlib.sha256(raw).hexdigest(),
        "catalog_academic_year": (
            catalog.get("academic_year") if isinstance(catalog, dict) else None
        ),
        "catalog_records": len(records),
        "material_occurrences": sum(len(items) for items in occurrences_by_url.values()),
        "unique_urls": len(occurrences_by_url),
        "olympiads_with_materials": len(
            {item["olympiad_slug"] for items in occurrences_by_url.values() for item in items}
        ),
    }
    return metadata, dict(occurrences_by_url)


def audit_host_group(
    urls: list[str],
    *,
    timeout: float,
    max_bytes: int,
    retries: int,
    retry_delay: float,
    host_delay: float,
    ssl_context: ssl.SSLContext,
) -> list[FetchResult]:
    results: list[FetchResult] = []
    for index, url in enumerate(urls):
        if index:
            time.sleep(host_delay)
        results.append(
            audit_url(
                url,
                timeout=timeout,
                max_bytes=max_bytes,
                retries=retries,
                retry_delay=retry_delay,
                ssl_context=ssl_context,
            )
        )
    return results


def make_report(
    *,
    catalog_path: Path,
    metadata: dict[str, Any],
    occurrences_by_url: dict[str, list[dict[str, Any]]],
    fetch_results: list[FetchResult],
    args: argparse.Namespace,
    started_at: datetime,
) -> dict[str, Any]:
    result_rows: list[dict[str, Any]] = []
    status_occurrences: Counter[str] = Counter()
    for result in sorted(fetch_results, key=lambda item: item.url):
        row = result.as_dict()
        occurrences = occurrences_by_url[result.url]
        row["occurrence_count"] = len(occurrences)
        row["olympiad_count"] = len({item["olympiad_slug"] for item in occurrences})
        row["occurrences"] = occurrences
        result_rows.append(row)
        status_occurrences[result.status] += len(occurrences)

    status_unique = Counter(row["status"] for row in result_rows)
    reason_unique = Counter(row["reason_code"] for row in result_rows)
    content_match_unique = Counter(row["content_match"] for row in result_rows)
    http_status_unique = Counter(
        str(row["http_status"]) if row["http_status"] is not None else "none"
        for row in result_rows
    )
    finished_at = datetime.now(UTC)
    return {
        "schema_version": 1,
        "generated_at": finished_at.isoformat(timespec="seconds"),
        "catalog_path": (
            str(catalog_path.resolve().relative_to(ROOT))
            if catalog_path.resolve().is_relative_to(ROOT)
            else catalog_path.name
        ),
        **metadata,
        "method": {
            "http_method": "GET",
            "user_agent": USER_AGENT,
            "timeout_seconds": args.timeout,
            "retries_after_first_attempt": args.retries,
            "max_bytes_per_response": args.max_bytes,
            "max_parallel_hosts": args.workers,
            "per_host_parallelism": 1,
            "delay_between_same_host_requests_seconds": args.host_delay,
            "ca_bundle": (
                f"trusted-store:{args.ca_bundle.name}"
                if args.ca_bundle
                else "operating-system-default"
            ),
            "js_only_pages": "inconclusive",
            "js_page_adapters": ["v-olymp.ru via first-party materials API"],
        },
        "summary": {
            "status_unique_urls": dict(sorted(status_unique.items())),
            "status_material_occurrences": dict(sorted(status_occurrences.items())),
            "reason_unique_urls": dict(sorted(reason_unique.items())),
            "content_match_unique_urls": {
                str(key): value for key, value in sorted(content_match_unique.items(), key=str)
            },
            "http_status_unique_urls": dict(sorted(http_status_unique.items())),
            "duplicate_occurrences_saved": (
                metadata["material_occurrences"] - metadata["unique_urls"]
            ),
            "elapsed_seconds": round((finished_at - started_at).total_seconds(), 2),
        },
        "results": result_rows,
    }


def markdown_escape(value: Any) -> str:
    return normalize_space(str(value or "—")).replace("|", "\\|")


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    status = summary["status_unique_urls"]
    occurrence_status = summary["status_material_occurrences"]
    results = report["results"]
    inconclusive_or_broken = [row for row in results if row["status"] != "ok"]
    generic = [row for row in results if row["content_match"] == "generic_or_unclear"]
    shared = [row for row in results if row["olympiad_count"] >= 3]

    lines = [
        "# Аудит ссылок на материалы олимпиад",
        "",
        f"Проверено: **{report['generated_at']}**. Каталог: `{report['catalog_path']}`.",
        f"SHA-256 каталога: `{report['catalog_sha256']}`.",
        "",
        (
            "Проверка выполняет реальные GET-запросы с переходом по редиректам. URL "
            "проверяются один раз вне зависимости от числа использований; запросы к "
            "одному домену идут последовательно. Читается только начало ответа, "
            "достаточное для определения файла, пустой страницы, сообщения об ошибке "
            "или JavaScript-оболочки."
        ),
        "",
        "## Итог",
        "",
        f"- Записей материалов: **{report['material_occurrences']}**.",
        f"- Уникальных URL: **{report['unique_urls']}**.",
        (
            f"- Олимпиад с материалами: **{report['olympiads_with_materials']}** из "
            f"{report['catalog_records']}."
        ),
        (
            f"- Работают: **{status.get('ok', 0)}** URL / "
            f"**{occurrence_status.get('ok', 0)}** записей материалов."
        ),
        (
            f"- Сломаны: **{status.get('broken', 0)}** URL / "
            f"**{occurrence_status.get('broken', 0)}** записей материалов."
        ),
        (
            f"- Неоднозначны: **{status.get('inconclusive', 0)}** URL / "
            f"**{occurrence_status.get('inconclusive', 0)}** записей материалов."
        ),
        (
            f"- За счёт дедупликации не отправлено повторных GET: "
            f"**{summary['duplicate_occurrences_saved']}**."
        ),
        f"- Время аудита: **{summary['elapsed_seconds']} с**.",
        "",
        (
            "`inconclusive` не означает, что ссылка сломана: сервер мог потребовать "
            "JavaScript, CAPTCHA или заблокировать автоматический клиент. Такие URL "
            "нельзя считать подтверждёнными без проверки в браузере."
        ),
        "",
        "## Требуют внимания",
        "",
    ]
    if inconclusive_or_broken:
        lines.extend(
            [
                "| Статус | HTTP | Использований | URL | Причина |",
                "|---|---:|---:|---|---|",
            ]
        )
        for row in inconclusive_or_broken:
            lines.append(
                f"| {row['status']} | {row['http_status'] or '—'} | "
                f"{row['occurrence_count']} | {markdown_escape(row['url'])} | "
                f"{markdown_escape(row['reason'])} |"
            )
    else:
        lines.append("Сломанных или неоднозначных ссылок не обнаружено.")

    lines.extend(["", "## Содержимое требует смысловой проверки", ""])
    if generic:
        lines.extend(
            [
                (
                    "Эти страницы технически открываются, но в полученном HTML не найден "
                    "явный признак архива, задания, решения или олимпиады."
                ),
                "",
                "| Использований | URL | Заголовок страницы |",
                "|---:|---|---|",
            ]
        )
        for row in generic:
            lines.append(
                f"| {row['occurrence_count']} | {markdown_escape(row['url'])} | "
                f"{markdown_escape(row['page_title'])} |"
            )
    else:
        lines.append("Все подтверждённые HTML-страницы имеют признаки материалов или олимпиады.")

    lines.extend(["", "## Ссылки, общие для нескольких олимпиад", ""])
    if shared:
        lines.extend(
            [
                (
                    "Высокое число использований не является сетевой ошибкой, но помогает "
                    "найти слишком общие архивы, которые стоит заменить профильными "
                    "страницами."
                ),
                "",
                "| Олимпиад | Записей | URL |",
                "|---:|---:|---|",
            ]
        )
        for row in shared:
            lines.append(
                f"| {row['olympiad_count']} | {row['occurrence_count']} | "
                f"{markdown_escape(row['url'])} |"
            )
    else:
        lines.append("Нет URL, общих для трёх и более олимпиад.")

    lines.extend(
        [
            "",
            "## Все уникальные URL",
            "",
            "| Статус | HTTP | Тип | Использований | URL | Результат |",
            "|---|---:|---|---:|---|---|",
        ]
    )
    for row in results:
        lines.append(
            f"| {row['status']} | {row['http_status'] or '—'} | "
            f"{markdown_escape(row['content_type'])} | {row['occurrence_count']} | "
            f"{markdown_escape(row['url'])} | {markdown_escape(row['reason_code'])} |"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_REPORT)
    parser.add_argument("--workers", type=int, default=4, help="parallel host groups")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--max-bytes", type=int, default=512 * 1024)
    parser.add_argument("--host-delay", type=float, default=0.35)
    parser.add_argument("--retry-delay", type=float, default=0.75)
    parser.add_argument(
        "--ca-bundle",
        type=Path,
        default=DEFAULT_CA_BUNDLE,
        help="trusted CA bundle (defaults to certifi when installed)",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.workers < 1:
        raise ValueError("--workers must be at least 1")
    if args.timeout <= 0 or args.max_bytes < 1024:
        raise ValueError("--timeout must be positive and --max-bytes at least 1024")
    if args.retries < 0 or args.host_delay < 0 or args.retry_delay < 0:
        raise ValueError("retry and delay values cannot be negative")
    if args.ca_bundle and not args.ca_bundle.is_file():
        raise ValueError(f"CA bundle does not exist: {args.ca_bundle}")


def main() -> int:
    args = parse_args()
    validate_args(args)
    started_at = datetime.now(UTC)
    metadata, occurrences_by_url = load_materials(args.catalog)
    ssl_context = ssl.create_default_context(
        cafile=str(args.ca_bundle) if args.ca_bundle else None
    )

    urls_by_host: dict[str, list[str]] = defaultdict(list)
    for url in occurrences_by_url:
        host = (urlsplit(url).hostname or "").casefold()
        urls_by_host[host].append(url)

    fetch_results: list[FetchResult] = []
    worker_count = min(args.workers, max(1, len(urls_by_host)))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(
                audit_host_group,
                sorted(urls),
                timeout=args.timeout,
                max_bytes=args.max_bytes,
                retries=args.retries,
                retry_delay=args.retry_delay,
                host_delay=args.host_delay,
                ssl_context=ssl_context,
            ): host
            for host, urls in sorted(urls_by_host.items())
        }
        for future in as_completed(futures):
            fetch_results.extend(future.result())

    report = make_report(
        catalog_path=args.catalog,
        metadata=metadata,
        occurrences_by_url=occurrences_by_url,
        fetch_results=fetch_results,
        args=args,
        started_at=started_at,
    )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(report), encoding="utf-8")

    status = report["summary"]["status_unique_urls"]
    print(
        f"Audited {report['unique_urls']} unique URLs: "
        f"ok={status.get('ok', 0)}, broken={status.get('broken', 0)}, "
        f"inconclusive={status.get('inconclusive', 0)}"
    )
    print(f"JSON: {args.json_output}")
    print(f"Markdown: {args.markdown_output}")
    # A JavaScript shell, CAPTCHA or transport failure is not a confirmed
    # material link. Treat both broken and inconclusive results as a failed
    # publication check; the detailed report still distinguishes the causes.
    return 1 if status.get("broken", 0) or status.get("inconclusive", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
