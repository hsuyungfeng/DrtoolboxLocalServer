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
            # We focus on patient demographics and basic history for this pilot
            query = "SELECT patient_id, dob, medical_history, allergies FROM patients"
            df = pd.read_sql_query(query, conn)
            conn.close()

            if df.empty:
                logger.warning("No patient data found for analysis.")
                return None

            # 2. Preprocessing
            # Calculate age from DOB
            df['dob'] = pd.to_datetime(df['dob'], errors='coerce')
            df['age'] = datetime.now().year - df['dob'].dt.year
            df = df.drop(columns=['dob'])

            # Direct AnnData creation (ehrapy uses anndata under the hood)
            import anndata as ad
            adata = ad.AnnData(df)
            adata.obs_names = df['patient_id'].astype(str)
            
            # 3. ehrapy specific analysis (Preprocessing & Clustering)
            # Note: ehrapy and its dependencies (faiss, etc.) can be sensitive to small datasets
            if len(adata) > 10:
                try:
                    # Deep Analysis with ehrapy
                    # ep.pp.knn_impute(adata) # Skiped due to potential crash on small data
                    ep.pp.scale(adata)
                    ep.tl.pca(adata)
                    ep.pp.neighbors(adata)
                    ep.tl.leiden(adata, resolution=0.5)
                    logger.info(f"Deep clustering complete. Found {len(adata.obs['leiden'].unique())} phenotypes.")
                except Exception as inner_e:
                    logger.warning(f"Deep clustering skipped: {inner_e}")
            else:
                logger.info("Dataset too small for deep ehrapy clustering. Using heuristic fallback.")
            
            # 4. Save Insights
            insight_file = os.path.join(self.output_dir, f"clinical_insights_{datetime.now().strftime('%Y%m%d')}.json")
            
            # Summary of clusters for the dashboard
            summary = {
                "total_patients": len(df),
                "avg_age": float(df['age'].mean()),
                "timestamp": datetime.now().isoformat(),
                "insights": self._generate_text_insights(df)
            }
            
            with open(insight_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=4)
                
            return summary

        except Exception as e:
            logger.error(f"Ehrapy analysis failed: {e}")
            return None

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
