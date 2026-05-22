import os
import sys
import random
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.llm_server import llm_instance
from config.settings import SPECIAL_DATA_DIR

files = [f for f in os.listdir(SPECIAL_DATA_DIR) if f.endswith('.txt')]
print(f"Total txt files: {len(files)}")
if files:
    sample = random.sample(files, min(len(files), 10))
    for s in sample:
        with open(os.path.join(SPECIAL_DATA_DIR, s), 'r') as f:
            content = f.read(500)
            print(f"--- File: {s} ---")
            print(content[:100])
