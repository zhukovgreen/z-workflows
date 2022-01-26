import asyncio
import importlib
import logging
import pkgutil
import sys

from functools import wraps
from pathlib import Path
from typing import Coroutine, Tuple, TypeVar

import attrs
import click

from click import Context
from environs import Env

from app.logger import setup_logger
from z_workflows.bases import ConfigBase, WorkflowBase, _Workflow


_APP_KEY = "app"
_ENV_KEY = "env"
_WORKFLOWS_DIR_NAME = "workflows"
REPO_ROOT = Path(__file__).parents[2]

_Config = TypeVar("_Config", bound=ConfigBase)

logger = logging.getLogger(__name__)


def load_workflows() -> None:
    def inner(package: str) -> None:
        package = importlib.import_module(package)
        for _, name, is_pkg in pkgutil.walk_packages(package.__path__):
            full_name = package.__name__ + "." + name
            importlib.import_module(full_name)
            if is_pkg:
                inner(full_name)

    inner(_WORKFLOWS_DIR_NAME)


def get_app(ctx) -> "Application":
    return ctx.obj[_APP_KEY]


def get_env(ctx) -> Env:
    return ctx.obj[_ENV_KEY]


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


@click.group()
@click.pass_context
@verbose_option
@coro
async def main(ctx: Context) -> None:
    env = Env(expand_vars=True)
    env.read_env()

    ctx.ensure_object(dict)
    app = Application(env)
    app.discover_workflows()

    ctx.obj[_APP_KEY] = app
    ctx.obj[_ENV_KEY] = env


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
    env: Env = attrs.field()
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
