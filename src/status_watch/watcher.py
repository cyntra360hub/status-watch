"""Orchestrates a single poll cycle: fetch each configured provider's
current incidents, diff against the persisted state to find incidents
never seen before, then update the state file.

Cold-start note: on the very first run (empty/missing state file), every
incident a provider's feed currently lists counts as "new", since there
is no prior baseline to diff against -- this is expected, not a bug.
Statuspage.io feeds typically list recent history (weeks to months), so
a first run's report can be large; subsequent runs only show genuinely
newly-opened incidents."""

from __future__ import annotations

from dataclasses import dataclass, field

from status_watch.config import Config
from status_watch.providers import Incident, fetch_incidents, fetch_text
from status_watch.state import load_state, save_state


@dataclass(frozen=True)
class ProviderOutcome:
    provider: str
    ok: bool
    error: str | None
    new_incidents: tuple[Incident, ...] = field(default_factory=tuple)
    total_incidents: int = 0


@dataclass(frozen=True)
class WatchResult:
    providers: tuple[ProviderOutcome, ...]

    @property
    def new_incidents(self) -> tuple[Incident, ...]:
        return tuple(i for p in self.providers for i in p.new_incidents)

    @property
    def has_errors(self) -> bool:
        return any(not p.ok for p in self.providers)

    @property
    def outcome(self) -> str:
        """Maps to the AiOps Enabler `task_completed` outcome enum
        (success | failure | escalated)."""
        if self.has_errors:
            return "failure"
        if self.new_incidents:
            return "escalated"
        return "success"


def run_watch(config: Config, fetcher=fetch_text) -> WatchResult:
    state = load_state(config.state_file)
    outcomes = []

    for provider in config.providers:
        seen = state.get(provider.name, set())
        try:
            current = fetch_incidents(provider, timeout=config.timeout_seconds, fetcher=fetcher)
        except Exception as exc:  # noqa: BLE001 - any fetch/parse failure is a provider error
            outcomes.append(ProviderOutcome(provider=provider.name, ok=False, error=str(exc)))
            continue

        current_ids = {i.incident_id for i in current}
        new = tuple(i for i in current if i.incident_id not in seen)
        state[provider.name] = seen | current_ids

        outcomes.append(
            ProviderOutcome(
                provider=provider.name,
                ok=True,
                error=None,
                new_incidents=new,
                total_incidents=len(current),
            )
        )

    save_state(config.state_file, state)
    return WatchResult(providers=tuple(outcomes))
