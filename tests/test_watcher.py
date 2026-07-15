import json
from pathlib import Path

from status_watch.config import Config
from status_watch.providers import Provider
from status_watch.watcher import run_watch

PROVIDER = Provider(name="github", kind="statuspage_json", url="https://example.test")


def _feed(*ids: str) -> str:
    return json.dumps({"incidents": [{"id": i, "name": f"incident {i}"} for i in ids]})


def test_first_run_all_incidents_are_new(tmp_path: Path):
    # A completed poll that finds new incidents is still "success" --
    # detection is this agent doing its job, not a failure. The finding
    # is surfaced via findings_summary (reported as external_ref), not
    # via a non-success outcome.
    config = Config(providers=(PROVIDER,), state_file=tmp_path / "state.json")
    result = run_watch(config, fetcher=lambda url, timeout: _feed("a", "b"))
    assert len(result.new_incidents) == 2
    assert result.outcome == "success"
    assert result.findings_summary == "new incidents: github(2)"


def test_second_run_only_reports_genuinely_new_incidents(tmp_path: Path):
    state_file = tmp_path / "state.json"
    config = Config(providers=(PROVIDER,), state_file=state_file)

    run_watch(config, fetcher=lambda url, timeout: _feed("a", "b"))
    second = run_watch(config, fetcher=lambda url, timeout: _feed("a", "b", "c"))

    assert len(second.new_incidents) == 1
    assert second.new_incidents[0].incident_id == "c"
    assert second.outcome == "success"
    assert second.findings_summary == "new incidents: github(1)"


def test_no_new_incidents_is_success(tmp_path: Path):
    state_file = tmp_path / "state.json"
    config = Config(providers=(PROVIDER,), state_file=state_file)

    run_watch(config, fetcher=lambda url, timeout: _feed("a"))
    second = run_watch(config, fetcher=lambda url, timeout: _feed("a"))

    assert second.new_incidents == ()
    assert second.outcome == "success"
    assert second.findings_summary is None


def test_provider_fetch_failure_is_reported_as_error(tmp_path: Path):
    config = Config(providers=(PROVIDER,), state_file=tmp_path / "state.json")

    def failing_fetcher(url, timeout):
        raise TimeoutError("connection timed out")

    result = run_watch(config, fetcher=failing_fetcher)
    assert result.has_errors
    assert result.outcome == "failure"
    assert result.providers[0].error is not None


def test_state_file_persists_across_calls(tmp_path: Path):
    state_file = tmp_path / "state.json"
    config = Config(providers=(PROVIDER,), state_file=state_file)
    run_watch(config, fetcher=lambda url, timeout: _feed("a", "b"))
    assert state_file.exists()
    saved = json.loads(state_file.read_text())
    assert set(saved["github"]) == {"a", "b"}


def test_multiple_providers_are_independent(tmp_path: Path):
    other = Provider(name="cloudflare", kind="statuspage_json", url="https://example2.test")
    config = Config(providers=(PROVIDER, other), state_file=tmp_path / "state.json")

    def fetcher(url, timeout):
        if "example2" in url:
            return _feed("x")
        return _feed("a")

    result = run_watch(config, fetcher=fetcher)
    assert len(result.providers) == 2
    assert {p.provider for p in result.providers} == {"github", "cloudflare"}


def test_findings_summary_lists_multiple_providers(tmp_path: Path):
    other = Provider(name="cloudflare", kind="statuspage_json", url="https://example2.test")
    config = Config(providers=(PROVIDER, other), state_file=tmp_path / "state.json")

    def fetcher(url, timeout):
        if "example2" in url:
            return _feed("x", "y")
        return _feed("a")

    result = run_watch(config, fetcher=fetcher)
    assert result.findings_summary == "new incidents: github(1), cloudflare(2)"
