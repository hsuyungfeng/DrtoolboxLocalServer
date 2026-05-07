# 🔗 Hybrid Query API Guide

Complete guide for using the integrated SQLite Database + RAG Query API.

## 📚 Overview

The Hybrid Query System combines two powerful approaches:

- **SQLite Database**: For factual, operational data (schedules, staff, inventory)
- **RAG (Vector Search)**: For medical knowledge and semantic understanding

The API intelligently routes queries to the appropriate system(s) and combines results.

---

## 🚀 Starting the API Server

```bash
# Method 1: Direct Python (development)
python3 src/api/app.py

# Method 2: With gunicorn (production)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8080 src.api.app:app

# Method 3: Docker
docker build -t drtoolbox-api .
docker run -p 8080:8080 drtoolbox-api
```

**API runs at**: `http://localhost:8080`

---

## 📋 API Endpoints

### 1️⃣ Health Check

#### `GET /api/v1/hybrid/health`

Check if all systems are operational.

**Response:**
```json
{
  "status": "healthy",
  "medical_db": "available",
  "clinic_db": "available",
  "rag_engine": "available"
}
```

---

### 2️⃣ Clinic Operations (Database Queries)

#### `GET /api/v1/hybrid/clinic/schedule`

Get clinic schedule for a specific day.

**Parameters:**
- `day` (string): Day of week in Chinese (星期一, 星期二, etc.)

**Example:**
```bash
curl "http://localhost:8080/api/v1/hybrid/clinic/schedule?day=星期一"
```

**Response:**
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

---

#### `GET /api/v1/hybrid/clinic/staff`

Get clinic staff roster.

**Parameters:**
- `position` (optional): Filter by position (主治醫師, 護士, etc.)

**Example:**
```bash
curl "http://localhost:8080/api/v1/hybrid/clinic/staff"
curl "http://localhost:8080/api/v1/hybrid/clinic/staff?position=主治醫師"
```

**Response:**
```json
{
  "status": "success",
  "count": 6,
  "data": [
    {
      "id": "DOC001",
      "name": "王醫生",
      "position": "主治醫師",
      "specialty": "內科",
      "phone": "0912345678",
      "email": "wang@clinic.tw"
    },
    ...
  ]
}
```

---

#### `GET /api/v1/hybrid/clinic/supplies`

Get clinic inventory/supplies status.

**Parameters:**
- `category` (optional): Filter by category (藥物, 耗材, etc.)
- `status` (optional): Filter by status (LOW_STOCK or OK)

**Example:**
```bash
curl "http://localhost:8080/api/v1/hybrid/clinic/supplies"
curl "http://localhost:8080/api/v1/hybrid/clinic/supplies?status=LOW_STOCK"
```

**Response:**
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
    },
    ...
  ]
}
```

---

### 3️⃣ Medical Knowledge (RAG Queries)

#### `POST /api/v1/hybrid/medical/search`

Search medical knowledge using RAG (vector similarity).

**Request Body:**
```json
{
  "query": "What causes diabetes?",
  "top_k": 5
}
```

**Example:**
```bash
curl -X POST http://localhost:8080/api/v1/hybrid/medical/search \
  -H "Content-Type: application/json" \
  -d '{"query": "糖尿病症狀", "top_k": 3}'
```

**Response:**
```json
{
  "status": "success",
  "query": "糖尿病症狀",
  "count": 3,
  "results": [
    {
      "title": "糖尿病概述",
      "content": "糖尿病是一種影響身體處理血糖的疾病...",
      "similarity": 0.92,
      "source": "medical_knowledge"
    },
    ...
  ]
}
```

---

#### `POST /api/v1/hybrid/medical/condition`

Search medical conditions database.

**Request Body:**
```json
{
  "condition": "糖尿病"
}
```

**Example:**
```bash
curl -X POST http://localhost:8080/api/v1/hybrid/medical/condition \
  -H "Content-Type: application/json" \
  -d '{"condition": "糖尿病"}'
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "name": "糖尿病",
    "description": "影響身體處理血糖方式的疾病",
    "symptoms": ["多渴", "多尿", "疲勞", "視力模糊"],
    "causes": ["胰島素分泌不足", "胰島素抵抗"],
    "risk_factors": ["肥胖", "家族史", "年齡增長"],
    "treatments": ["飲食控制", "運動", "藥物治療"],
    "prevention": "維持健康體重，規律運動，健康飲食",
    "severity": {
      "mild": "血糖輕微升高",
      "moderate": "需要用藥控制",
      "severe": "併發症出現"
    },
    "icd_code": "E10-E14"
  }
}
```

---

### 4️⃣ Hybrid Queries (Combined)

#### `POST /api/v1/hybrid/diagnostic`

Hybrid diagnostic query combining RAG + Database.

**Combines:**
1. RAG search for medical knowledge articles
2. Database search for exact condition matches

**Request Body:**
```json
{
  "symptoms": "多渴、多尿、疲勞"
}
```

**Example:**
```bash
curl -X POST http://localhost:8080/api/v1/hybrid/diagnostic \
  -H "Content-Type: application/json" \
  -d '{"symptoms": "多渴、多尿、疲勞"}'
