from pyspark.sql import SparkSession
from sqlalchemy import create_engine
from io import BytesIO
import pandas as pd
import boto3
import os


def process_minio_data():
    # MinIO Configuration
    minio_endpoint = "http://minio:9000"  # MinIO endpoint
    access_key = "nguyenhoang"            # Your MINIO_ROOT_USER
    secret_key = "nguyenhoang"            # Your MINIO_ROOT_PASSWORD
    bucket_name = "sales-data"            # Bucket name
    folder_prefix = "batch_processed/"    # Folder path in MinIO containing CSV files
    local_dir = "/app/pipeline/src/data/raw_data/batch_processed"  # Local folder to temporarily store CSV files

    # PostgreSQL Configuration
    postgres_connection = "postgresql://postgres:postgres@host.docker.internal:5431/sales"

    # Ensure the local directory exists
    os.makedirs(local_dir, exist_ok=True)

    # Create a SparkSession
    spark = SparkSession.builder \
        .appName("Read Multiple MinIO CSVs with Spark") \
        .config("spark.hadoop.fs.s3a.endpoint", minio_endpoint) \
        .config("spark.hadoop.fs.s3a.access.key", access_key) \
        .config("spark.hadoop.fs.s3a.secret.key", secret_key) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()

    # Create a connection to MinIO using Boto3
    s3_client = boto3.client(
        's3',
        endpoint_url=minio_endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )

    # List all CSV files in the MinIO folder
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=folder_prefix)
    if 'Contents' in response:
        csv_files = [obj['Key'] for obj in response['Contents'] if obj['Key'].endswith('.csv')]
        print("Found CSV files:", csv_files)
    else:
        print("No files found in the specified folder.")
        csv_files = []

    # Download all CSV files from MinIO to a local directory
    for file_key in csv_files:
        local_file_path = os.path.join(local_dir, os.path.basename(file_key))
        print(f"Downloading {file_key} to {local_file_path}...")
        s3_client.download_file(bucket_name, file_key, local_file_path)

    # Use Spark to read all downloaded CSV files into a single DataFrame
    spark_df = spark.read.option("header", "true").csv(f"{local_dir}/*.csv")

    # Convert Spark DataFrame to Pandas DataFrame
    pandas_df = spark_df.toPandas()

    # Clean and format the DataFrame
    cleaned_data_df = (
        pandas_df.dropna(how='all')
        .drop_duplicates()
        .reset_index(drop=True)
    )
    cleaned_data_df = cleaned_data_df[cleaned_data_df['Order ID'] != 'Order ID'].reset_index(drop=True)
    cleaned_data_df = cleaned_data_df[cleaned_data_df['Order ID'].notna()]
    cleaned_data_df = cleaned_data_df[cleaned_data_df['Order ID'] != 'Order ID']

    formatted_data_df = cleaned_data_df.drop("Purchase Address", axis=1)
    formatted_data_df = formatted_data_df.rename(columns={
        'Order ID': 'Sale_ID',
        'Quantity Ordered': 'Quantity_Sold',
        'Price Each': 'Each_Price',
        'Order Date': 'Sale_Date'
    })

    # Convert data types
    formatted_data_df[['Sale_ID', 'Quantity_Sold', 'Each_Price']] = formatted_data_df[['Sale_ID', 'Quantity_Sold', 'Each_Price']].astype({
        'Sale_ID': 'int64',
        'Quantity_Sold': 'int64',
        'Each_Price': 'float64'
    })
    formatted_data_df['Sale_Date'] = pd.to_datetime(
        formatted_data_df['Sale_Date'], format='%m/%d/%y %H:%M'
    )
    formatted_data_df['Sales'] = formatted_data_df['Quantity_Sold'] * formatted_data_df['Each_Price']
    formatted_data_df = formatted_data_df.sort_values(by='Sale_Date').reset_index(drop=True)

    # Extract day, month, and year
    formatted_data_df['Day'] = formatted_data_df['Sale_Date'].dt.day
    formatted_data_df['Month'] = formatted_data_df['Sale_Date'].dt.month
    formatted_data_df['Year'] = formatted_data_df['Sale_Date'].dt.year

    # Print the number of rows
    length = len(formatted_data_df)
    print(f"The DataFrame has {length} rows.")

    # Save to PostgreSQL
    engine = create_engine(postgres_connection)
    formatted_data_df.to_sql(
        name='sales_data',
        con=engine,
        if_exists='replace',
        index=False
    )

    # Prepare Stock Quantity DataFrame
    stock_df = formatted_data_df.drop(['Sale_ID', 'Each_Price', 'Sale_Date', 'Sales', 'Day', 'Month', 'Year'], axis=1)
    stocks_df = stock_df.groupby(['Product'], as_index=False)['Quantity_Sold'].sum()
    stocks_df['Stock_Quantity'] = 31000

    # Save the DataFrame locally
    processed_data_path = "./data/processed_data"
    os.makedirs(processed_data_path, exist_ok=True)
    stocks_df.to_csv(f"{processed_data_path}/Stock_Quantity.csv", index=False)

    # Upload the CSV to MinIO
    file_name1 = "Stock_Quantity.csv"
    file_path1 = f"{processed_data_path}/{file_name1}"

    csv_buffer = BytesIO()
    stocks_df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    s3_client.put_object(Bucket=bucket_name, Key=file_name1, Body=csv_buffer.getvalue())
    print(f"File '{file_name1}' uploaded to bucket '{bucket_name}' successfully.")

    # Stop SparkSession
    spark.stop()
