from diff import Post, new_posts, trim_seen, FLOOD_CAP


def test_new_posts_returns_unseen_only():
    current = [Post("a", "url_a", None), Post("b", "url_b", None)]
    seen = {"a"}
    assert new_posts(current, seen) == [Post("b", "url_b", None)]


def test_new_posts_returns_empty_when_all_seen():
    current = [Post("a", "url_a", None)]
    seen = {"a"}
    assert new_posts(current, seen) == []


def test_new_posts_returns_all_when_seen_empty():
    current = [Post("a", "url_a", None), Post("b", "url_b", None)]
    assert new_posts(current, set()) == current


def test_new_posts_preserves_current_order():
    current = [Post("c", "url_c", None), Post("a", "url_a", None), Post("b", "url_b", None)]
    seen = {"a"}
    assert new_posts(current, seen) == [Post("c", "url_c", None), Post("b", "url_b", None)]


def test_new_posts_flood_caps_to_five():
    current = [Post(str(i), f"url_{i}", None) for i in range(10)]
    result = new_posts(current, set())
    assert len(result) == FLOOD_CAP == 5
    # Should keep the NEWEST 5 (first 5 in fetch order, since fetch returns newest-first)
    assert [p.id for p in result] == ["0", "1", "2", "3", "4"]


def test_trim_seen_keeps_last_200():
    ids = [str(i) for i in range(300)]
    trimmed = trim_seen(ids)
    assert len(trimmed) == 200
    assert trimmed == ids[-200:]


def test_trim_seen_no_op_when_under_cap():
    ids = ["a", "b", "c"]
    assert trim_seen(ids) == ids
