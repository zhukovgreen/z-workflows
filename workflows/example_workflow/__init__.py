from workflows.example_workflow.workflow import (
    c,
    example_workflow,
    sensor_example,
)


config = c
entrypoint = example_workflow.execute_on_sensor(sensor_example)
