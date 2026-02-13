import base64
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class HttpFetchResult:
    source_url: str
    http_status: Optional[int]
    html: Optional[str] = None
    error_message: Optional[str] = None


def build_source_url(base_url: str, draw_number: int) -> str:
    draw_param = f"DrawNumber={draw_number}"
    encoded_draw = base64.b64encode(draw_param.encode("utf-8")).decode("ascii")
    return f"{base_url}?sppl={encoded_draw}"


def fetch_html(url: str, timeout_seconds: int = 10) -> HttpFetchResult:
    try:
        response = requests.get(url, timeout=timeout_seconds)
        return HttpFetchResult(
            source_url=response.url,
            http_status=response.status_code,
            html=response.text,
            error_message=None,
        )
    except requests.exceptions.RequestException as exc:
        return HttpFetchResult(
            source_url=url,
            http_status=None,
            html=None,
            error_message=str(exc),
        )


def fetch_draw_html(
    base_url: str, draw_number: int, timeout_seconds: int = 10
) -> HttpFetchResult:
    source_url = build_source_url(base_url, draw_number)
    return fetch_html(source_url, timeout_seconds=timeout_seconds)
