"""
Clinical Named Entity Recognition (NER) Service (OpenMed + Hybrid KG Extractor)
Extracts structured medical entities (Diseases, Drugs, Dosages, Symptoms, Frequencies) on-device.
"""

import re
import os
import sqlite3
from typing import List, Dict, Any, Optional

try:
    import openmed
    HAS_OPENMED = True
except Exception:
    HAS_OPENMED = False


class ClinicalNER:
    """
    Local-first Clinical NER engine.
    Extracts Disease, Drug, Dosage, Frequency, and Symptom entities from clinical text and voice transcripts.
    """

    DOSAGE_PATTERN = re.compile(r'\b\d+(?:\.\d+)?\s*(?:mg|g|mcg|ml|cc|IU|units?|顆|錠|包|支|毫克|毫升|單位)\b', re.IGNORECASE)
    FREQUENCY_PATTERN = re.compile(r'\b(?:qd|bid|tid|qid|q4h|q6h|q8h|q12h|prn|hs|stat|po|iv|im|sc|ac|pc)\b', re.IGNORECASE)
    SYMPTOM_PATTERN = re.compile(
        r'(?:發燒|頭痛|胸痛|咳嗽|喉嚨痛|紅腫|發炎|噁心|嘔吐|腹瀉|便秘|頭暈|發癢|過敏|出血|痛風|水腫|麻木|呼吸困難|fever|cough|pain|swelling|nausea|vomiting|dizziness|headache|rash|edema)',
        re.IGNORECASE
    )

    def __init__(self, db_dir: Optional[str] = None):
        if db_dir:
            self.db_dir = db_dir
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.db_dir = os.path.join(base_dir, "data", "db")

        self.clinic_db_path = os.path.join(self.db_dir, "clinic.db")
        self.medical_db_path = os.path.join(self.db_dir, "medical.db")
        self._cached_drugs = set()
        self._cached_diseases = set()
        self._load_local_vocab()

    def _load_local_vocab(self):
        """Loads drug names, OTC brand names, and disease terminology from local SQLite DBs."""
        # 1. Load from clinic.db
        if os.path.exists(self.clinic_db_path):
            try:
                conn = sqlite3.connect(self.clinic_db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='drugs'")
                if cursor.fetchone():
                    cursor.execute("SELECT name, generic_name, otc_name FROM drugs")
                    for row in cursor.fetchall():
                        for val in row:
                            if val and len(val.strip()) >= 2:
                                self._cached_drugs.add(val.strip())
                conn.close()
            except Exception:
                pass

        # 2. Load common aesthetic & clinical procedures/drugs
        default_drugs = [
            "普拿疼", "Acetaminophen", "Paracetamol", "Ibuprofen", "Saxenda", "善纖達",
            "Botox", "保妥適", "Dysport", "皇家肉毒", "Xeomin", "天使肉毒", "Jeuveau",
            "Ellanse", "洢蓮絲", "伊妍仕", "Hyaluronic Acid", "玻尿酸", "喬雅登", "Juvederm",
            "Restylane", "瑞絲朗", "Belotero", "水微晶", "皮秒雷射", "Picosecond Laser",
            "EMFACE", "鳳凰電波", "Thermage", "音波拉皮", "Ulthera", "肉毒桿菌", "肉毒桿菌素",
            "Amoxicillin", "Augmentin", "Keflex", "Diclofenac", "Cataflam", "Clopidogrel",
            "Metformin", "Amlodipine", "Losartan", "Empagliflozin", "Colchicine", "Allopurinol"
        ]
        self._cached_drugs.update(default_drugs)

        # 3. Load from medical.db diseases
        if os.path.exists(self.medical_db_path):
            try:
                conn = sqlite3.connect(self.medical_db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='diseases'")
                if cursor.fetchone():
                    cursor.execute("SELECT name, chinese_name FROM diseases LIMIT 500")
                    for row in cursor.fetchall():
                        for val in row:
                            if val and len(val.strip()) >= 2:
                                self._cached_diseases.add(val.strip())
                conn.close()
            except Exception:
                pass

        default_diseases = [
            "糖尿病", "高血壓", "高血脂", "痛風", "骨髓炎", "蜂窩性組織炎", "肝硬化", "脂肪肝",
            "蜘蛛痣", "過敏性鼻炎", "濕疹", "蕁麻疹", "肌腱炎", "腱鞘囊腫", "脂漏性皮膚炎", "黃疸",
            "Diabetes", "Hypertension", "Gout", "Osteomyelitis", "Cellulitis", "Dermatitis",
            "NSTEMI", "STEMI", "Coronary Artery Disease", "Hyperlipidemia"
        ]
        self._cached_diseases.update(default_diseases)

    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract clinical entities from text.
        Returns a list of dicts with: text, label, confidence, start, end.
        """
        if not text:
            return []

        entities = []
        found_spans = set()

        # 1. Try OpenMed if available
        if HAS_OPENMED:
            try:
                res = openmed.analyze_text(text, model_name="pharma_detection_superclinical")
                for e in getattr(res, "entities", []):
                    span_key = (getattr(e, "start", -1), getattr(e, "end", -1))
                    found_spans.add(span_key)
                    entities.append({
                        "text": e.text,
                        "label": e.label,
                        "confidence": getattr(e, "confidence", 0.95),
                        "start": getattr(e, "start", -1),
                        "end": getattr(e, "end", -1),
                        "source": "openmed"
                    })
            except Exception:
                pass

        # 2. Local Hybrid Vocabulary Matching
        # Drugs
        for drug in self._cached_drugs:
            pattern = re.compile(re.escape(drug), re.IGNORECASE)
            for m in pattern.finditer(text):
                span = (m.start(), m.end())
                if span not in found_spans:
                    found_spans.add(span)
                    entities.append({
                        "text": m.group(0),
                        "label": "DRUG",
                        "confidence": 0.96,
                        "start": m.start(),
                        "end": m.end(),
                        "source": "hybrid_kg"
                    })

        # Diseases
        for disease in self._cached_diseases:
            pattern = re.compile(re.escape(disease), re.IGNORECASE)
            for m in pattern.finditer(text):
                span = (m.start(), m.end())
                if span not in found_spans:
                    found_spans.add(span)
                    entities.append({
                        "text": m.group(0),
                        "label": "DISEASE",
                        "confidence": 0.95,
                        "start": m.start(),
                        "end": m.end(),
                        "source": "hybrid_kg"
                    })

        # Dosages
        for m in self.DOSAGE_PATTERN.finditer(text):
            span = (m.start(), m.end())
            if span not in found_spans:
                found_spans.add(span)
                entities.append({
                    "text": m.group(0),
                    "label": "DOSAGE",
                    "confidence": 0.98,
                    "start": m.start(),
                    "end": m.end(),
                    "source": "regex"
                })

        # Frequencies
        for m in self.FREQUENCY_PATTERN.finditer(text):
            span = (m.start(), m.end())
            if span not in found_spans:
                found_spans.add(span)
                entities.append({
                    "text": m.group(0),
                    "label": "FREQUENCY",
                    "confidence": 0.94,
                    "start": m.start(),
                    "end": m.end(),
                    "source": "regex"
                })

        # Symptoms
        for m in self.SYMPTOM_PATTERN.finditer(text):
            span = (m.start(), m.end())
            if span not in found_spans:
                found_spans.add(span)
                entities.append({
                    "text": m.group(0),
                    "label": "SYMPTOM",
                    "confidence": 0.92,
                    "start": m.start(),
                    "end": m.end(),
                    "source": "regex"
                })

        # Sort by start offset
        entities.sort(key=lambda x: x.get("start", 0))
        return entities

    def summarize_clinical_tags(self, text: str) -> Dict[str, List[str]]:
        """
        Groups extracted entities by category for easy display in SOAP Lab & RAG.
        """
        entities = self.extract_entities(text)
        summary = {
            "diseases": [],
            "drugs": [],
            "dosages": [],
            "symptoms": [],
            "frequencies": []
        }
        for e in entities:
            label = e.get("label", "").upper()
            val = e.get("text", "").strip()
            if label in ("DISEASE", "CONDITION") and val not in summary["diseases"]:
                summary["diseases"].append(val)
            elif label in ("DRUG", "MEDICATION") and val not in summary["drugs"]:
                summary["drugs"].append(val)
            elif label == "DOSAGE" and val not in summary["dosages"]:
                summary["dosages"].append(val)
            elif label == "SYMPTOM" and val not in summary["symptoms"]:
                summary["symptoms"].append(val)
            elif label == "FREQUENCY" and val not in summary["frequencies"]:
                summary["frequencies"].append(val)
        return summary


# Global singleton instance
clinical_ner = ClinicalNER()
