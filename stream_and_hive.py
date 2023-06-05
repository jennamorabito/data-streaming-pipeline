#!/usr/bin/env python
"""Extract events from kafka and write them to hdfs
"""
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, from_json
from pyspark.sql.types import StructType, StructField, StringType

# Tells Spark what schema to expect
def event_schema():
    """
    root
    |-- Accept: string (nullable = true)
    |-- Host: string (nullable = true)
    |-- User-Agent: string (nullable = true)
    |-- event_type: string (nullable = true)
    """
    return StructType([
        StructField("Accept", StringType(), True),
        StructField("Host", StringType(), True),
        StructField("User-Agent", StringType(), True),
        StructField("event_type", StringType(), True),
    ])

# Creating different tables for purchasing swords and joining guilds by filtering the Kafka stream
@udf('boolean')
def is_sword_purchase(event_as_json):
    """udf for filtering events
    """
    event = json.loads(event_as_json)
    if event['event_type'] == 'purchase_a_sword':
        return True
    return False

@udf('boolean')
def is_join_guild(event_as_json):
    """udf for filtering events
    """
    event = json.loads(event_as_json)
    if event['event_type'] == 'join_a_guild':
        return True
    return False


def main():
    """main
    """
    spark = SparkSession \
        .builder \
        .appName("ExtractEventsJob") \
        .enableHiveSupport() \
        .getOrCreate()

    # pulling in the raw json format
    raw_events = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:29092") \
        .option("subscribe", "events") \
        .load()

    # unrolling and filtering the Kakfa stream to land sword purchases in a normalized table
    sword_purchases = raw_events \
        .filter(is_sword_purchase(raw_events.value.cast('string'))) \
        .select(raw_events.value.cast('string').alias('raw_event'),
                raw_events.timestamp.cast('string'),
                from_json(raw_events.value.cast('string'),
                          event_schema()).alias('json')) \
        .select('raw_event', 'timestamp', 'json.*')
    
    # unrolling and filtering the Kakfa stream to land guild joins in a normalized table
    join_guild = raw_events \
        .filter(is_join_guild(raw_events.value.cast('string'))) \
        .select(raw_events.value.cast('string').alias('raw_event'),
                raw_events.timestamp.cast('string'),
                from_json(raw_events.value.cast('string'),
                          event_schema()).alias('json')) \
        .select('raw_event', 'timestamp', 'json.*')

    # creating or over-writing the table
    spark.sql("drop table if exists sword_purchases")
    sword_sql_string = """
        create external table if not exists sword_purchases (
            raw_event string,
            timestamp string,
            Accept string,
            Host string,
            `User-Agent` string,
            event_type string
            )
            stored as parquet
            location '/tmp/sword_purchases'
            tblproperties ("parquet.compress"="SNAPPY")
            """
    spark.sql(sword_sql_string)
    
    spark.sql("drop table if exists join_guild")
    guild_sql_string = """
        create external table if not exists join_guild (
            raw_event string,
            timestamp string,
            Accept string,
            Host string,
            `User-Agent` string,
            event_type string
            )
            stored as parquet
            location '/tmp/join_guild'
            tblproperties ("parquet.compress"="SNAPPY")
            """
    spark.sql(guild_sql_string)

    # landing the tables in parquet; updating every 60 seconds
    sink1 = sword_purchases \
        .writeStream \
        .format("parquet") \
        .option("checkpointLocation", "/tmp/checkpoints_for_sword_purchases") \
        .option("path", "/tmp/sword_purchases") \
        .trigger(processingTime="60 seconds") \
        .start()

    sink2 = join_guild \
        .writeStream \
        .format("parquet") \
        .option("checkpointLocation", "/tmp/checkpoints_for_join_guild") \
        .option("path", "/tmp/join_guild") \
        .trigger(processingTime="60 seconds") \
        .start()

    # run until the user ctrl + C's 
    sink1.awaitTermination()
    sink2.awaitTermination()


if __name__ == "__main__":
    main()
