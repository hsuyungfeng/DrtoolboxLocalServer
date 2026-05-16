import os
from dotenv import load_dotenv

load_dotenv()

MODEL_PATH = os.getenv("MODEL_PATH", "/home/hsu/models/gemma-4-27b.gguf")
SPECIAL_DATA_DIR = os.getenv("SPECIAL_DATA_DIR", "/media/hsu/软件/行銷圖文檔案整理")
GENERAL_DATA_DIR = os.getenv("GENERAL_DATA_DIR", "./documents/general")
LOG_DIR = os.getenv("LOG_DIR", "./data")
