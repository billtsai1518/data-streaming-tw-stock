# Data Streaming Project: TWSE Stock

### Architecture

![architecture](img/architecture.PNG)

### Description

Use Airflow, Kafka, Spark, and Cassandra to establish a data pipeline.

It will fetch daily trading information of Taiwan stocks from [TWSE API](https://openapi.twse.com.tw/) every day.

### Screenshot

1. Airflow: do fetch task.
![airflow](img/airflow.PNG)

2. Kafka: we can see the stock information.
![kafka](img/kafka.PNG)

3. Cassandra: finally we store data here.
![cassandra](img/cassandra.PNG)
