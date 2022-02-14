from click.testing import CliRunner

from z_workflows import bases
from z_workflows.app.cli import main


def test_run_basic(monkeypatch):
    monkeypatch.setattr(bases, "_EXECUTE_ON_SENSOR_ONCE", value=True)
    runner = CliRunner()
    results = runner.invoke(
        main,
        [
            "-v",
            "run",
            "--workflow-name",
            "ExampleWorkflowOne",
            "--workflow-name",
            "ExampleWorkflowTwo",
        ],
        catch_exceptions=False,
    )
    print(results.stdout)
    assert results.exit_code == 0


def test_ls_basic():
    runner = CliRunner()
    results = runner.invoke(
        main,
        [
            "ls",
        ],
        catch_exceptions=False,
    )
    assert results.output.strip() == "ExampleWorkflowOne\nExampleWorkflowTwo"


def test_run_on_schedule(monkeypatch):
    monkeypatch.setattr(bases, "_EXECUTE_ON_SENSOR_ONCE", value=True)
    runner = CliRunner()
    results = runner.invoke(
        main,
        [
            "-v",
            "run",
            "--workflow-name",
            "ExampleWorkflowOne",
            "--on-schedule",
            "'aaa'",
            "--workflow-name",
            "ExampleWorkflowTwo",
            # "--on-schedule",
            # "'bbb'",
        ],
        catch_exceptions=False,
    )
    assert results.output.strip() == "ExampleWorkflowOne\nExampleWorkflowTwo"
