"""Configuration for status-watch, sourced from environment variables."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from status_watch.providers import DEFAULT_PROVIDERS, Provider

DEFAULT_STATE_FILE = ".state/status_watch_state.json"
DEFAULT_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class Config:
    providers: tuple[Provider, ...] = DEFAULT_PROVIDERS
    state_file: Path = Path(DEFAULT_STATE_FILE)
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    report_enabled: bool = False
    agent_key_id: str | None = None
    agent_secret: str | None = None
    base_url: str = "https://api.aiopsenabler.com"


def load_config(env: dict[str, str] | None = None) -> Config:
    """Build a Config from environment variables (or an injected mapping,
    for tests). Reporting is opt-in: it only turns on when both
    STATUS_WATCH_AGENT_KEY_ID and STATUS_WATCH_AGENT_SECRET are set --
    see `onboarding.py` for the self-service flow a fork without keys
    can use to get its own pair."""
    source = env if env is not None else os.environ

    raw_providers = source.get("STATUS_WATCH_PROVIDERS", "").strip()
    if raw_providers:
        parsed = json.loads(raw_providers)
        providers = tuple(
            Provider(name=p["name"], kind=p["kind"], url=p["url"]) for p in parsed
        )
    else:
        providers = DEFAULT_PROVIDERS

    # `.get(key, default)` only falls back when the key is *absent* -- an
    # explicitly empty env var would otherwise silently win over the
    # default (and crash float() on ""), so empty/unset is treated the
    # same via `or`.
    state_file = Path(source.get("STATUS_WATCH_STATE_FILE") or DEFAULT_STATE_FILE)
    timeout_seconds = float(
        source.get("STATUS_WATCH_TIMEOUT_SECONDS") or DEFAULT_TIMEOUT_SECONDS
    )

    key_id = source.get("STATUS_WATCH_AGENT_KEY_ID") or None
    secret = source.get("STATUS_WATCH_AGENT_SECRET") or None
    base_url = source.get("STATUS_WATCH_BASE_URL") or "https://api.aiopsenabler.com"

    return Config(
        providers=providers,
        state_file=state_file,
        timeout_seconds=timeout_seconds,
        report_enabled=bool(key_id and secret),
        agent_key_id=key_id,
        agent_secret=secret,
        base_url=base_url,
    )
