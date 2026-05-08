# 📚 如何使用 DrtoolboxLocalServer 系統

完整的中文使用指南，包含數據導入、API 調用和系統配置。

---

## 目錄

1. [快速開始](#快速開始)
2. [系統架構](#系統架構)
3. [數據導入指南](#數據導入指南)
4. [API 使用說明](#api-使用說明)
5. [常見問題](#常見問題)

---

## 快速開始

### 1️⃣ 初始化系統（第一次使用）

```bash
# 進入項目目錄
cd ~/DrtoolboxLocalServer

# 創建虛擬環境（可選）
python3 -m venv venv
source venv/bin/activate

# 安裝依賴
pip install flask flask-cors chromadb requests python-dotenv llama-cpp-python

# 初始化數據庫（創建 SQLite 數據庫）
python3 scripts/populate_databases.py --all

# 啟動 API 服務器
python3 src/api/app.py
```

**預期輸出:**
```
 * Running on http://0.0.0.0:8080
```

API 現在運行在: **http://localhost:8080**

### 2️⃣ 測試系統

```bash
# 在新的終端窗口，運行測試套件
python3 scripts/test_hybrid_api.py
```

**預期結果:** ✅ 15/15 測試通過

---

## 系統架構

### 📊 三層架構

```
┌─────────────────────────────────────┐
│      你的應用 / 前端界面             │
│   (Web 應用、移動應用、CLI 工具)     │
└────────────┬────────────────────────┘
             │ HTTP REST API
             ▼
┌─────────────────────────────────────┐
│        Flask REST API (port 8080)    │
│  (/api/v1/hybrid/*, /api/v1/rag/*)  │
└────────────┬───────────────────┬────┘
             │                   │
      ┌──────▼──────┐    ┌───────▼──────┐
      │   SQLite    │    │  向量數據庫  │
      │  數據庫     │    │   (Chroma)   │
      └──────┬──────┘    └───────┬──────┘
             │                   │
    ┌────────┴────────┐    ┌─────┴──────┐
    ▼                 ▼    ▼            ▼
 medical.db       clinic.db  general_  clinic_
                              medical   specific
  (事實數據)      (操作數據)  (醫療知識)
  (精確)          (精確)     (語義)
```

### 🗄️ 三個核心存儲

| 存儲 | 用途 | 更新頻率 | 查詢速度 |
|------|------|---------|---------|
| **medical.db** | 醫學知識、病例模板 | 低頻 | ⚡ 5ms |
| **clinic.db** | 診所運營、員工、日程 | 中頻 | ⚡ 5ms |
| **Chroma (RAG)** | 醫學文檔向量搜索 | 中頻 | ⏱️ 150ms |

---

## 數據導入指南

### 方法 1️⃣: 快速導入（使用提供的腳本）

#### 🏥 導入診所信息到 clinic.db

編輯 `scripts/populate_databases.py`，修改 `populate_clinic_info()` 方法：

```python
# 找到這一行 (約第 310 行)
clinic = {
    'clinic_name': 'Healthy Life Clinic',
    'clinic_name_english': 'Healthy Life Clinic',
    'clinic_name_chinese': '健康生活診所',  # 改為你的診所名稱
    'phone': '(02) 2345-6789',  # 改為你的電話
    'address': '台北市信義區市府路1號',  # 改為你的地址
    'district': '信義區',  # 改為你的行政區
    'city': '台北市',  # 改為你的城市
    # ... 其他信息
}
```

**然後運行:**
```bash
python3 scripts/populate_databases.py --clinic
```

#### 🧑‍⚕️ 導入醫療人員到 clinic.db

編輯 `scripts/populate_databases.py`，修改 `populate_clinic_staff()` 方法：

```python
staff = [
    ('DOC001', '王醫生', 'Wang Doctor', '主治醫師', '內科', 'LIC123456', '2026-12-31', '0912345678', 'wang@clinic.tw', json.dumps(['星期一', '星期二']), 'full-time'),
    ('DOC002', '李醫生', 'Li Doctor', '主治醫師', '外科', 'LIC123457', '2026-12-31', '0912345679', 'li@clinic.tw', json.dumps(['星期三', '星期四']), 'full-time'),
    # 添加更多員工...
]
```

**然後運行:**
```bash
python3 scripts/populate_databases.py --clinic
```

#### 📅 導入診所時間表到 clinic.db

編輯 `scripts/populate_databases.py`，修改 `populate_clinic_schedules()` 方法：

```python
schedules = [
    # (日期, 日期號, 上午開始, 上午結束, 上午醫生, 上午容量, 下午開始, 下午結束, 下午醫生, 下午容量, 晚上開始, 晚上結束, 晚上醫生, 晚上容量)
    ('星期一', 1, '08:00', '12:00', '王醫生', 20, '14:00', '18:00', '李醫生', 20, '19:00', '21:00', '王醫生', 10),
    ('星期二', 2, '08:00', '12:00', '李醫生', 20, '14:00', '18:00', '王醫生', 20, '19:00', '21:00', '李醫生', 10),
    # 添加更多日期...
]
```

**然後運行:**
```bash
python3 scripts/populate_databases.py --clinic
```

---

### 方法 2️⃣: 直接 SQL 插入（高級用戶）

#### 插入到 medical.db

```bash
python3 << 'EOF'
import sqlite3
import json

conn = sqlite3.connect('data/local_db/medical.db')
cursor = conn.cursor()

# 添加醫療知識
cursor.execute('''
    INSERT INTO medical_knowledge
    (category, subcategory, title, content, keywords, language, confidence, is_active)
    VALUES (?, ?, ?, ?, ?, 'zh_TW', 0.85, 1)
''', (
    '糖尿病',  # category
    'Type 2',  # subcategory
    '2型糖尿病管理指南',  # title
    '2型糖尿病是最常見的糖尿病類型...',  # content
    '糖尿病,2型,管理,治療',  # keywords
))

# 添加醫療條件
cursor.execute('''
    INSERT INTO medical_conditions
    (condition_name, description, symptoms, causes, risk_factors, 
     treatment_options, prevention, severity_levels, icd_code)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (
    '高血脂症',  # condition_name
    '血液中脂肪水平過高',  # description
    json.dumps(['疲勞', '胸痛']),  # symptoms (JSON array)
    json.dumps(['遺傳因素', '不健康飲食']),  # causes
    json.dumps(['肥胖', '缺乏運動']),  # risk_factors
    json.dumps(['飲食控制', '他汀類藥物']),  # treatment_options
    '健康飲食，規律運動',  # prevention
    json.dumps({'mild': '輕微升高', 'moderate': '中度升高', 'severe': '嚴重升高'}),  # severity_levels
    'E78',  # icd_code
))

conn.commit()
conn.close()
print("✓ 數據已插入")
EOF
```

#### 插入到 clinic.db

```bash
python3 << 'EOF'
import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect('data/local_db/clinic.db')
cursor = conn.cursor()

# 先插入診所信息
cursor.execute('''
    INSERT INTO clinic_info
    (clinic_name, clinic_name_english, clinic_name_chinese, phone, email, address,
     district, city, postal_code, established_year, department_type, specialties,
     director_name, director_title, staff_count, num_beds, has_imaging, has_lab, 
     has_emergency, is_active, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
''', (
    'Your Clinic Name',  # clinic_name
    'Your Clinic English Name',  # clinic_name_english
    '你的診所名稱',  # clinic_name_chinese
    '(02) XXXX-XXXX',  # phone
    'info@yourclinic.tw',  # email
    '台北市XX區XX街XX號',  # address
    'XX區',  # district
    '台北市',  # city
    '10000',  # postal_code
    2020,  # established_year
    '綜合診所',  # department_type
    json.dumps(['內科', '外科']),  # specialties
    '院長名稱',  # director_name
    '院長',  # director_title
    10,  # staff_count
    5,  # num_beds
    1,  # has_imaging
    1,  # has_lab
    0,  # has_emergency
    '診所簡介',  # notes
))

conn.commit()
conn.close()
print("✓ 診所信息已插入")
EOF
```

---

### 方法 3️⃣: 導入醫學文檔到 RAG（向量搜索）

#### 🔍 上傳 PDF/文本文檔

```bash
# 方法 A: 通過 API 端點
curl -X POST http://localhost:8080/api/v1/rag/ingest \
  -F "file=@data/rag/general_docs/your_document.pdf" \
  -F "collection=general_medical"

# 方法 B: Python 腳本
python3 << 'EOF'
import sys
sys.path.insert(0, 'src')
from rag.ingest import DocumentIngestor

# 導入到 general_medical 集合
ingestor = DocumentIngestor(
    chroma_dir="data/rag/chroma_new/",
    collection_name="general_medical"
)

result = ingestor.ingest(
    file_path="data/rag/general_docs/medical_articles.pdf",
    metadata={"category": "醫療知識", "source": "醫學資料庫"}
)

print(f"✓ 導入成功: {result.chunks} 個文本塊")
EOF
```

#### 📝 導入本地 JSON 文檔

```bash
python3 << 'EOF'
import json
import sys
sys.path.insert(0, 'src')
from rag.ingest import DocumentIngestor

# 讀取 JSON 文檔
with open('data/rag/general_docs/medical_data.json', 'r', encoding='utf-8') as f:
    documents = json.load(f)

# 初始化導入器
ingestor = DocumentIngestor(
    chroma_dir="data/rag/chroma_new/",
    collection_name="general_medical"
)

# 導入每個文檔
for doc in documents:
    ingestor.ingest_text(
        text=doc.get('content'),
        metadata={
            'title': doc.get('title'),
            'category': doc.get('category'),
            'source': 'medical_data.json'
        }
    )

print(f"✓ {len(documents)} 個文檔已導入")
EOF
```

#### 🏥 導入診所特定文檔到 RAG

```bash
# 導入到 clinic_specific 集合
curl -X POST http://localhost:8080/api/v1/rag/ingest \
  -F "file=@data/rag/clinic_docs/clinic_protocols.pdf" \
  -F "collection=clinic_specific"
```

---

### 方法 4️⃣: 批量導入數據

#### 📊 從 CSV 導入到 medical.db

```bash
python3 << 'EOF'
import csv
import sqlite3
import json

def import_csv_to_medical_conditions(csv_file):
    """從 CSV 導入醫療條件"""
    conn = sqlite3.connect('data/local_db/medical.db')
    cursor = conn.cursor()
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute('''
                INSERT INTO medical_conditions
                (condition_name, description, symptoms, causes, 
                 risk_factors, treatment_options, prevention, icd_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['condition_name'],
                row['description'],
                json.dumps(row['symptoms'].split(',')),
                json.dumps(row['causes'].split(',')),
                json.dumps(row['risk_factors'].split(',')),
                json.dumps(row['treatment_options'].split(',')),
                row['prevention'],
                row['icd_code'],
            ))
    
    conn.commit()
    conn.close()
    print(f"✓ CSV 數據已導入")

# 調用函數
import_csv_to_medical_conditions('data/your_conditions.csv')
EOF
```

**CSV 格式示例 (data/your_conditions.csv):**
```
condition_name,description,symptoms,causes,risk_factors,treatment_options,prevention,icd_code
高血壓,血液對血管壁的壓力過高,頭痛|胸悶,遺傳|鹽分過多,肥胖|年齡,降壓藥|運動,減少鹽分|規律運動,I10-I15
```

#### 📊 從 Excel 導入到 clinic.db

```bash
# 首先安裝 openpyxl
pip install openpyxl

python3 << 'EOF'
import openpyxl
import sqlite3
from datetime import datetime

def import_staff_from_excel(excel_file):
    """從 Excel 導入員工信息"""
    conn = sqlite3.connect('data/local_db/clinic.db')
    cursor = conn.cursor()
    
    # 先获取 clinic_id
    cursor.execute("SELECT id FROM clinic_info LIMIT 1")
    clinic_id = cursor.fetchone()[0]
    
    # 讀取 Excel
    workbook = openpyxl.load_workbook(excel_file)
    worksheet = workbook.active
    
    for row in worksheet.iter_rows(min_row=2, values_only=True):
        cursor.execute('''
            INSERT INTO clinic_staff
            (clinic_id, staff_id, staff_name, staff_name_english, position,
             specialty, phone, email, is_active, hire_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        ''', (
            clinic_id,
            row[0],  # staff_id
            row[1],  # staff_name
            row[2],  # staff_name_english
            row[3],  # position
            row[4],  # specialty
            row[5],  # phone
            row[6],  # email
            datetime.now().date(),  # hire_date
        ))
    
    conn.commit()
    conn.close()
    print(f"✓ Excel 數據已導入")

# 調用函數
import_staff_from_excel('data/staff_list.xlsx')
EOF
```

---

## API 使用說明

### 🏥 診所運營查詢（數據庫 - 快速精確）

#### 1. 獲取診所時間表

```bash
# 獲取星期一的時間表
curl "http://localhost:8080/api/v1/hybrid/clinic/schedule?day=星期一"
```

**響應:**
```json
{
  "status": "success",
  "data": {
    "day": "星期一",
    "morning": {
      "time": "08:00-12:00",
      "doctor": "王醫生",
      "capacity": 20
    },
    "afternoon": {
      "time": "14:00-18:00",
      "doctor": "李醫生",
      "capacity": 20
    },
    "evening": {
      "time": "19:00-21:00",
      "doctor": "王醫生",
      "capacity": 10
    }
  }
}
```

#### 2. 查詢員工名單

```bash
# 獲取所有員工
curl "http://localhost:8080/api/v1/hybrid/clinic/staff"

# 只獲取醫生
curl "http://localhost:8080/api/v1/hybrid/clinic/staff?position=主治醫師"
```

**響應:**
```json
{
  "status": "success",
  "count": 2,
  "data": [
    {
      "id": "DOC001",
      "name": "王醫生",
      "position": "主治醫師",
      "specialty": "內科",
      "phone": "0912345678",
      "email": "wang@clinic.tw"
    }
  ]
}
```

#### 3. 檢查庫存狀態

```bash
# 獲取所有物品
curl "http://localhost:8080/api/v1/hybrid/clinic/supplies"

# 只看低庫存警告
curl "http://localhost:8080/api/v1/hybrid/clinic/supplies?status=LOW_STOCK"
```

**響應:**
```json
{
  "status": "success",
  "count": 4,
  "low_stock_alert": 0,
  "data": [
    {
      "name": "醫用手套",
      "quantity": 500,
      "min": 100,
      "max": 1000,
      "unit": "box",
      "supplier": "台灣醫療用品公司",
      "status": "✓ OK"
    }
  ]
}
```

---

### 📚 醫療知識查詢（RAG - 語義搜索）

#### 1. 搜索醫學知識

```bash
curl -X POST http://localhost:8080/api/v1/hybrid/medical/search \
  -H "Content-Type: application/json" \
  -d '{"query": "糖尿病症狀和治療", "top_k": 3}'
```

**響應:**
```json
{
  "status": "success",
  "query": "糖尿病症狀和治療",
  "count": 3,
  "results": [
    {
      "title": "2型糖尿病管理",
      "content": "2型糖尿病是最常見的糖尿病類型...",
      "similarity": 0.89,
      "source": "medical_knowledge"
    }
  ]
}
```

#### 2. 查詢特定疾病信息

```bash
curl -X POST http://localhost:8080/api/v1/hybrid/medical/condition \
  -H "Content-Type: application/json" \
  -d '{"condition": "糖尿病"}'
```

**響應:**
```json
{
  "status": "success",
  "data": {
    "name": "糖尿病",
    "description": "影響身體處理血糖方式的疾病",
    "symptoms": ["多渴", "多尿", "疲勞", "視力模糊"],
    "causes": ["胰島素分泌不足", "胰島素抵抗"],
    "treatments": ["飲食控制", "運動", "藥物治療"],
    "icd_code": "E10-E14"
  }
}
```

---

### 🔗 混合查詢（組合 - 最智能）

#### 1. 診斷協助（症狀 → 可能診斷）

```bash
curl -X POST http://localhost:8080/api/v1/hybrid/diagnostic \
  -H "Content-Type: application/json" \
  -d '{"symptoms": "多渴、多尿、疲勞"}'
```

**響應:**
```json
{
  "status": "success",
  "query": "多渴、多尿、疲勞",
  "rag_results": [
    {
      "title": "糖尿病症狀和診斷",
      "content": "多渴是糖尿病的典型症狀...",
      "similarity": 0.89,
      "source": "medical_knowledge"
    }
  ],
  "db_results": [
    {
      "condition": "糖尿病",
      "description": "影響身體處理血糖方式的疾病",
      "symptoms": ["多渴", "多尿", "疲勞", "視力模糊"]
    }
  ],
  "recommendation": "Possible conditions: 糖尿病. Please consult a healthcare professional for proper diagnosis."
}
```

#### 2. 智能查詢（自動判斷意圖）

```bash
# 系統會自動判斷查詢類型，並調用適當的資源

# 診所運營查詢
curl -X POST http://localhost:8080/api/v1/hybrid/query \
  -H "Content-Type: application/json" \
  -d '{"query": "星期一王醫生什麼時間上班？"}'

# 醫學知識查詢
curl -X POST http://localhost:8080/api/v1/hybrid/query \
  -H "Content-Type: application/json" \
  -d '{"query": "如何治療高血壓？"}'

# 混合查詢
curl -X POST http://localhost:8080/api/v1/hybrid/query \
  -H "Content-Type: application/json" \
  -d '{"query": "王醫生可以治療糖尿病嗎？"}'
```

---

## 常見問題

### Q1: 如何更新診所信息？

**方法 A: 直接 SQL 更新**
```bash
python3 << 'EOF'
import sqlite3

conn = sqlite3.connect('data/local_db/clinic.db')
cursor = conn.cursor()

cursor.execute('''
    UPDATE clinic_info
    SET clinic_name_chinese = '新診所名稱',
        phone = '(02) 8765-4321'
    WHERE id = 1
''')

conn.commit()
conn.close()
print("✓ 診所信息已更新")
EOF
```

**方法 B: 重新導入**
```bash
python3 scripts/populate_databases.py --clinic
```

---

### Q2: 如何添加新醫生？

```bash
python3 << 'EOF'
import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect('data/local_db/clinic.db')
cursor = conn.cursor()

# 先獲取診所 ID
cursor.execute("SELECT id FROM clinic_info LIMIT 1")
clinic_id = cursor.fetchone()[0]

# 添加新醫生
cursor.execute('''
    INSERT INTO clinic_staff
    (clinic_id, staff_id, staff_name, staff_name_english, position,
     specialty, license_number, license_expiry, phone, email,
     available_days, shift_type, is_active, hire_date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
''', (
    clinic_id,
    'DOC003',  # 員工ID
    '陳醫生',  # 員工名稱
    'Chen Doctor',  # 英文名稱
    '主治醫師',  # 職位
    '兒科',  # 科室
    'LIC123458',  # 執照編號
    '2026-12-31',  # 執照過期日期
    '0912345680',  # 電話
    'chen@clinic.tw',  # 郵箱
    json.dumps(['星期一', '星期三', '星期五']),  # 可用日期
    'full-time',  # 班次類型
    datetime.now().date(),  # 聘用日期
))

conn.commit()
conn.close()
print("✓ 新醫生已添加")
EOF
```

---

### Q3: 如何導入大量醫學文檔？

```bash
python3 << 'EOF'
import os
import sys
sys.path.insert(0, 'src')
from rag.ingest import DocumentIngestor
from pathlib import Path

# 導入器實例
ingestor = DocumentIngestor(
    chroma_dir="data/rag/chroma_new/",
    collection_name="general_medical"
)

# 遍歷目錄中的所有文檔
doc_dir = Path("data/rag/general_docs")
for file in doc_dir.glob("*.pdf"):
    print(f"正在導入 {file.name}...")
    try:
        result = ingestor.ingest(str(file))
        print(f"  ✓ {result.chunks} 個文本塊")
    except Exception as e:
        print(f"  ✗ 錯誤: {e}")

print("\n✓ 所有文檔已導入")
EOF
```

---

### Q4: 如何備份數據？

```bash
# 備份所有數據庫
cp -r data/local_db data/local_db.backup
cp -r data/rag/chroma_new data/rag/chroma_new.backup

echo "✓ 備份完成"
```

---

### Q5: 如何重置系統？

```bash
# 危險！這會刪除所有數據
rm -rf data/local_db
rm -rf data/rag/chroma_new

# 重新初始化
python3 scripts/populate_databases.py --all

echo "✓ 系統已重置"
```

---

## 最佳實踐

### ✅ 推薦做法

1. **定期備份數據**
   ```bash
   # 每週備份
   cp -r data/local_db data/local_db.$(date +%Y%m%d).backup
   ```

2. **驗證導入的數據**
   ```bash
   # 導入後檢查數據
   python3 << 'EOF'
   import sqlite3
   conn = sqlite3.connect('data/local_db/medical.db')
   cursor = conn.cursor()
   cursor.execute("SELECT COUNT(*) FROM medical_conditions")
   print(f"共有 {cursor.fetchone()[0]} 個醫療條件")
   conn.close()
   EOF
   ```

3. **使用版本控制追蹤數據變化**
   ```bash
   # 記錄導入時間和內容
   echo "$(date): 導入 10 個新的醫療條件" >> data/CHANGELOG.md
   ```

### ❌ 避免的做法

1. ❌ 直接修改數據庫文件
2. ❌ 不備份就批量刪除數據
3. ❌ 混合不同編碼的文檔（始終使用 UTF-8）
4. ❌ 導入重複的數據而不檢查

---

## 故障排除

### 🔴 問題: API 無法啟動

```bash
# 檢查 Python 環境
python3 --version  # 應該 >= 3.8

# 檢查依賴
pip list | grep -E "flask|chromadb|llama"

# 檢查導入
python3 << 'EOF'
import sys
sys.path.insert(0, 'src')
from api.app import create_app
try:
    app = create_app()
    print("✓ Flask 應用可以創建")
except Exception as e:
    print(f"✗ 錯誤: {e}")
EOF
```

### 🔴 問題: 數據庫連接失敗

```bash
# 檢查文件是否存在
ls -lh data/local_db/

# 檢查權限
chmod 644 data/local_db/*.db

# 驗證數據庫完整性
python3 << 'EOF'
import sqlite3
for db in ['medical.db', 'clinic.db']:
    try:
        conn = sqlite3.connect(f'data/local_db/{db}')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        count = cursor.fetchone()[0]
        print(f"✓ {db}: {count} 個表")
        conn.close()
    except Exception as e:
        print(f"✗ {db}: {e}")
EOF
```

### 🔴 問題: RAG 搜索沒有結果

```bash
# 檢查 Chroma 集合
python3 << 'EOF'
import sys
sys.path.insert(0, 'src')
from rag.search import SemanticSearch

search = SemanticSearch(
    chroma_dir="data/rag/chroma_new/",
    collection_name="general_medical"
)

# 查詢集合信息
info = search.collection.count()
print(f"✓ 集合中有 {info} 個文檔")
EOF
```

---

## 下一步

✅ 系統已準備好使用！

1. **導入你的數據** - 按照上面的指南添加診所信息和醫學文檔
2. **測試 API** - 運行 `test_hybrid_api.py` 確保一切正常
3. **構建前端** - 使用 API 端點創建你的應用界面
4. **部署** - 使用 gunicorn 或 Docker 部署到生產環境

**文檔:** 
- 完整 API 參考: `HYBRID_API_GUIDE.md`
- 快速開始: `QUICKSTART_HYBRID_API.md`

**聯繫支持:** 如有問題，請檢查上面的故障排除部分。

---

**最後更新:** 2026-05-07  
**版本:** 1.0.0  
**狀態:** ✅ 準備生產
