import html
import ipaddress
import os
import re
import secrets
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from rest_framework.exceptions import ValidationError


SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
PROHIBITED_HEADER_NAMES = {"host", "content-length", "connection", "x-forwarded-for", "x-real-ip"}


def escape_markdown_to_html(markdown_text):
    import markdown

    safe_markdown = html.escape(markdown_text or "")
    return markdown.markdown(
        safe_markdown,
        extensions=["extra", "tables"],
        output_format="html5",
    )


def sanitize_filename(filename, default="file"):
    name = Path(filename or default).name
    stem = SAFE_FILENAME_RE.sub("_", Path(name).stem).strip("._-") or default
    suffix = SAFE_FILENAME_RE.sub("", Path(name).suffix)
    return f"{stem[:80]}{suffix[:20]}"


def secure_random_token(length=48):
    # token_urlsafe returns ~1.3 chars per byte
    return secrets.token_urlsafe(length)[: max(length, 32)]


def get_allowed_outbound_hosts():
    raw_hosts = getattr(settings, "OUTBOUND_HTTP_ALLOWED_HOSTS", []) or []
    hosts = {str(h).strip().lower() for h in raw_hosts if str(h).strip()}
    for url in [
        getattr(settings, "ENRICHMENT_API_URL", ""),
        getattr(settings, "WEBHOOK_RECEIVER_URL", ""),
        getattr(settings, "MAIL_SERVICE_URL", ""),
    ]:
        parsed = urlparse(url)
        if parsed.hostname:
            hosts.add(parsed.hostname.lower())
    return hosts


def is_disallowed_private_host(hostname, allowed_hosts=None):
    hostname = (hostname or "").strip().lower()
    allowed_hosts = {h.lower() for h in (allowed_hosts or set())}
    if hostname in allowed_hosts:
        return False
    if not hostname:
        return True
    if hostname == "localhost" or hostname.endswith('.local'):
        return True
    try:
        ip = ipaddress.ip_address(hostname)
        return not ip.is_global
    except ValueError:
        return False


def validate_outbound_url(url, extra_allowed_hosts=None):
    parsed = urlparse(url or "")
    if parsed.scheme not in {"http", "https"}:
        raise ValidationError("Only http and https URLs are allowed.")
    if not parsed.hostname:
        raise ValidationError("URL must include a hostname.")

    allowed_hosts = get_allowed_outbound_hosts()
    if extra_allowed_hosts:
        allowed_hosts |= {h.lower() for h in extra_allowed_hosts}

    hostname = parsed.hostname.lower()
    if is_disallowed_private_host(hostname, allowed_hosts=allowed_hosts):
        raise ValidationError("Outbound requests to private or localhost addresses are not allowed.")

    if allowed_hosts and not (
        hostname in allowed_hosts or any(hostname.endswith(f".{host}") for host in allowed_hosts)
    ):
        raise ValidationError("Outbound requests to this host are not allowed.")
    return parsed


def sanitize_outbound_headers(headers):
    cleaned = {}
    if not isinstance(headers, dict):
        return cleaned
    for key, value in headers.items():
        if str(key).lower() in PROHIBITED_HEADER_NAMES:
            continue
        cleaned[str(key)] = str(value)
    return cleaned
