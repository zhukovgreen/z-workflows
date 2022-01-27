import asyncio
import importlib
import logging
import pkgutil

from functools import wraps
from pathlib import Path
from typing import Tuple, TypeVar

import attrs
import click

from click import Context

from z_workflows.app.logger import setup_logger
from z_workflows.bases import ConfigBase, WorkflowBase, _Workflow


_APP_KEY = "app"
_ENV_KEY = "env"
_WORKFLOWS_DIR_NAME = "workflows"
REPO_ROOT = Path(__file__).parents[2]

_Config = TypeVar("_Config", bound=ConfigBase)


CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
    "auto_envvar_prefix": "ZW",
}

logger = logging.getLogger(__name__)


def load_workflows() -> None:
    def inner(package: str) -> None:
        package_mod = importlib.import_module(package)
        for _, name, is_pkg in pkgutil.walk_packages(package_mod.__path__):
            full_name = package_mod.__name__ + "." + name
            importlib.import_module(full_name)
            if is_pkg:
                inner(full_name)

    inner(_WORKFLOWS_DIR_NAME)


def get_app(ctx) -> "Application":
    return ctx.obj[_APP_KEY]


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


def set_logger_callback(ctx, param, value):
    setup_logger("DEBUG" if value else "INFO")


verbose_option = click.option(
    "-v",
    "--verbose",
    is_flag=True,
    is_eager=True,
    callback=set_logger_callback,
    expose_value=False,
)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@verbose_option
@coro
async def main(ctx: Context) -> None:
    ctx.ensure_object(dict)
    app = Application()
    app.discover_workflows()

    ctx.obj[_APP_KEY] = app


@main.command(help="Run given workflow(s)")
@click.option(
    "--workflow-name",
    required=False,
    multiple=True,
    default=(),
    help=(
        "provide the name of the workflow. "
        "Use multiple times for more than one workflow to run. "
        "Without this option all workflows will be run."
    ),
)
@click.pass_context
@verbose_option
@coro
async def run(
    ctx: Context,
    workflow_name: Tuple[str, ...],
):
    app = get_app(ctx)
    try:
        await app.start(
            workflows_=workflow_name
            or tuple(w.__class__.__name__ for w in app.available_workflows)
        )
    finally:
        await app.shutdown()


@main.command(help="List available workflows")
@click.pass_context
@verbose_option
@coro
async def ls(ctx):
    for item in get_app(ctx).available_workflows:
        click.echo(item.__class__.__name__)


@attrs.define(auto_attribs=True, slots=True)
class Application:
    available_workflows: Tuple[_Workflow, ...] = attrs.field(init=False)

    def discover_workflows(self):
        logger.debug("Workflows discovering started.")
        load_workflows()
        self.available_workflows = tuple(WorkflowBase.instances)

    async def start(self, workflows_: Tuple[str, ...]):
        logger.info("Starting workflows execution.")
        available_workflows_names = tuple(
            w.__class__.__name__ for w in self.available_workflows
        )
        assert all(w in available_workflows_names for w in workflows_), (
            "Found unknown workflow name. See list of available workflows:\n"
            "`z-workflows ls`"
        )

        workflows_to_run = filter(
            lambda w: w.__class__.__name__ in workflows_,
            self.available_workflows,
        )
        await asyncio.gather(
            *map(
                lambda w: w.execute_on_sensor(),
                workflows_to_run,
            )
        )

    async def shutdown(self):
        logger.info("Shutdown the application started.")
        # TODO resources cleaning
