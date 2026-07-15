from pathlib import Path

from status_watch.config import DEFAULT_STATE_FILE, load_config
from status_watch.providers import DEFAULT_PROVIDERS


def test_defaults_when_env_empty():
    config = load_config(env={})
    assert config.providers == DEFAULT_PROVIDERS
    assert config.state_file == Path(DEFAULT_STATE_FILE)
    assert config.report_enabled is False


def test_custom_state_file_from_env():
    config = load_config(env={"STATUS_WATCH_STATE_FILE": "/tmp/custom.json"})
    assert config.state_file == Path("/tmp/custom.json")


def test_custom_providers_from_json_env():
    import json

    providers_json = json.dumps(
        [{"name": "test", "kind": "statuspage_json", "url": "https://example.test"}]
    )
    config = load_config(env={"STATUS_WATCH_PROVIDERS": providers_json})
    assert len(config.providers) == 1
    assert config.providers[0].name == "test"


def test_reporting_enabled_only_when_both_creds_present():
    assert load_config(env={"STATUS_WATCH_AGENT_KEY_ID": "ak_x"}).report_enabled is False
    assert (
        load_config(
            env={"STATUS_WATCH_AGENT_KEY_ID": "ak_x", "STATUS_WATCH_AGENT_SECRET": "s"}
        ).report_enabled
        is True
    )
