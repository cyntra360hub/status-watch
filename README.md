# status-watch

A small, deterministic Python agent that polls public provider status
pages/APIs and detects **newly opened incidents**, keeping a state file
between runs so it only reports what's actually new.

No LLM calls, no paid APIs, no server to run — it's a script you run on
a schedule (cron, GitHub Actions, etc.) or by hand.

## What it does

For each configured provider, status-watch:

1. Fetches the provider's current incident list — either the
   [Statuspage.io](https://www.atlassian.com/software/statuspage) JSON
   API (used by GitHub, Cloudflare, and many others) or a generic RSS 2.0
   feed (used by Azure's status page).
2. Diffs the current incident IDs against a persisted state file of IDs
   already seen.
3. Reports any incident ID never seen before as "new".
4. Saves the updated set of seen IDs back to the state file.

Default providers: GitHub, Cloudflare, Azure.

**Cold-start note:** on the very first run (no state file yet), every
incident a provider's feed currently lists counts as "new" — there's no
prior baseline to diff against. This is expected: subsequent runs only
report genuinely newly-opened incidents.

## Install

Requires Python 3.12+.

```bash
pip install .
```

## Usage

```bash
status-watch
```

Or as a module:

```bash
python -m status_watch.cli
```

### Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `STATUS_WATCH_PROVIDERS` | GitHub + Cloudflare + Azure | JSON array of `{"name", "kind", "url"}` (`kind` is `statuspage_json` or `rss`) |
| `STATUS_WATCH_STATE_FILE` | `.state/status_watch_state.json` | where to persist seen-incident IDs |
| `STATUS_WATCH_TIMEOUT_SECONDS` | `15` | network timeout per provider |

Copy `.env.example` to `.env` to set these locally; `.env` is gitignored
and never committed.

## Optional: AiOps Enabler integration

status-watch can optionally report each poll cycle as a signed task
event to [AiOps Enabler](https://aiopsenabler.com), a public-interest
registry of verified AI agent performance. **This is opt-in and off by
default** — the agent never phones home unless you explicitly configure
credentials.

Reporting is implemented as **raw HMAC-signed REST**
(`src/status_watch/signing.py` + `reporting.py`), built directly from the
platform's own published spec ([skill.md](https://aiopsenabler.com/skill.md) §3,
[api-guide.md](https://aiopsenabler.com/api-guide.md) §2) using only the
standard library. This is a deliberate substitution for the
officially-documented Python SDK (`aiops-enabler`): its install command
points at `github.com/cyntra360hub/aiops-enabler`, which is currently a
**private** repository and not installable by the public despite being
the documented path for external integrators. Raw signed REST sidesteps
that and is functionally equivalent (same headers, same signing scheme,
same published test vector — see `tests/test_signing.py`).

### No AiOps Enabler credentials yet? Self-onboard.

status-watch ships a **reusable first-run config module**
(`src/status_watch/onboarding.py`) that implements the self-onboarding
flow [skill.md](https://aiopsenabler.com/skill.md) documents for any
agent (or fork of one) that doesn't have a key pair yet:

```bash
python -m status_watch.onboarding register \
  --name "My status-watch fork" \
  --category observability \
  --operator-email you@example.com
```

This does the one *unsigned* `POST /api/v1/skill-onboarding/register`
call and prints back a `key_id`/`secret` pair — save it immediately (the
secret is shown exactly once). Your operator email then receives a claim
link to review and publish the new agent profile. Once you have a pair,
set:

```
STATUS_WATCH_AGENT_KEY_ID=ak_...
STATUS_WATCH_AGENT_SECRET=...
```

(in `.env` locally, or as GitHub Actions secrets in CI — see
`.github/workflows/scheduled.yml`) and every run sends a signed
`task_started` / `task_completed` pair to `POST /api/v1/events`.
`outcome` is `success` whenever the poll actually ran — **including**
when it finds new incidents, since detecting that is this agent doing
its job, not a failure. `outcome` is `failure` only when a provider's
fetch itself errored (network failure, unparseable feed). Any newly
found incidents are summarized as a short, human-readable line in the
event's `details` field — what actually renders on your agent's public
pulse/profile activity — e.g. `"found 3 new incidents across 2
providers -- e.g. github: API latency degraded"`. The fuller
per-provider breakdown goes in the legacy `external_ref` field instead,
e.g. `"github(2), cloudflare(1)"`. If you run without credentials
configured, status-watch just prints a reminder pointing back at this
flow instead of silently doing nothing.

## Development

```bash
pip install -e ".[dev]"
pytest
```

All tests run fully offline — provider fetches, state I/O (via
`tmp_path`), signing, and reporting all use injected fakes, so the suite
never touches the network or the real filesystem outside pytest's own
temp dirs.

## License

MIT — see [LICENSE](LICENSE).
