import os
import boto3
from urllib.parse import urlparse
import pandas as pd
import numpy as np
from io import BytesIO
from src.utils.logger import logger

def download_model_from_s3(s3_model_path: str, local_dir: str = "/tmp") -> str:
    """
    Downloads a file from S3 given its s3_model_path (e.g., "s3://my-bucket/path/to/model.onnx").
    Saves the file in the local folder specified by local_dir (defaults to "/tmp").
    
    Returns the local path to the downloaded file.
    """
    if not s3_model_path.startswith("s3://"):
        raise ValueError("s3_model_path must start with 's3://'.")
    
    # Extract bucket and key from S3 path
    s3_path_trim = s3_model_path[len("s3://"):]
    bucket, key = s3_path_trim.split("/", 1)
    
    # Define local output path
    local_path = os.path.join(local_dir, os.path.basename(key))
    
    # If file doesn't exist locally, download it
    if not os.path.exists(local_path):
        s3 = boto3.client("s3")
        s3.download_file(bucket, key, local_path)
    
    return local_path 

def read_from_s3(s3_path: str):
    """
    Reads a file from S3.
    
    Args:
        s3_path (str): Complete file path in S3 (e.g. 's3://bucket/path/to/file.npy')
    
    Returns:
        numpy.ndarray or pandas.DataFrame depending on the file extension
    """
    try:
        logger.info(f"Reading file from S3: {s3_path}")
        
        # Parse s3://bucket/key path
        path_parts = s3_path.replace("s3://", "").split("/")
        bucket = path_parts[0]
        key = "/".join(path_parts[1:])
        
        logger.info(f"Parsed S3 path - Bucket: {bucket}, Key: {key}")
        
        s3_client = boto3.client('s3')
        response = s3_client.get_object(Bucket=bucket, Key=key)
        
        # Read full content into memory
        file_content = BytesIO(response['Body'].read())
        
        # For numpy files (.npy)
        if s3_path.endswith('.npy'):
            logger.info("Loading .npy file from S3")
            return np.load(file_content)
        # For CSV files
        elif s3_path.endswith('.csv'):
            logger.info("Loading .csv file from S3")
            return pd.read_csv(file_content)
        else:
            raise ValueError(f"Unsupported file type: {s3_path}")
            
    except Exception as e:
        logger.error(f"Error reading from S3: {str(e)}")
        raise 