```

**Response:**
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

---

#### `POST /api/v1/hybrid/query`

Smart hybrid query with automatic intent detection.

Analyzes query to determine if it's:
1. **Clinic operational** (schedule, staff, supplies) → Database
2. **Medical knowledge** → RAG
3. **Combined** (clinic + medical) → Hybrid

**Request Body:**
```json
{
  "query": "Can Dr. Wang treat my diabetes?"
}
```

**Example:**
```bash
curl -X POST http://localhost:8080/api/v1/hybrid/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Can Dr. Wang treat my diabetes?"}'
```

**Response:**
```json
{
  "status": "success",
  "query": "Can Dr. Wang treat my diabetes?",
  "query_type": "hybrid",
  "clinic_info": {
    "type": "staff",
    "data": [...]
  },
  "medical_info": {
    "query": "diabetes",
    "results": [...]
  }
}
```

---

## 💡 Usage Examples

### Example 1: Check Clinic Hours

```bash
# Get Monday schedule
curl "http://localhost:8080/api/v1/hybrid/clinic/schedule?day=星期一"
```

### Example 2: Find Low Stock Items

```bash
# Check inventory for low stock
curl "http://localhost:8080/api/v1/hybrid/clinic/supplies?status=LOW_STOCK"
```

### Example 3: Search Medical Knowledge

```bash
# Find information about high blood pressure
curl -X POST http://localhost:8080/api/v1/hybrid/medical/search \
  -H "Content-Type: application/json" \
  -d '{"query": "高血壓治療方法"}'
```

### Example 4: Diagnostic Assistance

```bash
# Get help with symptoms
curl -X POST http://localhost:8080/api/v1/hybrid/diagnostic \
  -H "Content-Type: application/json" \
  -d '{"symptoms": "頭痛、胸悶、呼吸困難"}'
```

### Example 5: Smart Query

```bash
# Let system figure out what to search
curl -X POST http://localhost:8080/api/v1/hybrid/query \
  -H "Content-Type: application/json" \
  -d '{"query": "什麼時候Dr. Li可以看診？"}'
```

---

## 🔄 Query Flow Diagram

```
User Query
    ↓
Intent Detection
    ├─ Clinic Keywords (時間、醫生、掛號) → DB Query
    ├─ Medical Keywords (症狀、治療、疾病) → RAG Query
    └─ Both → Hybrid Query
    ↓
Results Routing
    ├─ DB → Return structured data
    ├─ RAG → Return semantic matches
    └─ Hybrid → Merge both results
    ↓
Response with Recommendation
```

---

## 📊 Performance Characteristics

| Operation | Speed | Accuracy | Best For |
|-----------|-------|----------|----------|
| **Database Query** | ⚡⚡⚡ Fast (ms) | ✓ Exact | Facts, operations |
| **RAG Search** | ⏱️ Moderate (100-200ms) | ✓✓ Contextual | Knowledge, recommendations |
| **Hybrid Query** | ⏱️ Moderate (100-300ms) | ✓✓✓ Best | Complex questions |

---

## 🐛 Troubleshooting

### Issue: "medical_db not available"

**Solution**: Ensure databases are initialized:
```bash
python3 scripts/populate_databases.py --all
```

### Issue: "rag_engine unavailable"

**Solution**: Check RAG initialization:
```bash
python3 scripts/hybrid_query.py
```

### Issue: Connection refused

**Solution**: Ensure API server is running:
```bash
python3 src/api/app.py
```

---

## 📖 Related Documentation

- [Database Schema Guide](schema/README.md)
- [RAG System Documentation](LLM_INTEGRATION_GUIDE.md)
- [Population Script Guide](scripts/populate_databases.py)

---

## ✅ Next Steps

1. **Start the API server**: `python3 src/api/app.py`
2. **Test endpoints**: Use curl examples above
3. **Integrate with frontend**: Build UI using these endpoints
4. **Add custom data**: Populate databases with your clinic info
5. **Deploy**: Use gunicorn/Docker for production

---

**Last Updated**: 2026-05-07
**API Version**: 1.0.0
