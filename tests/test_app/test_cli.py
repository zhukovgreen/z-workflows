from click.testing import CliRunner

from z_workflows.app.cli import main


def test_run_basic(monkeypatch):
    runner = CliRunner()
    results = runner.invoke(
        main,
        [
            "run",
            "--workflow-name",
            "ExampleWorkflow",
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
