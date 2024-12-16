from kafka import KafkaProducer
from json import dumps
import pandas as pd
import time
from pathlib import Path

# Kafka Configuration
KAFKA_TOPIC_NAME = 'sales-data'
KAFKA_BOOTSTRAP_SERVERS = '10.17.4.125:9092'

def generate_data():
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda x: dumps(x).encode('utf-8')
    )

    file_path = Path('./data/raw_data/stream_processed/Sales_December_2019_sorted.csv')
    sales_df = pd.read_csv(file_path)
    sales_df['Order ID'] = pd.to_numeric(sales_df['Order ID'], errors='coerce').fillna(0).astype(int)
    sales_df['Price Each'] = pd.to_numeric(sales_df['Price Each'], errors='coerce').fillna(0).astype(float)
    sales_df['Quantity Ordered'] = pd.to_numeric(sales_df['Quantity Ordered'], errors='coerce').fillna(0).astype(int)
    sales_list = sales_df.to_dict(orient='records')

    for sale in sales_list:
        print(f"Sending: {sale}")
        producer.send(KAFKA_TOPIC_NAME, value=sale)
        time.sleep(1)
    print("Kafka Producer: Data streaming completed!")

if __name__ == '__main__':
    generate_data()
