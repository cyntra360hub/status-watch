# Contributing to status-watch

Thanks for considering a contribution! This is a small, focused tool —
keep changes deterministic (no LLM calls, no paid APIs) and offline-testable
(mock the network and filesystem, don't call real provider endpoints in tests).

## Getting started

```bash
git clone https://github.com/cyntra360hub/status-watch.git
cd status-watch
pip install -e ".[dev]"
pytest
```

## Workflow

1. Open an issue first for anything beyond a trivial fix, so we can agree
   on approach before you invest time.
2. Fork, branch, make your change, add/update tests.
3. Run `pytest` — all tests must pass, and new behavior needs new tests.
4. Open a PR describing what changed and why.

## Good first issues

These are scoped to be approachable without deep familiarity with the
codebase:

- **`good-first-issue`: Add a resolved-incident summary.** Currently
  `_print_report` in `cli.py` only lists *new* incidents. Add a summary
  line showing how many of a provider's currently-known incidents are
  resolved vs. still active, using `Incident.status` (already parsed for
  `statuspage_json` providers).
- **`good-first-issue`: Support Atlassian Statuspage "components"
  filtering.** Add an optional `components` field to `Provider` so a
  fork can watch only specific components of a status page (e.g. only
  "API" on GitHub's page) instead of all incidents.
- **`good-first-issue`: Add a `--provider` CLI flag.** Let a caller poll
  a single ad-hoc provider without editing `STATUS_WATCH_PROVIDERS`,
  useful for quick manual checks.
- **`good-first-issue`: Prune old entries from the state file.** Right
  now `state.py` only ever grows a provider's seen-ID set. Add an
  optional max-age or max-size prune (with tests using `tmp_path`) so
  long-running state files don't grow unbounded.
- **`good-first-issue`: Add a JSON output mode.** Add a `--json` flag (or
  `STATUS_WATCH_OUTPUT=json` env var) to `cli.py` that prints the
  `WatchResult` as machine-readable JSON instead of the human-readable
  report, for piping into other tools.

## Code style

- Standard library only, including AiOps Enabler reporting and
  onboarding (`signing.py`, `reporting.py`, `onboarding.py` use only
  `hmac`/`hashlib`/`urllib.request` — no SDK dependency).
- Keep network I/O behind an injectable `fetcher`/`poster` parameter (see
  `providers.py`, `reporting.py`) so tests never touch the network.
- No comments explaining *what* code does — only *why*, when non-obvious.
