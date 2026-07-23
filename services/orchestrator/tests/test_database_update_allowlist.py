"""Unit tests for the column allowlist on DatabaseManager update methods.

These guard the B608 fix (issue #83): ``update_organization`` / ``update_team``
interpolate column identifiers (which cannot be bound as query params), so the
identifiers MUST be validated against a fixed allowlist. A rejected column must
fail fast — before any DB connection is opened — and a valid update must only
ever emit allowlisted column identifiers with every value bound as a $N param.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

import database
from database import DatabaseManager


def _fake_db_connection(mock_conn):
    @asynccontextmanager
    async def _cm():
        yield mock_conn

    return _cm


@pytest.mark.database
class TestUpdateColumnAllowlist:
    async def test_update_organization_rejects_unknown_column(self):
        # A non-allowlisted key (here even carrying a SQL payload) must be
        # rejected with ValueError and must never reach the database.
        with patch.object(
            database, "get_db_connection", side_effect=AssertionError("connected!")
        ):
            with pytest.raises(ValueError):
                await DatabaseManager.update_organization(
                    "org-1", **{"name; DROP TABLE organizations; --": "x"}
                )

    async def test_update_team_rejects_unknown_column(self):
        with patch.object(
            database, "get_db_connection", side_effect=AssertionError("connected!")
        ):
            with pytest.raises(ValueError):
                await DatabaseManager.update_team("team-1", evil_column="x")

    async def test_update_organization_valid_columns_are_parameterized(self):
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")

        with patch.object(
            database, "get_db_connection", _fake_db_connection(mock_conn)
        ):
            ok = await DatabaseManager.update_organization(
                "org-1", name="New Name", description="Desc"
            )

        assert ok is True
        mock_conn.execute.assert_awaited_once()
        query, *params = mock_conn.execute.await_args.args

        # Only allowlisted identifiers appear; values are bound, not inlined.
        assert "name = $1" in query
        assert "description = $2" in query
        assert "updated_at = $3" in query
        assert "WHERE id = $4" in query
        assert "New Name" not in query  # value is a param, never in SQL text
        assert params[0] == "New Name"
        assert params[1] == "Desc"
        assert params[-1] == "org-1"

    async def test_update_team_valid_columns_are_parameterized(self):
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")

        with patch.object(
            database, "get_db_connection", _fake_db_connection(mock_conn)
        ):
            ok = await DatabaseManager.update_team(
                "team-1", name="Squad", team_type="engineering"
            )

        assert ok is True
        query, *params = mock_conn.execute.await_args.args
        assert "name = $1" in query
        assert "team_type = $2" in query
        assert "Squad" not in query
        assert params[-1] == "team-1"
