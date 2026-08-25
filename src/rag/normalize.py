"""
Simplified-to-Traditional Chinese normalization module using OpenCC.
Taiwan phrase-level substitution (s2twp) is used to align with local clinic vocabulary.
"""

import logging

logger = logging.getLogger(__name__)

try:
    from opencc import OpenCC
    _converter = OpenCC('s2twp')
except ImportError:
    _converter = None
    logger.warning("opencc is not installed; text normalization to Traditional Chinese will be disabled.")


def normalize_to_traditional(text: str) -> str:
    """
    Convert text from Simplified Chinese to Traditional Chinese (Taiwan phrasing).
    If conversion fails or OpenCC is unavailable, returns original text without raising.

    Args:
        text: Input string.

    Returns:
        Converted Traditional Chinese string or original text on error/empty.
    """
    if not text:
        return text

    if _converter is None:
        return text

    try:
        return _converter.convert(text)
    except Exception as e:
        logger.warning(f"OpenCC normalization failed, using raw text: {e}")
        return text
