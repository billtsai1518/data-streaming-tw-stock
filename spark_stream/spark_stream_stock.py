import logging

from cassandra.cluster import Cluster
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType


def create_keyspace(session):
    session.execute("""
        CREATE KEYSPACE IF NOT EXISTS spark_streams_stock
        WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'};
    """)

    print("Keyspace created successfully!")


def create_table(session):
    session.execute("""
    CREATE TABLE IF NOT EXISTS spark_streams_stock.tw_stock_day (
        "id" UUID PRIMARY KEY,
        "Code" TEXT,
        "Name" TEXT,
        "TradeVolume" TEXT,
        "TradeValue" TEXT,
        "OpeningPrice" TEXT,
        "HighestPrice" TEXT,
        "LowestPrice" TEXT,
        "ClosingPrice" TEXT,
        "Change" TEXT,
        "Transaction" TEXT);
    """)

    print("Table created successfully!")

def create_spark_connection():
    s_conn = None

    try:
        s_conn = SparkSession.builder \
            .appName('SparkDataStreaming') \
            .config('spark.jars.packages', "com.datastax.spark:spark-cassandra-connector_2.12:3.5.0,"
                                           "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
            .config('spark.cassandra.connection.host', 'cassandra_db') \
            .getOrCreate()

        s_conn.sparkContext.setLogLevel("ERROR")
        logging.info("Spark connection created successfully!")
    except Exception as e:
        logging.error(f"Couldn't create the spark session due to exception {e}")
    return s_conn


def connect_to_kafka(spark_conn):
    spark_df = None
    try:
        spark_df = spark_conn.readStream \
            .format('kafka') \
            .option('kafka.bootstrap.servers', 'broker:29092') \
            .option('subscribe', 'tw_stock_day_all') \
            .option('startingOffsets', 'earliest') \
            .option('failOnDataLoss', 'false') \
            .load()
        logging.info("kafka dataframe created successfully")
    except Exception as e:
        logging.warning(f"kafka dataframe could not be created because: {e}", exc_info=True)

    return spark_df


def create_cassandra_connection():
    try:
        # connecting to the cassandra cluster
        cluster = Cluster(['cassandra_db'])

        cas_session = cluster.connect()

        return cas_session
    except Exception as e:
        logging.error(f"Could not create cassandra connection due to {e}")
        return None


def create_selection_df_from_kafka(spark_df):
    schema = StructType([
        StructField("id", StringType(), False),
        StructField("Code", StringType(), False),
        StructField("Name", StringType(), False),
        StructField("TradeVolume", StringType(), False),
        StructField("TradeValue", StringType(), False),
        StructField("OpeningPrice", StringType(), False),
        StructField("HighestPrice", StringType(), False),
        StructField("LowestPrice", StringType(), False),
        StructField("ClosingPrice", StringType(), False),
        StructField("Change", StringType(), False),
        StructField("Transaction", StringType(), False)
    ])

    sel = spark_df.selectExpr("CAST(value AS STRING)") \
        .select(from_json(col('value'), schema).alias('data')).select("data.*")
    print(sel)

    return sel


if __name__ == "__main__":
    # create spark connection
    spark_conn = create_spark_connection()

    if spark_conn is not None:
        # connect to kafka with spark connection
        spark_df = connect_to_kafka(spark_conn)
        selection_df = create_selection_df_from_kafka(spark_df)
        session = create_cassandra_connection()

        if session is not None:
            create_keyspace(session)
            create_table(session)

            logging.info("Streaming is being started...")
            print("Streaming is being started...")

            streaming_query = (selection_df.writeStream.format("org.apache.spark.sql.cassandra")
                               .option('checkpointLocation', '/tmp/checkpoint')
                               .option('keyspace', 'spark_streams_stock')
                               .option('table', 'tw_stock_day')
                               .start())

            # for debug
            #streaming_query = selection_df.writeStream \
            #    .outputMode("append") \
            #    .format("console") \
            #    .start()

            streaming_query.awaitTermination()
