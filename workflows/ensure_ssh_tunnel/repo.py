import shlex
import subprocess

from dagster import (
    RunRequest,
    SolidExecutionContext,
    graph,
    op,
    repository,
    sensor,
)
from environs import Env


env = Env(expand_vars=True)
env.read_env()
SOCKS5_HOSTNAME = env.str("ZW_EST_SOCK5_HOSTNAME")
URL = env.str("ZW_EST_URL")
SSH_DEST_SERVER = env.str("ZW_EST_SSH_DEST_SERVER")


@op
def trigger_tunnel_command(context: SolidExecutionContext):
    context.log.info("executing command to restore ssh connection")
    subprocess.run(
        shlex.split(f"ssh -fNTD {SOCKS5_HOSTNAME} {SSH_DEST_SERVER}"),
        check=True,
    )
    context.log.info("ssh tunnel restored")


@graph
def job_maintain_ssh_tunnel_healthy():
    trigger_tunnel_command()


def ssh_tunnel_is_healthy(socks5_hostname: str, url: str) -> bool:
    return (
        subprocess.run(
            shlex.split(f"curl --socks5-hostname {socks5_hostname} {url}"),
        ).returncode
        == 0
    )


@sensor(
    job=job_maintain_ssh_tunnel_healthy.to_job(),
    minimum_interval_seconds=15,
)
def job_maintain_ssh_tunnel_healthy_sensor():
    if not ssh_tunnel_is_healthy(
        socks5_hostname=SOCKS5_HOSTNAME,
        url=URL,
    ):
        yield RunRequest(run_key=None)


@repository
def macos_workflows():
    return [
        job_maintain_ssh_tunnel_healthy_sensor,
    ]
