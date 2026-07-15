"""Persists the set of incident IDs already seen per provider, so repeat
runs can tell a genuinely *new* incident from one already reported.

Stored as plain JSON: `{"<provider>": ["<incident_id>", ...], ...}`. In
CI this file is expected to be restored/saved across scheduled runs via
`actions/cache` (see `.github/workflows/scheduled.yml`) -- GitHub Actions
runners are otherwise stateless between runs.
"""

from __future__ import annotations

import json
from pathlib import Path


def load_state(path: Path) -> dict[str, set[str]]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {provider: set(ids) for provider, ids in raw.items()}


def save_state(path: Path, state: dict[str, set[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {provider: sorted(ids) for provider, ids in state.items()}
    path.write_text(json.dumps(serializable, indent=2, sort_keys=True), encoding="utf-8")
