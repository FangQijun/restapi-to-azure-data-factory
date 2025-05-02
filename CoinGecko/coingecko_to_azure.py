import requests
import json
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient


# Logging settings
current_time = datetime.now().strftime("%Y%m%d-%H%M%S")
log_filename = f"coingecko_azure_{current_time}.log"
logs_dir = "logs"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, log_filename)),
        logging.StreamHandler()  # Also keep console output
    ]
)
logger = logging.getLogger('coingecko_to_azure')


# Environment parameter configuration
load_dotenv()
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd"
AZURE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = os.environ.get("AZURE_CONTAINER_NAME", "cryptocurrency-data")


def fetch_coingecko_data():
    """
    Fetch cryptocurrency data from CoinGecko API
    """
    logger.info(f"Fetching data from CoinGecko API: {COINGECKO_API_URL}")
    
    try:
        response = requests.get(COINGECKO_API_URL)
        
        # Check if the request was successful
        if response.status_code == 200:
            logger.info("Successfully retrieved data from CoinGecko API")
            return response.text
        else:
            logger.error(f"API request failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception occurred when fetching data: {str(e)}")
        return None


def save_data_locally(data, timestamp):
    """
    Save the JSON data to a local file in the data directory
    """
    # Create filename with timestamp
    local_filename = os.path.join("data", f"coingecko_data_{timestamp}.json")
    
    try:
        with open(local_filename, 'w', encoding='utf-8') as f:
            f.write(data)
        logger.info(f"Data successfully saved locally to: {local_filename}")
        return local_filename
    except Exception as e:
        logger.error(f"Failed to save data locally: {str(e)}")
        return None


def upload_to_azure_blob(data, timestamp):
    """
    Upload the raw JSON data to Azure Blob Storage
    """
    if not AZURE_CONNECTION_STRING:
        logger.error("Azure Storage Connection String not found. Please set AZURE_STORAGE_CONNECTION_STRING environment variable.")
        return False
    
    try:
        blob_name = f"coingecko_data_{timestamp}.json"
        
        # Create the BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
        
        # Get container client
        try:
            container_client = blob_service_client.get_container_client(CONTAINER_NAME)
            # Check if container exists, create if it doesn't
            if not container_client.exists():
                logger.info(f"Container {CONTAINER_NAME} does not exist. Creating it...")
                container_client = blob_service_client.create_container(CONTAINER_NAME)
                logger.info(f"Container {CONTAINER_NAME} created successfully.")
        except Exception as e:
            logger.error(f"Error accessing or creating container: {str(e)}")
            return False
        
        # Create blob client
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)
        
        # Upload the data
        logger.info(f"Uploading data to blob: {blob_name}")
        blob_client.upload_blob(data)
        
        logger.info(f"Data successfully uploaded to {CONTAINER_NAME}/{blob_name}")
        return True
    
    except Exception as e:
        logger.error(f"Exception occurred when uploading to Azure: {str(e)}")
        return False


def main():
    """
    Main function to run the application
    """
    logger.info("Starting CoinGecko to Azure application")
    
    # Step 1: Fetch data from CoinGecko
    data = fetch_coingecko_data()
    
    if data:
        # Create timestamp for consistent filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Step 2: Save data locally
        local_file = save_data_locally(data, timestamp)
        if not local_file:
            logger.error("Failed to save data locally")
            return 1
        
        # Step 3: Upload to Azure
        success = upload_to_azure_blob(data, timestamp)
        
        if success:
            logger.info("Process completed successfully")
            return 0
        else:
            logger.error("Failed to upload data to Azure")
            return 1
    else:
        logger.error("Failed to fetch data from CoinGecko")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)