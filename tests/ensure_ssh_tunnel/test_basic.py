from workflows.ensure_ssh_tunnel.repo import ssh_tunnel_is_healthy


def test_ssh_tunnel_is_healthy():
    res = ssh_tunnel_is_healthy("localhost:8888", "zhukovgreen.pro")
    assert res is True
