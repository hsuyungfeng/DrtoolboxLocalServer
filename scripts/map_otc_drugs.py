import os
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'db', 'clinic.db')

# Mapping of English chemical ingredients to localized OTC/common names
OTC_MAPPING = {
    "ACETAMINOPHEN": "普拿疼 (退燒止痛藥)",
    "IBUPROFEN": "布洛芬 (消炎止痛藥)",
    "DICLOFENAC": "強效消炎止痛藥",
    "NAPROXEN": "長效消炎止痛藥",
    "MEFENAMIC ACID": "經痛/牙痛止痛藥",
    
    "AMOXICILLIN": "安莫西林 (常見抗生素)",
    "CEPHALEXIN": "頭孢菌素 (抗生素)",
    "AZITHROMYCIN": "阿奇黴素 (長效抗生素)",
    "LEVOFLOXACIN": "左氧氟沙星 (廣效抗生素)",
    
    "CETIRIZINE": "驅敏 (第二代抗組織胺/過敏藥)",
    "LORATADINE": "柔沛 (抗過敏藥)",
    "FEXOFENADINE": "艾來 (抗敏藥/不嗜睡)",
    "CHLORPHENIRAMINE": "第一代抗過敏藥 (會嗜睡)",
    "PSEUDOEPHEDRINE": "偽麻黃鹼 (鼻塞解除劑)",
    
    "LOPERAMIDE": "樂必寧 (強效止瀉藥)",
    "SMECTITE": "思密達 (腸胃吸附止瀉劑)",
    "METOCLOPRAMIDE": "止吐藥",
    "DOMPERIDONE": "表飛鳴 (止吐/促進腸胃蠕動)",
    
    "PANTOPRAZOLE": "胃潰瘍藥 (PPI 質子幫浦抑制劑)",
    "ESOMEPRAZOLE": "耐適恩 (強效胃藥)",
    "LANSOPRAZOLE": "泰克胃通 (胃潰瘍藥)",
    "FAMOTIDINE": "法莫替丁 (一般胃酸抑制劑)",
    "MAGNESIUM OXIDE": "氧化鎂 (軟便劑/胃藥)",
    "ALUMINUM HYDROXIDE": "氫氧化鋁 (中和胃酸藥)",
    
    "METFORMIN": "美福明 (第一線降血糖藥)",
    "GLIMEPIRIDE": "瑪爾胰 (降血糖藥)",
    "EMPAGLIFLOZIN": "恩排糖 (排糖藥/護心腎)",
    
    "AMLODIPINE": "脈優 (鈣離子阻斷降血壓藥)",
    "VALSARTAN": "得高壓 (ARB降血壓藥)",
    "LOSARTAN": "可悅您 (降血壓藥)",
    "BISOPROLOL": "康肯 (交感神經阻斷/降心跳血壓)",
    
    "ATORVASTATIN": "立普妥 (降膽固醇藥)",
    "ROSUVASTATIN": "冠脂妥 (強效降膽固醇藥)",
    
    "ZOLPIDEM": "使蒂諾斯 (短效安眠藥)",
    "ALPRAZOLAM": "讚安諾 (抗焦慮/輕度安眠)",
    "LORAZEPAM": "安定文 (抗焦慮/肌肉鬆弛)",
    "CLONAZEPAM": "利福全 (抗癲癇/神經痛/抗焦慮)",
    "ESCITALOPRAM": "立普能 (抗憂鬱藥)",
    
    "DEXTROMETHORPHAN": "停咳 (乾咳止咳藥)",
    "AMBROXOL": "化痰藥",
    "ACETYLCYSTEINE": "愛克痰 (發泡錠化痰藥)",
    
    "ALLOPURINOL": "別嘌醇 (降尿酸/痛風藥)",
    "COLCHICINE": "秋水仙素 (急性痛風藥)"
}

def map_otc_drugs():
    if not os.path.exists(DB_PATH):
        logging.error(f"Database not found at {DB_PATH}")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    total_updated = 0
    
    for ingredient, otc_name in OTC_MAPPING.items():
        # Update matching drugs (case-insensitive for ingredient)
        cursor.execute('''
            UPDATE drugs 
            SET otc_name = ? 
            WHERE ingredient LIKE ? OR drug_name_en LIKE ?
        ''', (otc_name, f'%{ingredient}%', f'%{ingredient}%'))
        
        updated = cursor.rowcount
        if updated > 0:
            logging.info(f"Mapped '{ingredient}' -> '{otc_name}' ({updated} records updated)")
            total_updated += updated
            
    conn.commit()
    conn.close()
    
    logging.info(f"OTC drug mapping complete! Total records updated: {total_updated}")

if __name__ == "__main__":
    map_otc_drugs()
