import asyncio
import logging

from functools import wraps

import attrs
import click

from environs import Env

from app.logger import setup_logger
from workflows.ensure_ssh_tunnel.workflow import ssh_tunnel_is_not_healthy, w
from z_workflows.bases import WorkflowBase


logger = logging.getLogger(__name__)


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


@click.command()
@click.option("--verbose", is_flag=True, default=False)
@click.option("--debug", is_flag=True, default=False)
@coro
async def main(verbose: bool, debug: bool) -> None:
    setup_logger()
    env = Env(expand_vars=True)
    env.read_env()
    app = Application()
    try:
        await app.discover_workflows()
        await app.start()
    finally:
        await app.shutdown()


@attrs.define(auto_attribs=True, slots=True)
class Application:
    async def discover_workflows(self):
        logger.info("Workflows discovering started.")

    async def start(self):
        logger.info("Starting workflows execution.")
        await w.execute_on_sensor(ssh_tunnel_is_not_healthy)

    async def shutdown(self):
        logger.info("Shutdown the application started.")
        ...
