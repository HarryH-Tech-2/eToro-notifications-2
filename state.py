"""State persistence for seen post IDs."""
import json
from pathlib import Path
from diff import trim_seen


def load_seen(path: Path) -> set[str]:
    """Read seen ids from `path`. Returns empty set if missing or malformed."""
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    ids = data.get("seen_ids")
    if not isinstance(ids, list):
        return set()
    return set(ids)


def save_seen(path: Path, ids: list[str]) -> None:
    """Write seen ids to `path`, trimmed to cap. Creates parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    trimmed = trim_seen(ids)
    path.write_text(
        json.dumps({"seen_ids": trimmed}, indent=2),
        encoding="utf-8",
    )
