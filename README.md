# boundary-layer
`boundary-layer` is a tool for building [Airflow](https://www.github.com/apache/incubator-airflow) DAGs from human-friendly, structured, maintainable yaml configuration.  It includes a migration tool for converting Oozie workflows into compatible yaml configs.

Boundary-layer is used heavily on the Etsy Data Platform: all of our Airflow DAGs are defined by YAML configurations, and our migration from Oozie to Airflow relied heavily on `boundary-layer`'s conversion tools.

Boundary-layer is _pluggable_, supporting custom configuration and extensions via plugins that are installed using `pip`.  The [core](core) package does not contain any etsy-specific customizations; instead, those are all defined in an internally-distributed etsy plugin package.

## Installation

`boundary-layer` is distributed via Pypi and can be installed using pip.

```
pip install boundary-layer --upgrade
```

We recommend installing into a [virtual environment](https://docs.python-guide.org/dev/virtualenvs/), but that's up to you.

You should now be able to run `boundary-layer` and view its help message:
```
$ boundary-layer --help
```
If the installation was successful, you should see output like:
```
usage: boundary-layer [-h] {build-dag,prune-dag,parse-oozie} ...

positional arguments:
  {build-dag,prune-dag,parse-oozie}

optional arguments:
  -h, --help            show this help message and exit
```

# boundary-layer YAML configs
The primary feature of boundary-layer is its ability to build python DAGs from simple, structured YAML files.

Below is a simple boundary-layer yaml config, used for running a Hadoop job on Google Cloud Dataproc:
```yaml
name: my_dag
dag_args:
  schedule_interval: '@daily'
resources:
- name: dataproc-cluster
  type: dataproc_cluster
  properties:
    cluster_name: my-cluster-{{ execution_date.strftime('%s') }}
    num_workers: 10
    region: us-central1
default_task_args:
  owner: etsy-data-platform
  project_id: my-project-id
  retries: 2
  start_date: '2018-10-31'
  dataproc_hadoop_jars:
  - gs://my-bucket/my/path/to/my.jar
before:
- name: data-sensor
  type: gcs_object_sensor
  properties:
    bucket: my-bucket
    object: my/object
operators:
- name: my-job
  type: dataproc_hadoop
  requires_resources:
  - dataproc-cluster
  properties:
    main_class: com.etsy.my.job.ClassName
    dataproc_hadoop_properties:
      mapreduce.map.output.compress: 'true'
    arguments: [ '--date', '{{ ds }}' ]
```
A few interesting features:
 - The `resources` section of the configuration defines a transient `DataProc` cluster resource that is required by the hadoop job.  `boundary-layer` will automatically insert the operators to create and delete this cluster, as well as the dependencies between the jobs and the cluster, when the DAG is created.
 - The `before` section of the configuration defines sensors that will be inserted by `boundary-layer` as prerequisites for all downstream operations in the DAG, including the creation of the transient DataProc cluster.

To convert the above YAML config into a python DAG, save it to a file (for convenience, this DAG is already stored in the [examples directory](examples/readme_example.yaml)) and run
```
$ boundary-layer build-dag readme_example.yaml > readme_example.py
```
and, if all goes well, this will write a valid Airflow DAG into the file  `readme_example.py`.  You should open this file up and look at its contents, to get a feel for what boundary-layer is doing.  In particular, after some comments at the top of the file, you should see something like this:
```python
import os
from airflow import DAG

import datetime

from airflow.operators.dummy_operator import DummyOperator
from airflow.contrib.sensors.gcs_sensor import GoogleCloudStorageObjectSensor
from airflow.contrib.operators.dataproc_operator import DataprocClusterDeleteOperator, DataProcHadoopOperator, DataprocClusterCreateOperator

DEFAULT_TASK_ARGS = {
        'owner': 'etsy-data-platform',
        'retries': 2,
        'project_id': 'my-project-id',
        'start_date': '2018-10-31',
        'dataproc_hadoop_jars': ['gs://my-bucket/my/path/to/my.jar'],
    }

dag = DAG(
        schedule_interval = '@daily',
        catchup = True,
        max_active_runs = 1,
        dag_id = 'my_dag',
        default_args = DEFAULT_TASK_ARGS,
    )

data_sensor = GoogleCloudStorageObjectSensor(
        dag = (dag),
        task_id = 'data_sensor',
        object = 'my/object',
        bucket = 'my-bucket',
        start_date = (datetime.datetime(2018, 10, 31, 0, 0)),
    )


dataproc_cluster_create = DataprocClusterCreateOperator(
        dag = (dag),
        task_id = 'dataproc_cluster_create',
        num_workers = 10,
        region = 'us-central1',
        cluster_name = "my-cluster-{{ execution_date.strftime('%s') }}",
        start_date = (datetime.datetime(2018, 10, 31, 0, 0)),
    )

dataproc_cluster_create.set_upstream(data_sensor)

my_job = DataProcHadoopOperator(
        dag = (dag),
        task_id = 'my_job',
        dataproc_hadoop_properties = { 'mapreduce.map.output.compress': 'true' },
        region = 'us-central1',
        start_date = (datetime.datetime(2018, 10, 31, 0, 0)),
        cluster_name = "my-cluster-{{ execution_date.strftime('%s') }}",
        arguments = ['--date','{{ ds }}'],
        main_class = 'com.etsy.my.job.ClassName',
    )

my_job.set_upstream(dataproc_cluster_create)

dataproc_cluster_destroy_sentinel = DummyOperator(
        dag = (dag),
        start_date = (datetime.datetime(2018, 10, 31, 0, 0)),
        task_id = 'dataproc_cluster_destroy_sentinel',
    )

dataproc_cluster_destroy_sentinel.set_upstream(my_job)

dataproc_cluster_destroy = DataprocClusterDeleteOperator(
        dag = (dag),
        task_id = 'dataproc_cluster_destroy',
        trigger_rule = 'all_done',
        region = 'us-central1',
        cluster_name = "my-cluster-{{ execution_date.strftime('%s') }}",
        priority_weight = 50,
        start_date = (datetime.datetime(2018, 10, 31, 0, 0)),
    )

dataproc_cluster_destroy.set_upstream(my_job)
```

This python DAG is now ready for ingestion directly into a running Airflow instance, following whatever procedure is appropriate for your Airflow deployments.

A few things to note:
 - `boundary-layer` converted the `start_date` parameter from a string to a python `datetime` object.  This is an example of the boundary-layer argument-preprocessor feature, which allows config parameters to be specified as user-friendly strings and converted to the necessary python data structures automatically.
 - `boundary-layer` added a `sentinel` node in parallel with the cluster-destroy node, which serves as an indicator to Airflow itself regarding the ultimate outcome of the Dag Run.  Airflow determines the Dag Run status from the leaf nodes of the DAG, and normally the cluster-destroy node will always execute (irrespective of upstream failures) and will likely succeed. This would cause DAGs with failures in critical nodes to be marked as successes, if not for the sentinel node.  The sentinel node will only trigger if all of its upstream dependencies succeed --- otherwise it will be marked as `upstream-failed`, which induces a failure state for the Dag Run.

# Oozie Migration tools

In addition to allowing us to define Airflow workflows using YAML configurations, `boundary-layer` also provides a module for converting Oozie XML configuration files into `boundary-layer` YAML configurations, which can then be used to create Airflow DAGs.
