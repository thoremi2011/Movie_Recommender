import logging
import os
import sys

# Determine the project root directory and the logs folder
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')

# Create the logs directory if it doesn't exist
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Define the logfile path
LOG_FILE = os.path.join(LOG_DIR, 'project.log')

# Configure the logging settings
logging.basicConfig(
    level=logging.INFO,  # Set default logging level to INFO (adjust as needed)
    format="%(asctime)s [%(levelname)s] %(module)s.%(funcName)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),  # Save logs to file
        logging.StreamHandler(sys.stdout)         # Also output logs to console
    ]
)

# Create a global logger
logger = logging.getLogger('MovieRecommender')
logger.setLevel(logging.DEBUG)  # Cambiar a DEBUG para ver todos los logs

# Handler para archivo
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setLevel(logging.DEBUG)

# Handler para consola
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)

# Formato para los logs
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Añadir los handlers al logger
logger.addHandler(file_handler)
logger.addHandler(console_handler) 