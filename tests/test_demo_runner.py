import json
import pytest
from pathlib import Path

from transparencyx.demo import create_demo_database, run_demo
from transparencyx.db.database import get_connection


@pytest.fixture
def demo_db(tmp_path):
    path = tmp_path / "demo_test.sqlite"
    create_demo_database(path)
    return path


def test_demo_database_creation(demo_db):
    """Demo database must contain the expected politician, assets, and trades."""
    with get_connection(demo_db) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM politicians")
        assert cursor.fetchone()[0] == 1

        cursor.execute("SELECT COUNT(*) FROM normalized_assets WHERE politician_id = 1")
        asset_count = cursor.fetchone()[0]
        assert asset_count >= 2

        cursor.execute("SELECT COUNT(*) FROM trades WHERE politician_id = 1")
        trade_count = cursor.fetchone()[0]
        assert trade_count >= 2

        # At least one asset with NULL max (partial range)
        cursor.execute("SELECT COUNT(*) FROM normalized_assets WHERE politician_id = 1 AND value_max IS NULL")
        assert cursor.fetchone()[0] >= 1

        # At least one trade with NULL max (partial range)
        cursor.execute("SELECT COUNT(*) FROM trades WHERE politician_id = 1 AND amount_max IS NULL")
        assert cursor.fetchone()[0] >= 1


def test_demo_export_runs(tmp_path):
    """run_demo must return a valid export dict with summary and trace."""
    db_path = tmp_path / "demo_export.sqlite"
    export = run_demo(db_path)

    assert isinstance(export, dict)
    assert export["politician_id"] == 1
    assert "summary" in export
    assert "trace" in export

    # JSON serializable
    serialized = json.dumps(export)
    assert isinstance(serialized, str)
    roundtrip = json.loads(serialized)
    assert roundtrip == export


def test_demo_cli_returns_dict(tmp_path, monkeypatch, capsys):
    """The demo-run CLI command must print valid JSON containing summary and trace."""
    import sys

    # Point the demo db to tmp_path so we don't pollute the project
    monkeypatch.setattr(
        "transparencyx.cli.Path",
        lambda p: tmp_path / "cli_demo.sqlite" if p == "data/demo.sqlite" else Path(p),
    )

    monkeypatch.setattr(sys, "argv", ["transparencyx", "demo-run"])

    from transparencyx.cli import main
    main()

    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert isinstance(output, dict)
    assert output["politician_id"] == 1
    assert "summary" in output
    assert "trace" in output
