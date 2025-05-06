import os
import re
import json
import logging
from datetime import datetime
import pandas as pd
import pyodbc
import sqlalchemy as sa
from sqlalchemy.engine import URL
from dotenv import load_dotenv


# Logging settings
current_time = datetime.now().strftime("%Y%m%d-%H%M%S")
log_filename = f"crypto_json_to_sql_{current_time}.log"
logs_dir = "logs"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, log_filename)),
        logging.StreamHandler()  # Also keep console output
    ]
)
logger = logging.getLogger('crypto_json_to_sql')


# Environment parameter configuration: SQL Server connection parameters
load_dotenv()
SQL_SERVER = os.environ.get("SQL_SERVER")
SQL_DATABASE = os.environ.get("SQL_DATABASE")
USERNAME = os.environ.get("SQL_USERNAME")
PASSWORD = os.environ.get("SQL_PASSWORD")


def get_latest_data_file():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, "data")
    pattern = re.compile(r'coingecko_data_(\d{8})_(\d{6})\.json$')
    
    latest_file, latest_timestamp = None, None
    for filename in os.listdir(data_dir):
        match = pattern.match(filename)
        if match:
            date_part = match.group(1)  # Extract YYYYMMDD substrings from the filename
            time_part = match.group(2)  # Extract HHMMSS substrings from the filename
            timestamp_str = f"{date_part}_{time_part}"
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                if latest_timestamp is None or timestamp > latest_timestamp:
                    latest_timestamp = timestamp
                    latest_file = filename
            except ValueError:
                continue # Skip files with invalid timestamps
    
    if latest_file is None:
        raise FileNotFoundError("No matching data files found")
    else:
        logger.info(f"Latest json file found: {latest_file}")

    return os.path.join(data_dir, latest_file)


def clean_dataframe(df):
    # Convert all dictionary/list columns to strings
    for column in df.columns:
        if df[column].apply(lambda x: isinstance(x, (dict, list))).any():
            df[column] = df[column].apply(lambda x: str(x) if isinstance(x, (dict, list)) else x)
    
    return df


def connect_to_sql_server(username, password, host, port, database):
    # Construct Microsoft SQL Server connection string for SQLAlchemy
    connection_url = URL.create(
        "mssql+pyodbc",
        username=username,
        password=password,
        host=host,
        port=port,  # Add explicit port
        database=database,
        query={
            "driver": "ODBC Driver 17 for SQL Server",
            "TrustServerCertificate": "yes",
            "Encrypt": "yes",
            "Connection Timeout": "60",
            "Command Timeout": "300"
        },
    )
    
    # Create SQLAlchemy engine 
    engine = sa.create_engine(connection_url)

    # Test connection to SQL Server
    try:
        with engine.connect() as connection:
            logger.info("Successfully connected to database")
            return engine
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        raise


def create_sql_server_table(engine, table_name, df):
    try:
        df.to_sql('crypto_data', engine, if_exists='replace', index=False)
        logger.info("Data successfully loaded to SQL Server!")
    except Exception as e:
        logger.error(f"Failed to load data to SQL Server: {str(e)}")
        raise  # Re-raise the exception after logging


def main():
    # Read the JSON file
    latest_data_file = get_latest_data_file()
    with open(latest_data_file, 'r') as ldf:
        latest_data = json.load(ldf)
    df = pd.DataFrame(latest_data)
    df = clean_dataframe(df)

    sql_server_engine = connect_to_sql_server(
        username=USERNAME,
        password=PASSWORD,
        host=SQL_SERVER,
        port=1433,
        database=SQL_DATABASE
    )

    create_sql_server_table(
        engine=sql_server_engine,
        table_name='crypto_data',
        df=df
    )


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)