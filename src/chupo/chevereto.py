from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx


def build_upload_url(base: str) -> str:
    # Chevereto V4: POST {base}/api/1/upload
    return f"{base.rstrip('/')}/api/1/upload"


def _absolutize_against_site(site_base: str, ref: str) -> str:
    ref = ref.strip()
    if not ref or ref.startswith(("http://", "https://")):
        return ref
    return urljoin(site_base.rstrip("/") + "/", ref)


def upload_file(
    client: httpx.Client,
    base_url: str,
    api_key: str,
    path: Path,
    response_format: str,
) -> httpx.Response:
    url = build_upload_url(base_url)
    headers = {"X-API-Key": api_key}
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    data = {"format": response_format}
    content = path.read_bytes()
    files = {"source": (path.name, content, mime)}
    follow_redirects = response_format != "redirect"
    return client.post(
        url,
        headers=headers,
        data=data,
        files=files,
        follow_redirects=follow_redirects,
    )


def parse_upload_result(
    response: httpx.Response,
    response_format: str,
    *,
    site_base: str | None = None,
) -> tuple[bool, str, dict[str, Any] | None]:
    if response_format == "redirect":
        if 300 <= response.status_code < 400:
            loc = response.headers.get("location", "")
            if loc:
                if site_base:
                    loc = _absolutize_against_site(site_base, loc)
                return True, "redirect", {"url": loc, "url_viewer": loc}
            return False, f"HTTP {response.status_code} (no Location)", None
        if response.status_code == 200:
            return True, "OK", None
        return False, f"HTTP {response.status_code}", None

    if response_format == "txt":
        if response.status_code == 200:
            text = response.text.strip()
            if text:
                return True, text, {"url": text, "url_viewer": text}
            return False, "empty response", None
        return False, response.text or f"HTTP {response.status_code}", None

    try:
        payload = response.json()
    except Exception:
        body = (response.text or "")[:500]
        return False, body or f"HTTP {response.status_code}", None

    status = payload.get("status_code")
    status_txt = str(payload.get("status_txt", ""))
    if response.status_code == 200 and status == 200:
        image = payload.get("image")
        if isinstance(image, dict):
            return True, status_txt or "OK", image
        return True, status_txt or "OK", None

    err = status_txt or str(payload.get("error", payload))[:500]
    return False, err, None
