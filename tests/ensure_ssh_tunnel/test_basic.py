from z_workflows.ensure_ssh_tunnel.repo import (
    job_maintain_ssh_tunnel_healthy,
    ssh_tunnel_is_healthy,
)


def test_basic():
    job_maintain_ssh_tunnel_healthy.execute_in_process()


def test_ssh_tunnel_is_healthy():
    res = ssh_tunnel_is_healthy("localhost:8888", "zhukovgreen.pro")
    assert res is True
