import sqlite3
import random
import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# Data for simulation
last_names = ["張", "李", "王", "劉", "陳", "楊", "趙", "黃", "周", "吳", "徐", "孫", "胡", "朱", "高", "林", "何", "郭", "馬", "羅"]
first_names = ["明", "芳", "偉", "秀英", "秀蘭", "建國", "小玲", "強", "軍", "平", "保羅", "大衛", "麗華", "惠珍", "雅婷", "冠宇", "欣怡", "宗翰", "佳穎", "佩珊"]
medical_conditions = ["無", "高血壓", "糖尿病", "過敏性鼻炎", "氣喘", "心臟病", "胃潰瘍", "偏頭痛", "腰痛", "近視", "乾眼症", "濕疹"]
allergies_list = ["無", "盤尼西林", "花生", "塵蟎", "海鮮", "花粉", "乳膠"]
topics = ["皮秒雷射", "水飛梭", "外泌體", "預約掛號", "價格詢問", "門診時間", "醫生推薦", "術後保養", "音波拉提", "水光針"]

def generate_random_patient(i):
    name = random.choice(last_names) + random.choice(first_names)
    phone = f"09{random.randint(10000000, 99999999)}"
    email = f"patient{i}_{random.randint(1000, 9999)}@example.com"
    # Age between 18 and 80
    days_old = random.randint(18*365, 80*365)
    dob = (datetime.now() - timedelta(days=days_old)).strftime("%Y-%m-%d")
    history = random.choice(medical_conditions)
    # 15% chance of having a second condition
    if random.random() < 0.15:
        history += f", {random.choice(medical_conditions)}"
    allergies = random.choice(allergies_list)
    return (name, phone, email, dob, history, allergies)

def expand_data(count=50):
    db_path = "data/db/clinic.db"
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"🚀 Expanding data with {count} new patients...")
    
    # Get current max patient_id to avoid conflicts if any
    cursor.execute("SELECT MAX(patient_id) FROM patients")
    max_id = cursor.fetchone()[0] or 0
    
    for i in range(count):
        # 1. Insert Patient
        patient_data = generate_random_patient(max_id + i + 1)
        cursor.execute("""
            INSERT INTO patients (name, phone, email, dob, medical_history, allergies, created_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (*patient_data, datetime.now().isoformat(), "simulation_script"))
        patient_id = cursor.lastrowid
        
        # 2. Create LINE mapping for 85% of patients
        line_id = f"U{random.randint(100000000, 999999999)}fake"
        if random.random() < 0.85:
            cursor.execute("INSERT INTO line_user_mapping (line_user_id, patient_id, linked_by) VALUES (?, ?, ?)", 
                         (line_id, patient_id, "simulation_script"))
            
            # 3. Create Conversations for these LINE users
            num_msgs = random.randint(5, 15)
            for m in range(num_msgs):
                topic = random.choice(topics)
                sender = "patient" if random.random() < 0.5 else "bot"
                
                if sender == "patient":
                    text = random.choice([
                        f"請問{topic}的費用是多少？",
                        f"我想預約下週三的{topic}",
                        f"請問{topic}有什麼副作用嗎？",
                        f"你們診所地址在哪裡？",
                        f"今天有開嗎？",
                        f"我想找張醫生看{topic}"
                    ])
                else:
                    text = f"關於您的{topic}諮詢，我們建議..."
                
                # Vary confidence to simulate "Knowledge Gaps"
                # Some topics have lower confidence
                if topic in ["外泌體", "術後保養"]:
                    conf = random.uniform(0.4, 0.7)
                else:
                    conf = random.uniform(0.75, 0.99)
                
                escalated = 1 if conf < 0.6 else 0
                
                msg_time = (datetime.now() - timedelta(days=random.randint(0, 14), hours=random.randint(0, 23))).isoformat()
                
                cursor.execute("""
                    INSERT INTO patient_conversations (patient_id, sender, text, rag_confidence, escalated_flag, timestamp, unread_flag)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (line_id, sender, text, conf, escalated, msg_time, 0))

        # 4. Create Appointments
        num_apps = random.randint(1, 4)
        for _ in range(num_apps):
            days_offset = random.randint(-45, 45)
            app_date = (datetime.now() + timedelta(days=days_offset)).strftime("%Y-%m-%d")
            
            if days_offset < 0:
                status = random.choice(["completed", "completed", "cancelled"])
            elif days_offset == 0:
                status = "confirmed"
            else:
                status = random.choice(["confirmed", "pending", "pending"])
                
            cursor.execute("""
                INSERT INTO appointments (patient_id, appointment_date, status, created_by) 
                VALUES (?, ?, ?, ?)
            """, (patient_id, app_date, status, "simulation_script"))

    conn.commit()
    
    # Also trigger the clinical analyzer to refresh the insights JSON
    try:
        from src.services.clinical_analyzer import clinical_analyzer
        print("📊 Refreshing clinical insights...")
        clinical_analyzer.extract_and_analyze()
    except Exception as e:
        print(f"Warning: Could not refresh insights: {e}")

    conn.close()
    print(f"✅ Data expansion complete. Total new patients added: {count}")

if __name__ == "__main__":
    count = 50
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except: pass
    expand_data(count)
