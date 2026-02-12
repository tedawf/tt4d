from pathlib import Path

from app.dddd.types import FetchResult
from app.dddd import service


SAMPLES_DIR = Path(__file__).resolve().parents[1] / "samples"


def _read_sample(name: str) -> str:
    return (SAMPLES_DIR / name).read_text(encoding="utf-8")


def test_no_new_draw_does_not_write_audit(monkeypatch):
    audits = []

    monkeypatch.setattr(
        service,
        "fetch_dddd_html",
        lambda draw_number: FetchResult(
            source_url="https://example.test",
            http_status=200,
            html=_read_sample("4d_506.html"),
            error_message=None,
        ),
    )
    monkeypatch.setattr(service, "_write_audit_safely", lambda *args, **kwargs: audits.append(kwargs))
    monkeypatch.setattr(service, "draw_exists", lambda db, draw_number: False)
    monkeypatch.setattr(service, "insert_draw_and_prizes", lambda db, parsed: None)

    result = service._run_fetch(db=None, requested_draw_number=507, strict=True, replay=False)

    assert result.outcome == "no_new_draw"
    assert result.actual_draw_number == 506
    assert audits == []


def test_sequence_mismatch_writes_failure_audit(monkeypatch):
    audits = []

    monkeypatch.setattr(
        service,
        "fetch_dddd_html",
        lambda draw_number: FetchResult(
            source_url="https://example.test",
            http_status=200,
            html=_read_sample("4d_506.html"),
            error_message=None,
        ),
    )
    monkeypatch.setattr(service, "_write_audit_safely", lambda *args, **kwargs: audits.append(kwargs))

    result = service._run_fetch(db=None, requested_draw_number=505, strict=True, replay=False)

    assert result.outcome == "sequence_mismatch"
    assert result.actual_draw_number == 506
    assert len(audits) == 1
    assert audits[0]["outcome"] == "sequence_mismatch"


def test_strict_validation_failure_writes_failure_audit(monkeypatch):
    audits = []

    monkeypatch.setattr(
        service,
        "fetch_dddd_html",
        lambda draw_number: FetchResult(
            source_url="https://example.test",
            http_status=200,
            html=_read_sample("4d_505.html"),
            error_message=None,
        ),
    )
    monkeypatch.setattr(service, "_write_audit_safely", lambda *args, **kwargs: audits.append(kwargs))

    result = service._run_fetch(db=None, requested_draw_number=505, strict=True, replay=False)

    assert result.outcome == "validation_error"
    assert len(audits) == 1
    assert audits[0]["outcome"] == "validation_error"
