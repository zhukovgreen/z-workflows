import functools
import os
import sys

import pexpect

from environs import Env
from loguru import logger


def main():
    env = Env(expand_vars=True)
    env.read_env()
    spawn = functools.partial(
        pexpect.spawn,
        timeout=None,
        encoding="utf-8",
        env={
            **os.environ.copy(),
            **{"DAGSTER_HOME": env.str("DAGSTER_HOME")},
        },
    )

    try:
        daemon = spawn("dagster-daemon run")
        dagit = spawn("dagit -f src/z_workflows/ensure_ssh_tunnel/repo.py")

        dagit.logfile_read = sys.stdout
        daemon.logfile_read = sys.stdout

        daemon.expect(pexpect.EOF)
        dagit.expect(pexpect.EOF)
    finally:
        logger.info("graceful shutdown started")

        daemon.sendline(chr(3))
        daemon.close()

        dagit.sendline(chr(3))
        dagit.close()

        logger.info("graceful shutdown completed")
