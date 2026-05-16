import os
import glob
from config.settings import SPECIAL_DATA_DIR, GENERAL_DATA_DIR
import logging

logger = logging.getLogger(__name__)

def load_text_files(directory):
    """Simple text loader for the given directory."""
    documents = []
    if not os.path.exists(directory):
        logger.warning(f"Directory {directory} does not exist.")
        return documents
        
    for filepath in glob.glob(os.path.join(directory, "**/*.txt"), recursive=True):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                documents.append({"id": filepath, "content": content})
        except Exception as e:
            logger.error(f"Error reading {filepath}: {e}")
    return documents

def get_special_data():
    logger.info(f"Loading special data from {SPECIAL_DATA_DIR}")
    return load_text_files(SPECIAL_DATA_DIR)

def get_general_data():
    logger.info(f"Loading general data from {GENERAL_DATA_DIR}")
    return load_text_files(GENERAL_DATA_DIR)
