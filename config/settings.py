import os
from dotenv import load_dotenv

load_dotenv()

MODEL_PATH = os.getenv("MODEL_PATH", "/home/hsu/models/google_gemma-4-26B-A4B-it-Q3_K_L.gguf")
LOG_DIR = os.getenv("LOG_DIR", "./data")

# Setup safe local fallback directories under the fully writable './data/' directory
LOCAL_FALLBACK_SPECIAL = "./data/documents/special"
LOCAL_FALLBACK_GENERAL = "./data/documents/general"

# Preferred paths from environment
PREFERRED_SPECIAL_DIR = os.getenv("SPECIAL_DATA_DIR", "/media/hsu/软件/行銷圖文檔案整理")
PREFERRED_GENERAL_DIR = os.getenv("GENERAL_DATA_DIR", "./documents/general")

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

