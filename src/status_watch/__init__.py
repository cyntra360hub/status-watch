"""status-watch: polls public provider status pages/APIs and detects
newly opened incidents, with state kept between runs."""

from status_watch.watcher import WatchResult, run_watch

__all__ = ["WatchResult", "run_watch"]
__version__ = "0.1.0"
