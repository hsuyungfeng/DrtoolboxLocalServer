"""Shared pytest fixtures for the DrtoolboxLocalServer test suite.

Ensures the project root is importable (`import src...`) regardless of
how pytest is invoked (single file, directory, or full run).
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
