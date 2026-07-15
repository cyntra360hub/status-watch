from pathlib import Path

from status_watch.state import load_state, save_state


def test_load_state_missing_file_returns_empty(tmp_path: Path):
    assert load_state(tmp_path / "nope.json") == {}


def test_save_then_load_roundtrips(tmp_path: Path):
    path = tmp_path / "state.json"
    save_state(path, {"github": {"a", "b"}, "azure": set()})
    loaded = load_state(path)
    assert loaded == {"github": {"a", "b"}, "azure": set()}


def test_save_creates_parent_directories(tmp_path: Path):
    path = tmp_path / "nested" / "dir" / "state.json"
    save_state(path, {"github": {"a"}})
    assert path.exists()
    assert load_state(path) == {"github": {"a"}}
