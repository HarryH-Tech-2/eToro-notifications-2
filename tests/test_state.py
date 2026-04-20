import json
from pathlib import Path
from state import load_seen, save_seen


def test_load_seen_missing_file_returns_empty_set(tmp_path):
    missing = tmp_path / "seen.json"
    assert load_seen(missing) == set()


def test_load_seen_malformed_json_returns_empty_set(tmp_path):
    bad = tmp_path / "seen.json"
    bad.write_text("not json{")
    assert load_seen(bad) == set()


def test_load_seen_missing_key_returns_empty_set(tmp_path):
    bad = tmp_path / "seen.json"
    bad.write_text('{"other": []}')
    assert load_seen(bad) == set()


def test_load_seen_reads_ids(tmp_path):
    f = tmp_path / "seen.json"
    f.write_text('{"seen_ids": ["a", "b", "c"]}')
    assert load_seen(f) == {"a", "b", "c"}


def test_save_seen_writes_ids(tmp_path):
    f = tmp_path / "seen.json"
    save_seen(f, ["x", "y", "z"])
    data = json.loads(f.read_text())
    assert data == {"seen_ids": ["x", "y", "z"]}


def test_save_seen_creates_parent_directory(tmp_path):
    f = tmp_path / "nested" / "dir" / "seen.json"
    save_seen(f, ["a"])
    assert f.exists()


def test_save_seen_trims_to_cap(tmp_path):
    f = tmp_path / "seen.json"
    many = [str(i) for i in range(250)]
    save_seen(f, many)
    data = json.loads(f.read_text())
    assert len(data["seen_ids"]) == 200
    assert data["seen_ids"] == many[-200:]
