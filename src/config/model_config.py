"""
Configuration module for model settings.
Loads model configuration either from a local JSON file or AWS SSM Parameter Store.
"""
import os
import json
import boto3
from dotenv import load_dotenv
from src.utils.logger import logger

load_dotenv()

MODEL_CONFIG = {}

def load_model_config_from_ssm():
    """
    Loads the model configuration from AWS SSM Parameter Store.
    It assumes the parameter contains a JSON string.
    """
    logger.info("Attempting to load config from SSM...")
    environment = os.getenv("ENVIRONMENT", "dev")
    param_name = f"/{environment}/movie-recommender/models-config"
    logger.info(f"Looking for SSM parameter: {param_name}")
    
    try:
        ssm = boto3.client("ssm")
        logger.info("SSM client created successfully")
        response = ssm.get_parameter(Name=param_name, WithDecryption=True)
        logger.info("SSM parameter retrieved successfully")
        logger.info(f"SSM Response: {response}")
        config = json.loads(response["Parameter"]["Value"])
        logger.info(f"Parsed config from SSM: {config}")
        return config
    except Exception as e:
        logger.error(f"Error loading config from SSM: {str(e)}", exc_info=True)
        return None

def load_model_config_from_file():
    """
    Loads configuration from local models_config.json file.
    """
    logger.info("Loading config from local file...")
    config_path = os.path.join(os.path.dirname(__file__), "models_config.json")
    with open(config_path, "r") as f:
        config = json.load(f)
        logger.info(f"Parsed config from file: {config}")
        return config

def load_model_config():
    """
    Loads model configuration from either SSM or local file.
    Tries SSM first if USE_SSM is True, falls back to local if SSM fails.
    """
    use_ssm = os.getenv("USE_SSM", "false").lower() == "true"

    if use_ssm:
        logger.info("USE_SSM=True: Attempting to load config from SSM...")
        config_from_ssm = load_model_config_from_ssm()
        if config_from_ssm is None:
            logger.warning("Could not load from SSM, falling back to local file")
            config = load_model_config_from_file()
        else:
            config = config_from_ssm
    else:
        logger.info("USE_SSM=False: Loading config from local file")
        config = load_model_config_from_file()

    # Update global MODEL_CONFIG in place to maintain reference
    global MODEL_CONFIG
    MODEL_CONFIG.clear()
    MODEL_CONFIG.update(config)
    logger.info(f"MODEL_CONFIG updated to: {MODEL_CONFIG}")
    return MODEL_CONFIG

# Load configuration on startup
MODEL_CONFIG = load_model_config()
