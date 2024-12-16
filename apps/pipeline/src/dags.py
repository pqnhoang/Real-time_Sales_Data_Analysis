from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from apps.pipeline.src.kafka_trigger import generate_data
from apps.pipeline.src.spark_streaming import spark_stream_processing
from apps.pipeline.src.spark_batch import process_minio_data  # Import your processing function

# Default arguments for the DAG
DAG_DEFAULT_ARGS = {
    'owner': 'Alaa',
    'start_date': datetime(2023, 11, 11),
    'retries': 1,
    'retry_delay': timedelta(seconds=30)
}

# Creating the DAG with its configuration
with DAG(
    'begin_the_app',
    default_args=DAG_DEFAULT_ARGS,
    schedule_interval='0 1 * * *',
    catchup=False,
    description='Stream sales data into Kafka topic',
    max_active_runs=1
) as dag:
    
    # Task to begin Kafka data streaming
    Begin_Kafka_Stream_Task = PythonOperator(
        task_id='begin_streaming_to_kafka', 
        python_callable=generate_data,
        dag=dag
    )

    # Task to process streaming data using Spark
    Begin_Stream_Process = PythonOperator(
        task_id='stream',
        python_callable=spark_stream_processing,
        dag=dag
    )
    
    # Task to process MinIO data
    Process_MinIO_Data_Task = PythonOperator(
        task_id='process_minio_data',
        python_callable=process_minio_data,  # Replace with your function from process_minio_data.py
        dag=dag
    )

# Define the task dependencies
Begin_Kafka_Stream_Task >> Begin_Stream_Process
# Run Process_MinIO_Data_Task in parallel with other tasks
[Begin_Kafka_Stream_Task, Begin_Stream_Process] >> Process_MinIO_Data_Task
