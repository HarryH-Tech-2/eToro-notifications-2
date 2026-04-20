"""Pure diff and trim logic - no I/O."""
from dataclasses import dataclass


FLOOD_CAP = 5
SEEN_CAP = 200


@dataclass(frozen=True)
class Post:
    id: str
    url: str
    timestamp: str | None


def new_posts(current: list[Post], seen: set[str]) -> list[Post]:
    """Return posts in `current` whose IDs are not in `seen`, capped at FLOOD_CAP.

    `current` is expected to be newest-first; the flood cap keeps the newest.
    Order of the returned list matches the order of `current`.
    """
    unseen = [p for p in current if p.id not in seen]
    return unseen[:FLOOD_CAP]


def trim_seen(ids: list[str]) -> list[str]:
    """Keep only the most recent SEEN_CAP ids. Assumes ids are append-ordered."""
    if len(ids) <= SEEN_CAP:
        return ids
    return ids[-SEEN_CAP:]
