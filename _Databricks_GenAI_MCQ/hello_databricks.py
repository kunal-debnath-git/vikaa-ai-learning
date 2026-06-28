"""
Basic "Hello Databricks" program for interacting with a Databricks workspace via Databricks Connect.

This script demonstrates how to:
 - Establish a remote Spark session against your Databricks cluster.
 - List catalogs, schemas and tables in Unity Catalog.
 - Read a table from Unity Catalog into a Spark DataFrame.
 - Read a CSV file from DBFS.

Before running this script you must configure Databricks Connect and replace the placeholders below with
values from your Databricks workspace:
 - server_hostname: The workspace URL (e.g. "adb-1234567890123456.17.azuredatabricks.net").
 - http_path: The HTTP path of the cluster or SQL warehouse you want to connect to.
 - personal_access_token: A Databricks personal access token with appropriate permissions.

References:
https://docs.databricks.com/dev-tools/databricks-connect.html

Note: Uncomment lines as needed once you have configured your environment. This script is intended as a
starting point for your lab exercises.
"""

from databricks.connect import DatabricksSession
from pyspark.sql import DataFrame

# TODO: Replace with your workspace settings
server_hostname = "<your-workspace-host>"  # e.g. "adb-1234567890123456.17.azuredatabricks.net"
http_path = "<your-http-path>"             # e.g. "/sql/1.0/warehouses/abc123..."
personal_access_token = "<your-personal-access-token>"

# Establish a remote Spark session
spark = DatabricksSession.builder \
    .server_hostname(server_hostname) \
    .http_path(http_path) \
    .token(personal_access_token) \
    .getOrCreate()

print("Connected to Databricks!")

# List catalogs in Unity Catalog
print("\nAvailable catalogs:")
spark.sql("SHOW CATALOGS").show(truncate=False)

# Choose a catalog/schema/table that you have access to
catalog_name = "<catalog>"
schema_name = "<schema>"
table_name = "<table>"

# Read a Unity Catalog table
try:
    full_table_name = f"{catalog_name}.{schema_name}.{table_name}"
    df: DataFrame = spark.read.table(full_table_name)
    print(f"\nFirst 5 rows from {full_table_name}:")
    df.show(5)
except Exception as e:
    print(f"Could not read table {catalog_name}.{schema_name}.{table_name}: {e}")

# Read a CSV file stored in DBFS (Databricks File System)
csv_path = "dbfs:/FileStore/path/to/your/file.csv"  # Replace with your actual DBFS path

try:
    csv_df: DataFrame = spark.read.format("csv").option("header", "true").load(csv_path)
    print("\nPreview of CSV file loaded from DBFS:")
    csv_df.show(5)
except Exception as e:
    print(f"Could not load CSV file from {csv_path}: {e}")

# Stop the session when done
spark.stop()
print("Session closed.")
