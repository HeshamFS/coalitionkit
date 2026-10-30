# SPDX-License-Identifier: Apache-2.0
from unittest.mock import MagicMock, patch

import psycopg
import pytest

from coalitionkit_runtime.pool import ConnectionPool, StoreUnavailable


def test_pool_replaces_dead_connection_and_does_not_replay_transaction() -> None:
    first, second, third = MagicMock(), MagicMock(), MagicMock()
    with patch("psycopg.connect", side_effect=[first, second, third]):
        pool = ConnectionPool("unused", size=1)
        with pool.connection() as connection:
            assert connection is first
        first.execute.side_effect = psycopg.OperationalError("disconnected")
        with pool.connection() as connection:
            assert connection is second
        calls = 0
        with pytest.raises(StoreUnavailable), pool.connection():
            calls += 1
            raise psycopg.OperationalError("commit reply lost")
        assert calls == 1
        with pool.connection() as connection:
            assert connection is third
        pool.close()
        assert first.close.called and second.close.called and third.close.called


def test_pool_reconnect_backoff_then_recovers() -> None:
    with (
        patch("coalitionkit_runtime.pool.monotonic", return_value=10) as clock,
        patch("psycopg.connect") as connect,
    ):
        connect.side_effect = psycopg.OperationalError("down")
        pool = ConnectionPool("unused", size=1)
        for _ in range(2):
            with pytest.raises(StoreUnavailable), pool.connection():
                pytest.fail("unavailable connection yielded")
        assert connect.call_count == 1
        clock.return_value = 13
        connect.side_effect = None
        with pool.connection():
            pass
        assert connect.call_count == 2
        pool.close()
