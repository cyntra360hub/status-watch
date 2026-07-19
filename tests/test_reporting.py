import json

from status_watch.config import Config
from status_watch.reporting import ReportingError, report_run
from status_watch.watcher import ProviderOutcome, WatchResult


def _result(*, has_error: bool = False, new: int = 0) -> WatchResult:
    if has_error:
        outcome = ProviderOutcome(provider="github", ok=False, error="boom")
    else:
        from status_watch.providers import Incident

        incidents = tuple(
            Incident(provider="github", incident_id=str(i), title="x", status=None, url=None)
            for i in range(new)
        )
        outcome = ProviderOutcome(
            provider="github", ok=True, error=None, new_incidents=incidents, total_incidents=new
        )
    return WatchResult(providers=(outcome,))


class _FakePoster:
    def __init__(self):
        self.calls = []

    def __call__(self, url, body, headers):
        self.calls.append((url, body, headers))
        return {"id": "evt_123"}


def test_report_disabled_returns_none():
    poster = _FakePoster()
    config = Config(report_enabled=False)
    assert report_run(config, _result(), poster=poster) is None
    assert poster.calls == []


def test_report_enabled_sends_started_then_completed():
    poster = _FakePoster()
    config = Config(report_enabled=True, agent_key_id="ak_test", agent_secret="s3cret")
    response = report_run(config, _result(), poster=poster)
    assert response == {"id": "evt_123"}
    kinds = [json.loads(c[1])["event_type"] for c in poster.calls]
    assert kinds == ["task_started", "task_completed"]


def test_outcome_success_when_new_incidents_found_with_external_ref():
    # Finding new incidents is a successful detection, not a failure --
    # the finding goes in external_ref, not outcome.
    poster = _FakePoster()
    config = Config(report_enabled=True, agent_key_id="ak_test", agent_secret="s3cret")
    report_run(config, _result(new=2), poster=poster)
    second_body = json.loads(poster.calls[1][1])
    assert second_body["outcome"] == "success"
    assert second_body["external_ref"] == "swept 1 provider(s) -- new incidents: github(2)"


def test_outcome_success_without_external_ref_when_nothing_new():
    poster = _FakePoster()
    config = Config(report_enabled=True, agent_key_id="ak_test", agent_secret="s3cret")
    report_run(config, _result(new=0), poster=poster)
    second_body = json.loads(poster.calls[1][1])
    assert second_body["outcome"] == "success"
    assert "external_ref" not in second_body


def test_outcome_failure_when_provider_errors():
    poster = _FakePoster()
    config = Config(report_enabled=True, agent_key_id="ak_test", agent_secret="s3cret")
    report_run(config, _result(has_error=True), poster=poster)
    second_body = json.loads(poster.calls[1][1])
    assert second_body["outcome"] == "failure"


def test_reporting_error_carries_status_and_detail():
    err = ReportingError(422, '{"detail": "bad request"}')
    assert err.status_code == 422
    assert "bad request" in err.detail


def test_duration_ms_is_never_zero():
    poster = _FakePoster()
    config = Config(report_enabled=True, agent_key_id="ak_test", agent_secret="s3cret")
    report_run(config, _result(), poster=poster)
    second_body = json.loads(poster.calls[1][1])
    assert isinstance(second_body["duration_ms"], int)
    assert second_body["duration_ms"] >= 1


def test_duration_ms_reflects_real_elapsed_run_time():
    import time

    poster = _FakePoster()
    config = Config(report_enabled=True, agent_key_id="ak_test", agent_secret="s3cret")
    run_started = time.monotonic() - 2.5
    report_run(config, _result(), poster=poster, run_started=run_started)
    second_body = json.loads(poster.calls[1][1])
    assert second_body["duration_ms"] >= 2500
