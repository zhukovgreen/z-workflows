import asyncio

from unittest.mock import AsyncMock, Mock

from click.testing import CliRunner

from app.cli import main, run
from z_workflows import bases


def test_run_basic(monkeypatch):
    # sense_mock = AsyncMock(return_value=1)
    # monkeypatch.setattr(bases, "sense", sense_mock)
    runner = CliRunner()
    results = runner.invoke(
        main,
        [
            "run",
            "--workflow-name",
            "example_workflow",
        ],
        catch_exceptions=False,
    )
    results


def test_ls_basic():
    runner = CliRunner()
    results = runner.invoke(
        main,
        ["ls"],
        catch_exceptions=False,
    )
    results
