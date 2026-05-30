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
                    ep.pp.scale(adata)
                    ep.tl.pca(adata)
                    ep.pp.neighbors(adata, n_neighbors=min(len(df)-1, 15))
                    ep.tl.leiden(adata, resolution=0.5)
                    
                    logger.info(f"Deep clustering complete. Found {len(adata.obs['leiden'].unique())} phenotypes.")
                except Exception as inner_e:
                    logger.warning(f"Deep clustering skipped: {inner_e}")
            
            # 4. Save Insights
            insight_file = os.path.join(self.output_dir, f"clinical_insights_{datetime.now().strftime('%Y%m%d')}.json")
            
            # Handle NaN for avg_age
            avg_age = float(df['age'].mean()) if not df['age'].empty else 0
            if pd.isna(avg_age): avg_age = 0

            summary = {
                "total_patients": len(df),
                "avg_age": avg_age,
                "age_distribution": {
                    "labels": list(age_dist.keys()),
                    "values": [int(v) for v in age_dist.values()]
                },
                "knowledge_gaps": knowledge_gaps,
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
        import glob
        gaps = {}
        log_files = glob.glob(os.path.join(DATA_DIR, "interactions_*.jsonl"))
        
        for log_file in log_files[-3:]: # Check last 3 days
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        entry = json.loads(line)
                        meta = entry.get('metadata', {})
                        conf = meta.get('confidence_score', 100)
                        if conf < 65:
                            # Heuristic: Extract first 3 words as topic
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

clinical_analyzer = ClinicalAnalyzer()
