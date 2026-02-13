from pathlib import Path

from app.core.client import HttpFetchResult
from app.toto import service


SAMPLES_DIR = Path(__file__).resolve().parents[1] / "samples"


def _read_sample(name: str) -> str:
    return (SAMPLES_DIR / name).read_text(encoding="utf-8")


def test_run_trigger_next_prefers_incomplete_draw(monkeypatch):
    class _Draw:
        draw_number = 4042

    called = {}

    monkeypatch.setattr(service, "get_incomplete_draws", lambda db, limit, max_attempts: [_Draw()])
    monkeypatch.setattr(service, "get_latest_draw_number", lambda db: (_ for _ in ()).throw(AssertionError()))

    def _stub_run_with_lock(db, **kwargs):
        called.update(kwargs)
        return service.TotoRunResult(
            outcome="ok",
            requested_draw_number=kwargs["requested_draw_number"],
            validation_mode=kwargs["validation_mode"],
        )

    monkeypatch.setattr(service, "_run_with_lock", _stub_run_with_lock)

    result = service.run_trigger_next(db=None, validation_mode="current", dry_run=False)
    assert result.outcome == "ok"
    assert called["requested_draw_number"] == 4042
    assert called["replay"] is True


def test_run_trigger_next_uses_latest_plus_one_when_no_incomplete(monkeypatch):
    called = {}

    monkeypatch.setattr(service, "get_incomplete_draws", lambda db, limit, max_attempts: [])
    monkeypatch.setattr(service, "get_latest_draw_number", lambda db: 4043)

    def _stub_run_with_lock(db, **kwargs):
        called.update(kwargs)
        return service.TotoRunResult(
            outcome="ok",
            requested_draw_number=kwargs["requested_draw_number"],
            validation_mode=kwargs["validation_mode"],
        )

    monkeypatch.setattr(service, "_run_with_lock", _stub_run_with_lock)

    result = service.run_trigger_next(db=None, validation_mode="current", dry_run=False)
    assert result.outcome == "ok"
    assert called["requested_draw_number"] == 4044
    assert called["replay"] is False


def test_skipped_locked_writes_audit(monkeypatch):
    audits = []

    monkeypatch.setattr(service, "try_acquire_lock", lambda db: False)
    monkeypatch.setattr(
        service.core_client,
        "build_source_url",
        lambda base_url, draw_number: f"https://example.test/{draw_number}",
    )
    monkeypatch.setattr(service, "_write_audit_safely", lambda *args, **kwargs: audits.append(kwargs))

    result = service._run_with_lock(
        db=None,
        requested_draw_number=4044,
        validation_mode="current",
        dry_run=False,
        replay=False,
    )

    assert result.outcome == "skipped_locked"
    assert len(audits) == 1
    assert audits[0]["outcome"] == "skipped_locked"
    assert audits[0]["requested_draw_number"] == 4044


def test_dry_run_does_not_persist(monkeypatch):
    audits = []

    monkeypatch.setattr(
        service.core_client,
        "fetch_draw_html",
        lambda base_url, draw_number, timeout_seconds=10: HttpFetchResult(
            source_url="https://example.test",
            http_status=200,
            html=_read_sample("toto_4043_all.html"),
            error_message=None,
        ),
    )
    monkeypatch.setattr(service, "_write_audit_safely", lambda *args, **kwargs: audits.append(kwargs))
    monkeypatch.setattr(service, "_increment_attempt_if_existing", lambda *args, **kwargs: None)
    monkeypatch.setattr(service, "get_draw", lambda db, draw_number: None)
    monkeypatch.setattr(service, "upsert_draw", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))

    result = service._run_fetch(
        db=None,
        requested_draw_number=4043,
        validation_mode="current",
        dry_run=True,
        replay=False,
    )

    assert result.outcome == "dry_run"
    assert len(audits) == 1
    assert audits[0]["outcome"] == "dry_run"


def test_success_persists(monkeypatch):
    audits = []
    persisted = {"called": 0}

    monkeypatch.setattr(
        service.core_client,
        "fetch_draw_html",
        lambda base_url, draw_number, timeout_seconds=10: HttpFetchResult(
            source_url="https://example.test",
            http_status=200,
            html=_read_sample("toto_4043_all.html"),
            error_message=None,
        ),
    )
    monkeypatch.setattr(service, "_write_audit_safely", lambda *args, **kwargs: audits.append(kwargs))
    monkeypatch.setattr(service, "_increment_attempt_if_existing", lambda *args, **kwargs: None)
    monkeypatch.setattr(service, "get_draw", lambda db, draw_number: None)
    monkeypatch.setattr(service, "upsert_draw", lambda *args, **kwargs: persisted.__setitem__("called", persisted["called"] + 1))

    result = service._run_fetch(
        db=None,
        requested_draw_number=4043,
        validation_mode="current",
        dry_run=False,
        replay=False,
    )

    assert result.outcome == "success"
    assert persisted["called"] == 1
    assert len(audits) == 1
    assert audits[0]["outcome"] == "success"


def test_already_exists_short_circuits_persist(monkeypatch):
    audits = []

    class _Existing:
        is_complete = True

    monkeypatch.setattr(
        service.core_client,
        "fetch_draw_html",
        lambda base_url, draw_number, timeout_seconds=10: HttpFetchResult(
            source_url="https://example.test",
            http_status=200,
            html=_read_sample("toto_4043_all.html"),
            error_message=None,
        ),
    )
    monkeypatch.setattr(service, "_write_audit_safely", lambda *args, **kwargs: audits.append(kwargs))
    monkeypatch.setattr(service, "_increment_attempt_if_existing", lambda *args, **kwargs: None)
    monkeypatch.setattr(service, "get_draw", lambda db, draw_number: _Existing())
    monkeypatch.setattr(service, "upsert_draw", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))

    result = service._run_fetch(
        db=None,
        requested_draw_number=4043,
        validation_mode="current",
        dry_run=False,
        replay=False,
    )

    assert result.outcome == "already_exists"
    assert len(audits) == 1
    assert audits[0]["outcome"] == "already_exists"
