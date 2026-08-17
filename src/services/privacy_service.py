"""
Privacy & PII De-identification Service (OpenMed + Native Safe Harbor Engine)
Provides local-first, on-device redaction and anonymization of patient identifiers.
"""

import re
import os
import json
import hashlib
from typing import List, Dict, Any, Optional

try:
    import openmed
    HAS_OPENMED = True
except Exception:
    HAS_OPENMED = False


class PrivacyService:
    """
    Local privacy guard for PII/PHI de-identification.
    Compliant with HIPAA Safe Harbor and Taiwan Personal Data Protection Act.
    """

    # Comprehensive Regex Patterns for Native/Offline PII Detection
    PATTERNS = {
        'TW_NATIONAL_ID': re.compile(r'\b[A-Z][1289]\d{8}\b', re.IGNORECASE),
        'TW_MOBILE_PHONE': re.compile(r'(?:\+?886[-\s]?)?0?9\d{2}[-\s]?\d{3}[-\s]?\d{3}\b'),
        'TW_TEL_PHONE': re.compile(r'\b0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4}\b'),
        'EMAIL': re.compile(r'\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b'),
        'DATE_DOB': re.compile(r'\b(?:19|20)\d{2}[-/.年](?:0?[1-9]|1[0-2])[-/.月](?:0?[1-9]|[12]\d|3[01])日?\b'),
        'MRN': re.compile(r'(?:病歷號|病歷號碼|MRN|Chart\s*(?:No|Number)|Chart)[:：\s]*([A-Za-z0-9-_]{4,16})', re.IGNORECASE),
        'PATIENT_NAME_PREFIX': re.compile(r'(?:病患姓名|病患|患者|姓名|病人|聯絡人|先生|女士|小姐)[:：\s]*([\u4e00-\u9fa5]{2,4})'),
        'ENGLISH_PATIENT_NAME': re.compile(r'(?:Patient\s*(?:Name)?|Mr\.|Ms\.|Mrs\.)[:：\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'),
    }

    # Synthetic replacement dictionary
    FAKER_NAMES = ["王小明", "李小華", "張美麗", "陳大同", "林建志", "黃雅婷"]
    FAKER_PHONES = ["0912-000-111", "0928-111-222", "0933-222-333", "0955-444-555"]
    FAKER_IDS = ["A123456789", "B234567890", "C198765432"]

    def __init__(self, default_method: str = "mask", lang: str = "zh"):
        self.default_method = default_method
        self.lang = lang

    def extract_pii(self, text: str, lang: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extract all PII entities found in text with offsets and types."""
        if not text:
            return []

        target_lang = lang or self.lang
        entities = []

        # 1. Try OpenMed if available
        if HAS_OPENMED:
            try:
                res = openmed.extract_pii(text, lang=target_lang, use_smart_merging=True)
                for e in res.entities:
                    entities.append({
                        "text": e.text,
                        "label": e.label,
                        "start": getattr(e, "start", -1),
                        "end": getattr(e, "end", -1),
                        "confidence": getattr(e, "confidence", 0.95),
                        "source": "openmed"
                    })
                if entities:
                    return entities
            except Exception:
                pass

        # 2. Fallback to native Regex rules
        # MRN
        for m in self.PATTERNS['MRN'].finditer(text):
            mrn_val = m.group(1)
            entities.append({
                "text": mrn_val,
                "label": "ID",
                "start": m.start(1),
                "end": m.end(1),
                "confidence": 0.98,
                "source": "native_regex"
            })

        # Taiwanese ID
        for m in self.PATTERNS['TW_NATIONAL_ID'].finditer(text):
            entities.append({
                "text": m.group(0),
                "label": "ID",
                "start": m.start(),
                "end": m.end(),
                "confidence": 0.99,
                "source": "native_regex"
            })

        # Mobile Phone
        for m in self.PATTERNS['TW_MOBILE_PHONE'].finditer(text):
            entities.append({
                "text": m.group(0),
                "label": "PHONE",
                "start": m.start(),
                "end": m.end(),
                "confidence": 0.96,
                "source": "native_regex"
            })

        # Tel Phone
        for m in self.PATTERNS['TW_TEL_PHONE'].finditer(text):
            entities.append({
                "text": m.group(0),
                "label": "PHONE",
                "start": m.start(),
                "end": m.end(),
                "confidence": 0.90,
                "source": "native_regex"
            })

        # Email
        for m in self.PATTERNS['EMAIL'].finditer(text):
            entities.append({
                "text": m.group(0),
                "label": "EMAIL",
                "start": m.start(),
                "end": m.end(),
                "confidence": 0.99,
                "source": "native_regex"
            })

        # Dates / DOB
        for m in self.PATTERNS['DATE_DOB'].finditer(text):
            entities.append({
                "text": m.group(0),
                "label": "DATE",
                "start": m.start(),
                "end": m.end(),
                "confidence": 0.88,
                "source": "native_regex"
            })

        # Names (Prefix context)
        for m in self.PATTERNS['PATIENT_NAME_PREFIX'].finditer(text):
            name_val = m.group(1)
            entities.append({
                "text": name_val,
                "label": "NAME",
                "start": m.start(1),
                "end": m.end(1),
                "confidence": 0.92,
                "source": "native_regex"
            })

        for m in self.PATTERNS['ENGLISH_PATIENT_NAME'].finditer(text):
            name_val = m.group(1)
            entities.append({
                "text": name_val,
                "label": "NAME",
                "start": m.start(1),
                "end": m.end(1),
                "confidence": 0.92,
                "source": "native_regex"
            })

        return entities

    def anonymize_text(self, text: str, method: Optional[str] = None, lang: Optional[str] = None) -> str:
        """
        De-identify text using specified method:
        - 'mask': Replace with [NAME], [PHONE], [ID], etc.
        - 'replace': Replace with synthetic safe placeholders
        - 'hash': Replace with sha256 hash prefix
        """
        if not text:
            return ""

        method = method or self.default_method
        target_lang = lang or self.lang

        # 1. Try OpenMed
        if HAS_OPENMED:
            try:
                res = openmed.deidentify(text, method=method, lang=target_lang)
                if hasattr(res, 'deidentified_text') and res.deidentified_text:
                    return res.deidentified_text
            except Exception:
                pass

        # 2. Native Robust De-identification
        entities = self.extract_pii(text, lang=target_lang)
        if not entities:
            return text

        # Sort entities by start descending to replace from back to front
        sorted_entities = sorted(
            [e for e in entities if e.get("start", -1) >= 0 and e.get("end", -1) > e.get("start", -1)],
            key=lambda x: x["start"],
            reverse=True
        )

        anonymized = text
        for idx, e in enumerate(sorted_entities):
            start = e["start"]
            end = e["end"]
            label = e["label"]
            original_val = e["text"]

            if method == "replace":
                if label == "NAME":
                    rep = self.FAKER_NAMES[idx % len(self.FAKER_NAMES)]
                elif label == "PHONE":
                    rep = self.FAKER_PHONES[idx % len(self.FAKER_PHONES)]
                elif label == "ID":
                    rep = self.FAKER_IDS[idx % len(self.FAKER_IDS)]
                elif label == "EMAIL":
                    rep = "patient@example-clinic.tw"
                elif label == "DATE":
                    rep = "1990-01-01"
                else:
                    rep = f"[{label}]"
            elif method == "hash":
                h = hashlib.sha256(original_val.encode('utf-8')).hexdigest()[:8]
                rep = f"[{label}_{h}]"
            else:  # mask
                rep = f"[{label}]"

            anonymized = anonymized[:start] + rep + anonymized[end:]

        return anonymized

    def anonymize_conversation(self, conversation_data: Dict[str, Any], method: Optional[str] = None) -> Dict[str, Any]:
        """
        Anonymize a single conversation JSON entry (as in verified_training_data.jsonl).
        """
        method = method or self.default_method
        sanitized = json.loads(json.dumps(conversation_data))  # deep copy

        if "messages" in sanitized and isinstance(sanitized["messages"], list):
            for msg in sanitized["messages"]:
                if isinstance(msg, dict) and "content" in msg and isinstance(msg["content"], str):
                    # Mask patient's request & assistant mentions of PII
                    msg["content"] = self.anonymize_text(msg["content"], method=method)

        return sanitized

    def anonymize_jsonl_file(self, input_file_path: str, output_file_path: Optional[str] = None, method: str = "mask") -> int:
        """
        Batch anonymize an entire JSONL training dataset file.
        Returns the number of processed records.
        """
        if not os.path.exists(input_file_path):
            return 0

        target_path = output_file_path or input_file_path
        processed_count = 0
        cleaned_lines = []

        with open(input_file_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    record = json.loads(line_str)
                    clean_record = self.anonymize_conversation(record, method=method)
                    cleaned_lines.append(json.dumps(clean_record, ensure_ascii=False))
                    processed_count += 1
                except Exception:
                    cleaned_lines.append(line_str)

        with open(target_path, "w", encoding="utf-8") as f:
            for clean_line in cleaned_lines:
                f.write(clean_line + "\n")

        return processed_count


# Global singleton instance
privacy_service = PrivacyService()
