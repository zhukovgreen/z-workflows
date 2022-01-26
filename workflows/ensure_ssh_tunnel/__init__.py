from workflows.ensure_ssh_tunnel.workflow import (
    c,
    sensor_ssh_tunnel_is_not_healthy,
    ssh_tunnel,
)


config = c
entrypoint = ssh_tunnel.execute_on_sensor(sensor_ssh_tunnel_is_not_healthy)
