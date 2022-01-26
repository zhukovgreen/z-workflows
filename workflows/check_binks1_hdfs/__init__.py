from workflows.check_binks1_hdfs.workflow import (
    c,
    hdfs_path_exists,
    hdfs_watch,
)


config = c
entrypoint = hdfs_watch.execute_on_sensor(hdfs_path_exists)
