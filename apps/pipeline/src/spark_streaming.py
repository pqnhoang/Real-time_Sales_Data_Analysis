import os
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, IntegerType, StringType, FloatType
from pyspark.sql.functions import col, from_json, to_timestamp, round, sum as spark_sum
from kafka import KafkaProducer
from json import dumps
import time
from pathlib import Path
from sqlalchemy import create_engine
import pandas as pd

# Kafka Configuration
KAFKA_TOPIC_NAME = 'sales-data'
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
POSTGRES_URL = "postgresql://postgres:postgres@localhost:5431/sales"

def write_to_postgres(df, table_name, mode='append'):
    """
    Write a Spark DataFrame to PostgreSQL using pandas for batch processing.
    :param df: Spark DataFrame
    :param table_name: PostgreSQL table name
    :param mode: Append or overwrite
    """
    try:
        pandas_df = df.toPandas()
        engine = create_engine(POSTGRES_URL)
        pandas_df.to_sql(table_name, engine, if_exists=mode, index=False)
        print(f"Data successfully written to table: {table_name}")
    except Exception as e:
        print(f"Error writing to PostgreSQL: {e}")


def spark_stream_processing():
    """
    Consume data from Kafka and write results to PostgreSQL.
    """
    from pyspark.sql import SparkSession

    spark = (
    SparkSession.builder
    .appName("Streaming from Kafka to Postgres")
    .master("spark://spark-master:7077")  # Set the Spark master URL to the correct IP
    .config("spark.sql.shuffle.partitions", 4)
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.13:3.5.0")
    .config("spark.driver.bindAddress", "0.0.0.0")  # Bind driver to any available address
    .config("spark.driver.host", "0.0.0.0")   # Explicitly set the driver host   
    .getOrCreate()
)


    sales_schema = StructType([
        StructField('Order ID', IntegerType()),
        StructField('Product', StringType()),
        StructField('Quantity Ordered', IntegerType()),
        StructField('Price Each', FloatType()),
        StructField('Order Date', StringType()),
        StructField('Purchase Address', StringType())
    ])

    kafka_stream_df = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("subscribe", KAFKA_TOPIC_NAME)
        .option("startingOffsets", "latest")
        .load()
    )

    sales_df = kafka_stream_df.select(from_json(col("value").cast("string"), sales_schema).alias("sales")).select("sales.*")

    transformed_df = (
        sales_df
        .withColumn("Sale_Date", to_timestamp(col("Order Date"), "MM/dd/yy HH:mm"))
        .withColumn("Sales", round(col("Price Each") * col("Quantity Ordered"), 2))
        .drop("Purchase Address", "Order Date")
    )

    # Write streaming data to PostgreSQL
    sales_stream = transformed_df.writeStream \
        .outputMode("append") \
        .trigger(processingTime="5 seconds") \
        .foreachBatch(lambda df, epoch_id: write_to_postgres(df, "sales_stream")) \
        .start()

    # Write to console for debugging
    console_stream = transformed_df.writeStream \
        .outputMode("append") \
        .trigger(processingTime="5 seconds") \
        .format("console") \
        .start()

    sales_stream.awaitTermination()
    console_stream.awaitTermination()


def main():
    """
    Main entry point for Spark streaming and Kafka producer.
    """

    print("2. Starting Spark Stream Processing...")
    spark_stream_processing()


if __name__ == "__main__":
    main()
