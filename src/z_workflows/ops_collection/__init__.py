import asyncio


async def op_send_bell_to_terminal() -> None:
    cmd = "tput bel"
    proc = await asyncio.create_subprocess_shell(cmd)
    await proc.communicate()
