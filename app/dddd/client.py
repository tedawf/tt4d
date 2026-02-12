import base64

import requests

from app.dddd.types import FetchResult

BASE_URL = "https://www.singaporepools.com.sg/en/product/pages/4d_results.aspx"
REQUEST_TIMEOUT_SECONDS = 10


def build_source_url(draw_number: int) -> str:
    draw_str = f"DrawNumber={draw_number}"
    encoded_draw = base64.b64encode(draw_str.encode()).decode()
    return f"{BASE_URL}?sppl={encoded_draw}"


def fetch_dddd_html(draw_number: int) -> FetchResult:
    source_url = build_source_url(draw_number)

    try:
        response = requests.get(source_url, timeout=REQUEST_TIMEOUT_SECONDS)
        return FetchResult(
            source_url=response.url,
            http_status=response.status_code,
            html=response.text,
            error_message=None,
        )
    except requests.exceptions.RequestException as exc:
        return FetchResult(
            source_url=source_url,
            http_status=None,
            html=None,
            error_message=str(exc),
        )
