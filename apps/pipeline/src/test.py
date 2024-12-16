from pyspark.sql import SparkSession

# Spark Master URL (from your logs)
spark_master_url = "spark://spark-master:7077"

# Get your machine's IP address (replace 172.20.10.6 with your IP if static)
driver_host_ip = "172.20.10.6"  # Machine IP that Docker containers can access

spark = (
    SparkSession.builder
    .appName("Spark Application on Cluster")
    .master(spark_master_url)  # Connect to the Spark Master
    .config("spark.driver.host", driver_host_ip)  # Driver IP visible to Spark workers
    .config("spark.driver.bindAddress", "0.0.0.0")  # Bind to all interfaces
    .config("spark.ui.port", "4045")  # Avoid port conflicts
    .config("spark.executor.memory", "1g")  # Adjust executor memory
    .config("spark.executor.cores", "1")  # Adjust executor cores
    .getOrCreate()
)

print("Spark Session Initialized Successfully!")
spark.sparkContext.setLogLevel("WARN")

# Example operation to test
data = [("Alice", 1), ("Bob", 2), ("Charlie", 3)]
columns = ["Name", "ID"]

df = spark.createDataFrame(data, columns)
df.show()
