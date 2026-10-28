# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import pytest

from coalitionkit_contracts import is_ulid, new_ulid, ulid_timestamp_ms


def test_new_ulid_shape_and_time() -> None:
    value = new_ulid(now_ms=1_792_000_000_000)
    assert len(value) == 26
    assert is_ulid(value)
    assert ulid_timestamp_ms(value) == 1_792_000_000_000


def test_new_ulid_is_unique_and_sorts_by_time() -> None:
    first = new_ulid(now_ms=1000)
    second = new_ulid(now_ms=2000)
    assert first < second
    assert new_ulid() != new_ulid()


def test_fixed_entropy_is_deterministic() -> None:
    assert new_ulid(now_ms=0, entropy=bytes(10)) == "0" * 26
    assert new_ulid(now_ms=0, entropy=b"\xff" * 10) == "0" * 10 + "Z" * 16


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "0" * 25,
        "0" * 27,
        "0" * 25 + "I",  # I, L, O and U are not in the alphabet
        "0" * 25 + "L",
        "0" * 25 + "O",
        "0" * 25 + "U",
        "0" * 25 + "a",  # lower case
        "0" * 25 + "\n",
        " " + "0" * 25,
    ],
)
def test_is_ulid_rejects(bad: str) -> None:
    assert not is_ulid(bad)


def test_is_ulid_rejects_non_strings() -> None:
    assert not is_ulid(123)
    assert not is_ulid(None)


def test_new_ulid_bounds() -> None:
    with pytest.raises(ValueError):
        new_ulid(now_ms=-1)
    with pytest.raises(ValueError):
        new_ulid(now_ms=2**48)
    with pytest.raises(ValueError):
        new_ulid(entropy=b"short")
    with pytest.raises(ValueError):
        ulid_timestamp_ms("nope")
