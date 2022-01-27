import asyncio
import shlex

import attrs

from z_workflows.bases import ConfigBase, WorkflowBase
from z_workflows.graph import Edge
from z_workflows.ops_collection import op_send_bell_to_terminal


@attrs.define(auto_attribs=True, frozen=True, slots=True)
class C(ConfigBase):
    SSH_DEST_SERVER: str = attrs.field()
    HDFS_PATH: str = attrs.field()


c = C(
    "binks1",
    "/bigdatahdfs/datalake/publish/"
    "rwds/Membership/enceladus_info_date=2022-01-19",
)


@attrs.define(auto_attribs=True, frozen=True, slots=True)
class WatchHDFSonBinks1(WorkflowBase):
    pass


async def hdfs_path_exists() -> bool:
    cmd = (
        f"ssh {shlex.quote(c.SSH_DEST_SERVER)} "
        f"hdfs dfs -ls {shlex.quote(c.HDFS_PATH)} "
    )
    proc = await asyncio.create_subprocess_shell(cmd)
    await proc.communicate()
    return proc.returncode == 0


hdfs_watch = WatchHDFSonBinks1(
    ops=(Edge(fn=op_send_bell_to_terminal, ins=(), outs=("_",)),),
    sensor=hdfs_path_exists,
    config=c,
)
