from pathlib import Path

from app.core.client import HttpFetchResult
from app.dddd import service


SAMPLES_DIR = Path(__file__).resolve().parents[1] / "samples"


def _read_sample(name: str) -> str:
    return (SAMPLES_DIR / name).read_text(encoding="utf-8")


def test_no_new_draw_writes_audit(monkeypatch):
    audits = []

    monkeypatch.setattr(
        service.core_client,
        "fetch_draw_html",
        lambda base_url, draw_number, timeout_seconds=10: HttpFetchResult(
            source_url="https://example.test",
            http_status=200,
            html=_read_sample("4d_506.html"),
            error_message=None,
        ),
    )
    monkeypatch.setattr(service, "_write_audit_safely", lambda *args, **kwargs: audits.append(kwargs))
    monkeypatch.setattr(service, "draw_exists", lambda db, draw_number: False)
    monkeypatch.setattr(service, "insert_draw_and_prizes", lambda db, parsed: None)

    result = service._run_fetch(
        db=None,
        requested_draw_number=507,
        validation_mode="current",
        dry_run=False,
        replay=False,
    )

    assert result.outcome == "no_new_draw"
    assert result.actual_draw_number == 506
    assert len(audits) == 1
    assert audits[0]["outcome"] == "no_new_draw"


def test_sequence_mismatch_writes_failure_audit(monkeypatch):
    audits = []

    monkeypatch.setattr(
        service.core_client,
        "fetch_draw_html",
        lambda base_url, draw_number, timeout_seconds=10: HttpFetchResult(
            source_url="https://example.test",
            http_status=200,
            html=_read_sample("4d_506.html"),
            error_message=None,
        ),
    )
    monkeypatch.setattr(service, "_write_audit_safely", lambda *args, **kwargs: audits.append(kwargs))

    result = service._run_fetch(
        db=None,
        requested_draw_number=505,
        validation_mode="current",
        dry_run=False,
        replay=False,
    )

    assert result.outcome == "sequence_mismatch"
    assert result.actual_draw_number == 506
    assert len(audits) == 1
    assert audits[0]["outcome"] == "sequence_mismatch"


def test_current_validation_failure_writes_failure_audit(monkeypatch):
    audits = []

    monkeypatch.setattr(
        service.core_client,
        "fetch_draw_html",
        lambda base_url, draw_number, timeout_seconds=10: HttpFetchResult(
            source_url="https://example.test",
            http_status=200,
            html=_read_sample("4d_505.html"),
            error_message=None,
        ),
    )
    monkeypatch.setattr(service, "_write_audit_safely", lambda *args, **kwargs: audits.append(kwargs))

    result = service._run_fetch(
        db=None,
        requested_draw_number=505,
        validation_mode="current",
        dry_run=False,
        replay=False,
    )

    assert result.outcome == "validation_error"
    assert len(audits) == 1
    assert audits[0]["outcome"] == "validation_error"


def test_dry_run_does_not_persist(monkeypatch):
    audits = []

    monkeypatch.setattr(
        service.core_client,
        "fetch_draw_html",
        lambda base_url, draw_number, timeout_seconds=10: HttpFetchResult(
            source_url="https://example.test",
            http_status=200,
            html=_read_sample("4d_506.html"),
            error_message=None,
        ),
    )
    monkeypatch.setattr(service, "_write_audit_safely", lambda *args, **kwargs: audits.append(kwargs))
    monkeypatch.setattr(service, "insert_draw_and_prizes", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))
    monkeypatch.setattr(service, "replace_draw_and_prizes", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))
    monkeypatch.setattr(service, "draw_exists", lambda db, draw_number: False)

    result = service._run_fetch(
        db=None,
        requested_draw_number=506,
        validation_mode="current",
        dry_run=True,
        replay=False,
    )

    assert result.outcome == "dry_run"
    assert len(audits) == 1
    assert audits[0]["outcome"] == "dry_run"


def test_success_persists_with_insert_when_not_replay(monkeypatch):
    audits = []
    persisted = {"called": 0}

    monkeypatch.setattr(
        service.core_client,
        "fetch_draw_html",
        lambda base_url, draw_number, timeout_seconds=10: HttpFetchResult(
            source_url="https://example.test",
            http_status=200,
            html=_read_sample("4d_506.html"),
            error_message=None,
        ),
    )
    monkeypatch.setattr(service, "_write_audit_safely", lambda *args, **kwargs: audits.append(kwargs))
    monkeypatch.setattr(service, "insert_draw_and_prizes", lambda *args, **kwargs: persisted.__setitem__("called", persisted["called"] + 1))
    monkeypatch.setattr(service, "replace_draw_and_prizes", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))
    monkeypatch.setattr(service, "draw_exists", lambda db, draw_number: False)

    result = service._run_fetch(
        db=None,
        requested_draw_number=506,
        validation_mode="current",
        dry_run=False,
        replay=False,
    )

    assert result.outcome == "success"
    assert persisted["called"] == 1
    assert len(audits) == 1
    assert audits[0]["outcome"] == "success"


def test_success_persists_with_replace_when_replay(monkeypatch):
    audits = []
    replaced = {"called": 0}

    monkeypatch.setattr(
        service.core_client,
        "fetch_draw_html",
        lambda base_url, draw_number, timeout_seconds=10: HttpFetchResult(
            source_url="https://example.test",
            http_status=200,
            html=_read_sample("4d_506.html"),
            error_message=None,
        ),
    )
    monkeypatch.setattr(service, "_write_audit_safely", lambda *args, **kwargs: audits.append(kwargs))
    monkeypatch.setattr(service, "insert_draw_and_prizes", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))
    monkeypatch.setattr(service, "replace_draw_and_prizes", lambda *args, **kwargs: replaced.__setitem__("called", replaced["called"] + 1))

    result = service._run_fetch(
        db=None,
        requested_draw_number=506,
        validation_mode="current",
        dry_run=False,
        replay=True,
    )

    assert result.outcome == "success"
    assert replaced["called"] == 1
    assert len(audits) == 1
    assert audits[0]["outcome"] == "success"


def test_skipped_locked_returns_without_fetch(monkeypatch):
    audits = []

    monkeypatch.setattr(service, "try_acquire_lock", lambda db: False)
    monkeypatch.setattr(
        service.core_client,
        "build_source_url",
        lambda base_url, draw_number: f"https://example.test/{draw_number}",
    )
    monkeypatch.setattr(service, "_write_audit_safely", lambda *args, **kwargs: audits.append(kwargs))
    monkeypatch.setattr(
        service.core_client,
        "fetch_draw_html",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()),
    )

    result = service._run_with_lock(
        db=None,
        requested_draw_number=507,
        validation_mode="current",
        dry_run=False,
        replay=False,
    )

    assert result.outcome == "skipped_locked"
    assert len(audits) == 1
    assert audits[0]["outcome"] == "skipped_locked"
