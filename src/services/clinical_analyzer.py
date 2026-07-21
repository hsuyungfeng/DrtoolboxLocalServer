import os
import sqlite3
import pandas as pd
import ehrapy as ep
import logging
import json
from datetime import datetime
from config.settings import DATA_DIR

logger = logging.getLogger(__name__)

class ClinicalAnalyzer:
    def __init__(self):
        self.db_path = os.path.join(DATA_DIR, 'db', 'clinic.db')
        self.output_dir = os.path.join(DATA_DIR, 'analytics')
        os.makedirs(self.output_dir, exist_ok=True)

    def extract_and_analyze(self):
        """Extract patient data and perform deep phenotyping with ehrapy."""
        logger.info("Starting ehrapy clinical analysis...")
        
        if not os.path.exists(self.db_path):
            logger.error(f"Database not found at {self.db_path}")
            return None

        try:
            # 1. Load Data
            conn = sqlite3.connect(self.db_path)
            query = "SELECT patient_id, dob, medical_history, allergies FROM patients"
            df = pd.read_sql_query(query, conn)
            conn.close()

            if df.empty:
                logger.warning("No patient data found for analysis.")
                return None

            # 2. Preprocessing
            df['dob'] = pd.to_datetime(df['dob'], errors='coerce')
            df['age'] = datetime.now().year - df['dob'].dt.year
            df = df[df['age'].notnull()]
            
            # Age Buckets for Chart.js
            age_bins = [0, 20, 30, 40, 50, 60, 100]
            age_labels = ['<20', '20-30', '30-40', '40-50', '50-60', '60+']
            df['age_group'] = pd.cut(df['age'], bins=age_bins, labels=age_labels)
            age_dist = df['age_group'].value_counts().to_dict()

            # 3. ehrapy specific analysis (Preprocessing & Clustering)
            if len(df) >= 3: # Lowered threshold for pilot testing
                try:
                    import anndata as ad
                    # Ensure numeric data for ehrapy
                    analysis_df = df[['age']].copy()
                    adata = ad.AnnData(X=analysis_df.values.astype('float32'), obs=df[['patient_id']].astype(str))
                    adata.var_names = ['age']
                    
                    # ehrapy pipeline
                    ep.pp.scale_norm(adata)
                    ep.pp.pca(adata)
                    ep.pp.neighbors(adata, n_neighbors=min(len(df)-1, 15))
                    ep.tl.leiden(adata, resolution=0.5)
                    
                    logger.info(f"Deep clustering complete. Found {len(adata.obs['leiden'].unique())} phenotypes.")
                except Exception as inner_e:
                    logger.warning(f"Deep clustering skipped: {inner_e}")
            
            # 4. Save Insights
            knowledge_gaps = self._analyze_knowledge_gaps()
            insight_file = os.path.join(self.output_dir, f"clinical_insights_{datetime.now().strftime('%Y%m%d')}.json")
            
            # Handle NaN for avg_age
            avg_age = float(df['age'].mean()) if not df['age'].empty else 0
            if pd.isna(avg_age): avg_age = 0

            icd10_risks = self._analyze_icd10_risks(df)

            summary = {
                "total_patients": len(df),
                "avg_age": avg_age,
                "age_distribution": {
                    "labels": list(age_dist.keys()),
                    "values": [int(v) for v in age_dist.values()]
                },
                "knowledge_gaps": knowledge_gaps,
                "icd10_risks": icd10_risks,
                "timestamp": datetime.now().isoformat(),
                "insights": self._generate_text_insights(df)
            }
            
            with open(insight_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=4)
                
            return summary

        except Exception as e:
            logger.error(f"Ehrapy analysis failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _analyze_knowledge_gaps(self):
        """Analyzes recent logs to find topics with low AI confidence."""
        gaps = {}
        
        # 1. Check database for low confidence conversations
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Find patient messages with low confidence RAG responses
            query = """
                SELECT text FROM patient_conversations 
                WHERE sender = 'patient' AND rag_confidence < 0.65 
                ORDER BY timestamp DESC LIMIT 100
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            logger.info(f"Found {len(rows)} low-confidence messages in DB.")
            for (text,) in rows:
                # Heuristic: Extract first 3 words or 5 Chinese characters as topic
                words = text.split()
                if words and any(ord(c) > 127 for c in words[0]): # Likely Chinese
                    topic = text[:5]
                else:
                    topic = " ".join(words[:3])
                gaps[topic] = gaps.get(topic, 0) + 1
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to query knowledge gaps from DB: {e}")

        # 2. Legacy: Check last 3 days of JSONL logs
        import glob
        log_files = glob.glob(os.path.join(DATA_DIR, "interactions_*.jsonl"))
        
        for log_file in log_files[-3:]:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        entry = json.loads(line)
                        meta = entry.get('metadata', {})
                        conf = meta.get('confidence_score', 100)
                        if conf < 65:
                            topic = " ".join(entry['messages'][0]['content'].split()[:3])
                            gaps[topic] = gaps.get(topic, 0) + 1
            except: continue
            
        # Return top 5 gaps
        sorted_gaps = sorted(gaps.items(), key=lambda x: x[1], reverse=True)
        return [{"topic": k, "count": v} for k, v in sorted_gaps[:5]]

    def _generate_text_insights(self, df):
        """Heuristic text insights for PageIndex backflow."""
        insights = []
        
        # High-risk age group detection
        elderly = df[df['age'] > 65]
        if not elderly.empty:
            insights.append(f"本院有 {len(elderly)} 名 65 歲以上病患，建議針對高齡族群加強慢性病管理衛教。")
            
        # Keyword based history analysis
        diabetes_count = df['medical_history'].str.contains('糖尿病|血糖', na=False).sum()
        if diabetes_count > 0:
            insights.append(f"偵測到 {diabetes_count} 名病患具備糖尿病史，已將相關專業衛教優先級調高。")

        return insights

    def _analyze_icd10_risks(self, df):
        """Map medical history to high-risk ICD-10 categories and fetch medical knowledge."""
        try:
            # Map traditional kw to (code_prefix, simplified_kw_for_kg)
            risk_keywords = {
                '糖尿病': ('E11', '糖尿病'), 
                '高血壓': ('I10', '高血压'), 
                '心臟病': ('I51', '心脏病'), 
                '氣喘': ('J45', '哮喘'), 
                '憂鬱症': ('F32', '抑郁症')
            }
            risk_counts = {}
            risk_knowledge = {}
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for kw, (code_prefix, sc_kw) in risk_keywords.items():
                count = df['medical_history'].str.contains(kw, na=False).sum()
                if count > 0:
                    cursor.execute("SELECT name_cn FROM icd10_codes WHERE code LIKE ? LIMIT 1", (f'{code_prefix}%',))
                    row = cursor.fetchone()
                    name = row[0] if row else kw
                    key = f"{code_prefix} ({name})"
                    risk_counts[key] = int(count)
                    
                    # Fetch extra knowledge using Simplified Chinese keyword
                    cursor.execute("SELECT name, common_drug, check_items, do_eat, not_eat FROM disease_knowledge WHERE name LIKE ? LIMIT 1", (f'%{sc_kw}%',))
                    k_row = cursor.fetchone()
                    if k_row:
                        try:
                            import json
                            cd = json.loads(k_row[1]) if k_row[1] else []
                            ci = json.loads(k_row[2]) if k_row[2] else []
                            de = json.loads(k_row[3]) if k_row[3] else []
                            ne = json.loads(k_row[4]) if k_row[4] else []
                        except:
                            cd, ci, de, ne = [], [], [], []
                        
                        risk_knowledge[key] = {
                            "name": k_row[0],
                            "drugs": cd[:3] if isinstance(cd, list) else [],
                            "checks": ci[:3] if isinstance(ci, list) else [],
                            "do_eat": de[:3] if isinstance(de, list) else [],
                            "not_eat": ne[:3] if isinstance(ne, list) else []
                        }
                    
            conn.close()
            return {
                "labels": list(risk_counts.keys()),
                "values": list(risk_counts.values()),
                "knowledge": risk_knowledge
            }
        except Exception as e:
            logger.error(f"ICD-10 Risk Analysis failed: {e}")
            return {"labels": [], "values": [], "knowledge": {}}

clinical_analyzer = ClinicalAnalyzer()
