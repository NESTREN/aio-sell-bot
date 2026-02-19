from config import _parse_admin_ids


def test_parse_admin_ids_skips_invalid_values() -> None:
    assert _parse_admin_ids("1, 2, foo, 2") == {1, 2}


def test_parse_admin_ids_empty() -> None:
    assert _parse_admin_ids("") == set()
