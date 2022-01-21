import asyncio
import shlex

import attrs

from workflows.ops_collection import op_send_bell_to_terminal
from z_workflows.bases import ConfigBase, WorkflowBase
from z_workflows.graph import Edge


@attrs.define(slots=True, frozen=True, auto_attribs=True)
class C(ConfigBase):
    SOCKS5_HOSTNAME: str = attrs.field()
    SSH_DEST_SERVER: str = attrs.field()
    URL: str = attrs.field()


c = C(
    "127.0.0.1:8888",
    "mail",
    "zhukovgreen.pro",
)


async def op_trigger_ssh_tunnel_cmd():
    # TODO create utils fn for subprocess calls
    cmd = (
        f"ssh -fNTD "
        f"{shlex.quote(c.SOCKS5_HOSTNAME)} "
        f"{shlex.quote(c.SSH_DEST_SERVER)}"
    )
    proc = await asyncio.create_subprocess_shell(cmd)
    await proc.communicate()


@attrs.define(slots=True, auto_attribs=True)
class EnsureSSHTunnel(WorkflowBase):
    pass


async def ssh_tunnel_is_not_healthy() -> bool:
    cmd = (
        f"curl --socks5-hostname "
        f"{shlex.quote(c.SOCKS5_HOSTNAME)} "
        f"{shlex.quote(c.URL)}"
    )
    proc = await asyncio.create_subprocess_shell(cmd)
    await proc.communicate()
    return proc.returncode != 0


ssh_tunnel = EnsureSSHTunnel(
    ops=(
        Edge(fn=op_trigger_ssh_tunnel_cmd, ins=(), outs=("_",)),
        Edge(fn=op_send_bell_to_terminal, ins=(), outs=("__",)),
    ),
)
