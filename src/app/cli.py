import asyncio
import importlib
import logging

from functools import wraps
from pathlib import Path
from typing import Coroutine, Tuple, TypeVar

import attrs
import click

from click import Context
from environs import Env
from setuptools import find_packages

from app.logger import setup_logger
from z_workflows.bases import ConfigBase


_APP_KEY = "app"
_ENV_KEY = "env"
REPO_ROOT = Path(__file__).parents[2]

_Config = TypeVar("_Config", bound=ConfigBase)

logger = logging.getLogger(__name__)


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
    # setup_logger("INFO")
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
        await app.start(workflows_=workflow_name or app.available_workflows)
    finally:
        await app.shutdown()


@main.command(help="List available workflows")
@click.pass_context
@verbose_option
@coro
async def ls(ctx):
    for item in get_app(ctx).available_workflows:
        click.echo(item)


@attrs.define(auto_attribs=True, slots=True)
class Application:
    env: Env = attrs.field()
    available_workflows: Tuple[str, ...] = attrs.field(init=False)

    def discover_workflows(self):
        logger.debug("Workflows discovering started.")
        self.available_workflows = tuple(
            find_packages(str(REPO_ROOT / "workflows"))
        )

    async def start(self, workflows_: Tuple[str, ...]):
        logger.info("Starting workflows execution.")
        assert all(w in self.available_workflows for w in workflows_), (
            "Found unknown workflow name. See list of available workflows:"
            "\nz-workflows ls"
        )

        def get_entrypoint(workflow: str) -> Coroutine:
            w = importlib.import_module(f".{workflow}", "workflows")
            config: _Config = getattr(w, "config")
            return getattr(w, config.WORKFLOW_ENTRYPOINT)

        await asyncio.gather(*(map(get_entrypoint, workflows_)))

    async def shutdown(self):
        logger.info("Shutdown the application started.")
