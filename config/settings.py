import os
from dotenv import load_dotenv

load_dotenv()

# Get the project root directory (one level up from the 'config' folder)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

MODEL_PATH = os.getenv("MODEL_PATH", os.path.join(PROJECT_ROOT, "data/models/qwen-3.6-7b-it.gguf"))
LOG_DIR = os.getenv("LOG_DIR", os.path.join(PROJECT_ROOT, "data"))
DATA_DIR = os.getenv("DATA_DIR", os.path.join(PROJECT_ROOT, "data"))

# Setup safe local fallback directories under the fully writable './data/' directory
LOCAL_FALLBACK_SPECIAL = os.path.join(PROJECT_ROOT, "data/documents/special")
LOCAL_FALLBACK_GENERAL = os.path.join(PROJECT_ROOT, "data/documents/general")

# Preferred paths from environment (Default to local project directories for deployment portability)
PREFERRED_SPECIAL_DIR = os.getenv("SPECIAL_DATA_DIR", LOCAL_FALLBACK_SPECIAL)
PREFERRED_GENERAL_DIR = os.getenv("GENERAL_DATA_DIR", LOCAL_FALLBACK_GENERAL)

def get_writable_dir(preferred_path, fallback_path):
    try:
        os.makedirs(preferred_path, exist_ok=True)
        # Test write permissions by writing a temporary hidden file
        test_file = os.path.join(preferred_path, '.write_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        return preferred_path
    except (OSError, PermissionError):
        # Graceful fallback to fully writable local folder under ./data/
        os.makedirs(fallback_path, exist_ok=True)
        return fallback_path

SPECIAL_DATA_DIR = get_writable_dir(PREFERRED_SPECIAL_DIR, LOCAL_FALLBACK_SPECIAL)
GENERAL_DATA_DIR = get_writable_dir(PREFERRED_GENERAL_DIR, LOCAL_FALLBACK_GENERAL)

