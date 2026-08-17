"""
AnydocParser Service (Firecrawl Anydoc Rust Integration)
Converts .docx, .pptx, .xlsx, .pdf, .csv, .odt, .rtf documents into GitHub-Flavored Markdown (GFM).
"""

import os
import shutil
import subprocess
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AnydocParser:
    """
    High-performance document parser wrapping Firecrawl's anydoc Rust binary.
    Executes 100% on-device with zero external API calls.
    """

    SUPPORTED_EXTENSIONS = {
        '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls',
        '.pdf', '.rtf', '.odt', '.ods', '.odp', '.epub', '.csv'
    }

    def __init__(self):
        self._anydoc_bin = self._find_anydoc_binary()

    def _find_anydoc_binary(self) -> Optional[str]:
        """Locates the anydoc executable on the local system."""
        # 1. Check PATH
        bin_path = shutil.which("anydoc")
        if bin_path:
            return bin_path

        # 2. Check ~/.local/bin/anydoc
        user_local = os.path.expanduser("~/.local/bin/anydoc")
        if os.path.isfile(user_local) and os.access(user_local, os.X_OK):
            return user_local

        # 3. Check npx availability
        if shutil.which("npx"):
            return "npx"

        return None

    def is_supported(self, filepath: str) -> bool:
        """Checks if the file extension is natively supported by anydoc."""
        ext = os.path.splitext(filepath)[1].lower()
        return ext in self.SUPPORTED_EXTENSIONS

    def parse(self, filepath: str, format_hint: Optional[str] = None, timeout: int = 15) -> Dict[str, Any]:
        """
        Parses a document file and returns standard GitHub-Flavored Markdown.
        
        Returns:
            dict with {
                "success": bool,
                "markdown": str,
                "elapsed_ms": float,
                "scanned_or_unsupported": bool,
                "error": Optional[str]
            }
        """
        if not os.path.exists(filepath):
            return {
                "success": False,
                "markdown": "",
                "elapsed_ms": 0.0,
                "scanned_or_unsupported": False,
                "error": f"File not found: {filepath}"
            }

        start_time = time.perf_counter()
        ext = os.path.splitext(filepath)[1].lower().lstrip('.')
        fmt = format_hint or ext

        # Build command
        if self._anydoc_bin and self._anydoc_bin != "npx":
            cmd = [self._anydoc_bin, filepath]
            if format_hint:
                cmd.extend(["-f", format_hint])
        else:
            # Fallback to npx -y @firecrawl/anydoc
            cmd = ["npx", "-y", "@firecrawl/anydoc", filepath]
            if format_hint:
                cmd.extend(["-f", format_hint])

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace"
            )

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            if result.returncode == 0:
                markdown = result.stdout
                return {
                    "success": True,
                    "markdown": markdown,
                    "elapsed_ms": round(elapsed_ms, 2),
                    "scanned_or_unsupported": False,
                    "error": None
                }
            else:
                stderr_msg = result.stderr.strip()
                is_scanned = "OCR" in stderr_msg or "unsupported" in stderr_msg.lower()
                logger.warning(f"Anydoc exited with code {result.returncode} for {filepath}: {stderr_msg}")
                return {
                    "success": False,
                    "markdown": "",
                    "elapsed_ms": round(elapsed_ms, 2),
                    "scanned_or_unsupported": is_scanned,
                    "error": stderr_msg or f"Anydoc failed with exit code {result.returncode}"
                }
        except subprocess.TimeoutExpired:
            logger.error(f"Anydoc parse timed out ({timeout}s) for {filepath}")
            return {
                "success": False,
                "markdown": "",
                "elapsed_ms": timeout * 1000.0,
                "scanned_or_unsupported": False,
                "error": "Parsing timeout expired"
            }
        except Exception as e:
            logger.error(f"Anydoc execution failed for {filepath}: {e}")
            return {
                "success": False,
                "markdown": "",
                "elapsed_ms": 0.0,
                "scanned_or_unsupported": False,
                "error": str(e)
            }


# Global singleton instance
anydoc_parser = AnydocParser()
