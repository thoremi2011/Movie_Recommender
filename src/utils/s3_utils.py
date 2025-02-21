import os
import boto3
from urllib.parse import urlparse
import pandas as pd
import numpy as np
from io import BytesIO
from src.utils.logger import logger

def download_model_from_s3(s3_model_path: str, local_dir: str = "/tmp") -> str:
    """
    Descarga un archivo desde S3 dado su s3_model_path (por ejemplo, "s3://mi-bucket/path/to/model.onnx").
    Guarda el archivo en la carpeta local especificada por local_dir (por defecto "/tmp").
    
    Retorna la ruta local al archivo descargado.
    """
    if not s3_model_path.startswith("s3://"):
        raise ValueError("El s3_model_path debe comenzar con 's3://'.")
    
    # Extraer el bucket y el key del path S3
    s3_path_trim = s3_model_path[len("s3://"):]
    bucket, key = s3_path_trim.split("/", 1)
    
    # Definir la ruta local de salida
    local_path = os.path.join(local_dir, os.path.basename(key))
    
    # Si el archivo no existe ya en local, se descarga
    if not os.path.exists(local_path):
        s3 = boto3.client("s3")
        s3.download_file(bucket, key, local_path)
    
    return local_path 

def read_from_s3(s3_path: str):
    """
    Lee un archivo desde S3.
    
    Args:
        s3_path (str): Ruta completa del archivo en S3 (e.g. 's3://bucket/path/to/file.npy')
    
    Returns:
        numpy.ndarray o pandas.DataFrame dependiendo de la extensión del archivo
    """
    try:
        logger.info(f"Reading file from S3: {s3_path}")
        
        # Parsear la ruta s3://bucket/key
        path_parts = s3_path.replace("s3://", "").split("/")
        bucket = path_parts[0]
        key = "/".join(path_parts[1:])
        
        logger.info(f"Parsed S3 path - Bucket: {bucket}, Key: {key}")
        
        s3_client = boto3.client('s3')
        response = s3_client.get_object(Bucket=bucket, Key=key)
        
        # Leer el contenido completo en memoria
        file_content = BytesIO(response['Body'].read())
        
        # Para archivos numpy (.npy)
        if s3_path.endswith('.npy'):
            logger.info("Loading .npy file from S3")
            return np.load(file_content)
        # Para archivos CSV
        elif s3_path.endswith('.csv'):
            logger.info("Loading .csv file from S3")
            return pd.read_csv(file_content)
        else:
            raise ValueError(f"Unsupported file type: {s3_path}")
            
    except Exception as e:
        logger.error(f"Error reading from S3: {str(e)}")
        raise 