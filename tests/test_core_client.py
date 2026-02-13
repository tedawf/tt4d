from app.core import client


def test_build_source_url_encodes_sppl_query():
    url = client.build_source_url("https://example.test/path", 4043)
    assert url == "https://example.test/path?sppl=RHJhd051bWJlcj00MDQz"


def test_fetch_draw_html_builds_url_before_fetch(monkeypatch):
    calls = {}

    def _stub_fetch_html(url: str, timeout_seconds: int):
        calls["url"] = url
        calls["timeout_seconds"] = timeout_seconds
        return client.HttpFetchResult(
            source_url=url,
            http_status=200,
            html="<html/>",
            error_message=None,
        )

    monkeypatch.setattr(client, "fetch_html", _stub_fetch_html)

    result = client.fetch_draw_html(
        "https://example.test/path", draw_number=505, timeout_seconds=3
    )

    assert calls["url"] == "https://example.test/path?sppl=RHJhd051bWJlcj01MDU="
    assert calls["timeout_seconds"] == 3
    assert result.http_status == 200
