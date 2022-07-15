import asyncio
import importlib
import logging
import pkgutil

from collections.abc import Coroutine
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Iterable, ParamSpec, Tuple, TypeVar

import attrs
import click
import structlog

from click import Context, Option

from z_workflows.app.logger import setup_logger
from z_workflows.bases import ConfigBase, WorkflowBase


_APP_KEY = "app"
_ENV_KEY = "env"
_WORKFLOWS_DIR_NAME = "workflows"
REPO_ROOT = Path(__file__).parents[2]


CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
    "auto_envvar_prefix": "ZW",
}

_Config = TypeVar("_Config", bound=ConfigBase)
OPS_PARAMS = ParamSpec("OPS_PARAMS")
OPS_RET = TypeVar("OPS_RET")

logger = structlog.getLogger()


def load_workflows() -> None:
    def inner(package: str) -> None:
        package_mod = importlib.import_module(package)
        for _, name, is_pkg in pkgutil.walk_packages(package_mod.__path__):
            full_name = package_mod.__name__ + "." + name
            importlib.import_module(full_name)
            if is_pkg:
                inner(full_name)

    inner(_WORKFLOWS_DIR_NAME)


def get_app(ctx: Context) -> "Application":
    return ctx.obj[_APP_KEY]


def coro(
    f: Callable[
        OPS_PARAMS,
        Coroutine[None, None, OPS_RET],
    ]
) -> Callable[OPS_PARAMS, OPS_RET]:
    @wraps(f)
    def wrapper(
        *args: OPS_PARAMS.args,
        **kwargs: OPS_PARAMS.kwargs,
    ) -> OPS_RET:
        return asyncio.run(f(*args, **kwargs))

    return wrapper


def set_logger_callback(
    ctx: Context,
    param: Option,
    value: bool,
) -> None:
    setup_logger(logging.DEBUG if value else logging.INFO)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    is_eager=True,
    callback=set_logger_callback,
    expose_value=False,
)
@click.pass_context
@coro
async def main(ctx: Context) -> None:
    ctx.ensure_object(dict)
    app = Application()
    app.discover_workflows()

    ctx.obj[_APP_KEY] = app


@main.group(help="Run given workflow(s)", chain=True)
@click.pass_context
@coro
async def run(
    ctx: Context,
) -> None:
    app = get_app(ctx)
    try:
        await app.start()
    finally:
        await app.shutdown()


@main.command(help="List available workflows")
@click.pass_context
@coro
async def ls(ctx: Context) -> None:
    for item in get_app(ctx).available_workflows:
        click.echo(item.__class__.__name__)


@main.group()
@coro
async def completions() -> None:
    """Get shell completions scripts.

    Use --help to see available shells.

    Example:
        $ source <(z-workflows completions zsh)
    """


@completions.command(help="zsh completions script")
@coro
async def zsh() -> None:

    proc = await asyncio.subprocess.create_subprocess_shell(
        "_Z_WORKFLOWS_COMPLETE=zsh_source z-workflows",
        stdout=asyncio.subprocess.PIPE,
    )
    res, _ = await proc.communicate()
    click.echo(res.decode())


@completions.command(help="bash completions script")
@coro
async def bash() -> None:
    proc = await asyncio.subprocess.create_subprocess_shell(
        "_Z_WORKFLOWS_COMPLETE=bash_source z-workflows",
        stdout=asyncio.subprocess.PIPE,
    )
    res, _ = await proc.communicate()
    click.echo(res.decode())


@attrs.define(auto_attribs=True, slots=True)
class Application:
    available_workflows: Tuple[WorkflowBase, ...] = attrs.field(init=False)

    def discover_workflows(self) -> None:
        logger.debug("Workflows discovering started.")
        load_workflows()
        self.available_workflows = tuple(WorkflowBase.instances)

    async def start(
        self,
        workflows: Tuple[str, ...],
        schedules: Tuple[str, ...],
    ) -> None:
        logger.info("Starting workflows execution.")
        available_workflows_names = tuple(
            w.__class__.__name__ for w in self.available_workflows
        )
        assert all(w in available_workflows_names for w in workflows), (
            "Found unknown workflow name. See list of available workflows:\n"
            "`z-workflows ls`"
        )

        workflows_to_run = filter(
            lambda w: w.__class__.__name__ in workflows,
            self.available_workflows,
        )
        await asyncio.gather(
            *map(
                lambda w: asyncio.create_task(
                    w.execute_on_sensor(), name=w.id
                ),
                workflows_to_run,
            )
        )

    async def shutdown(self) -> None:
        logger.info("Shutdown the application started.")
        # TODO resources cleaning
