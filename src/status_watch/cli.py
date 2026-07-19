"""status-watch command-line entry point."""

from __future__ import annotations

import sys
import time

from status_watch.config import load_config
from status_watch.onboarding import first_run_message
from status_watch.reporting import report_run
from status_watch.watcher import WatchResult, run_watch


def _print_report(result: WatchResult) -> None:
    for outcome in result.providers:
        if not outcome.ok:
            print(f"[ERROR] {outcome.provider}: {outcome.error}")
            continue
        label = "NEW INCIDENTS" if outcome.new_incidents else "OK"
        print(f"[{label}] {outcome.provider}: {outcome.total_incidents} incident(s) known, "
              f"{len(outcome.new_incidents)} new")
        for incident in outcome.new_incidents:
            status = f" ({incident.status})" if incident.status else ""
            print(f"    - {incident.title}{status} [{incident.incident_id}]")
    print()
    print(f"Overall: outcome={result.outcome}, {len(result.new_incidents)} new incident(s) total")


def main() -> int:
    run_started = time.monotonic()
    config = load_config()
    result = run_watch(config)
    _print_report(result)

    if config.report_enabled:
        try:
            report_run(config, result, run_started=run_started)
            print("Reported run to AiOps Enabler.")
        except Exception as exc:  # noqa: BLE001
            print(f"AiOps Enabler reporting failed (non-fatal): {exc}", file=sys.stderr)
    else:
        print(first_run_message("STATUS_WATCH"))

    return 1 if result.has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
