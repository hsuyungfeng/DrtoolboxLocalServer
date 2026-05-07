# 🚀 Quick Start: Hybrid Query API

Get the integrated Database + RAG system up and running in 5 minutes.

## Step 1: Ensure Databases Are Populated

```bash
# Populate both medical.db and clinic.db with sample data
python3 scripts/populate_databases.py --all
```

**Expected Output:**
```
============================================================
🗄️  DATABASE POPULATION SCRIPT
============================================================

📊 Populating medical.db...
📚 Loading medical knowledge...
✓ Imported 0 medical knowledge entries
🏥 Adding medical conditions...
✓ Added 3 medical conditions
📖 Adding medical terminology...
✓ Added 5 medical terms

📊 Populating clinic.db...
🏪 Adding clinic information...
✓ Added clinic: 健康生活診所
📅 Adding clinic schedules...
✓ Added 7 weekly schedules
👨‍⚕️ Adding clinic staff...
✓ Added 6 staff members
📋 Adding clinical protocols...
✓ Added 2 clinical protocols
📦 Adding clinic supplies...
✓ Added 4 supplies

✅ Population Complete!
```

---

## Step 2: Start the API Server

```bash
# Start Flask development server
python3 src/api/app.py
```

**Expected Output:**
```
 * Serving Flask app 'api.app'
 * Debug mode: off
 * Running on http://0.0.0.0:8080
```

The API is now live at: **http://localhost:8080**

---

## Step 3: Test the API

In a new terminal, test basic endpoints:

### Health Check
```bash
curl http://localhost:8080/api/v1/hybrid/health
```

**Response:**
```json
{
  "status": "healthy",
  "medical_db": "available",
  "clinic_db": "available",
  "rag_engine": "available"
}
```

### Get Clinic Schedule
```bash
curl "http://localhost:8080/api/v1/hybrid/clinic/schedule?day=星期一"
```

### Get Staff Roster
```bash
curl http://localhost:8080/api/v1/hybrid/clinic/staff
```

### Search Medical Knowledge
```bash
curl -X POST http://localhost:8080/api/v1/hybrid/medical/search \
  -H "Content-Type: application/json" \
  -d '{"query": "糖尿病症狀", "top_k": 3}'
```

### Diagnostic Query
```bash
curl -X POST http://localhost:8080/api/v1/hybrid/diagnostic \
  -H "Content-Type: application/json" \
  -d '{"symptoms": "多渴、多尿、疲勞"}'
```

---

## Step 4: Run Full Test Suite

```bash
# Test all 15 API endpoints
python3 scripts/test_hybrid_api.py
```

**Expected Output:**
```
======================================================================
  🔗 HYBRID QUERY API TEST SUITE
======================================================================

======================================================================
  1. Health Check
======================================================================

  📍 Health Check
     GET /api/v1/hybrid/health
     ✓ Status: 200
     Status: healthy

======================================================================
  2. Clinic Operations (Database)
======================================================================

  📍 Get Clinic Schedule - Monday
     GET /api/v1/hybrid/clinic/schedule
     ✓ Status: 200
     Count: 7

... [more tests]

======================================================================
  📊 TEST SUMMARY
======================================================================

Total Tests: 15
✓ Passed: 15
✗ Failed: 0

🎉 All tests passed!
```

---

## 📊 API Endpoints Overview

### Clinic Operations (Database - Fast & Exact)

| Endpoint | Method | Purpose | Speed |
|----------|--------|---------|-------|
| `/clinic/schedule` | GET | Get clinic hours for a day | ⚡ ~5ms |
| `/clinic/staff` | GET | Get staff roster | ⚡ ~5ms |
| `/clinic/supplies` | GET | Check inventory | ⚡ ~5ms |

### Medical Knowledge (RAG - Semantic Search)

| Endpoint | Method | Purpose | Speed |
|----------|--------|---------|-------|
| `/medical/search` | POST | Search medical articles | ⏱️ ~150ms |
| `/medical/condition` | POST | Look up disease info | ⏱️ ~50ms |

### Hybrid Queries (Combined - Best Results)

| Endpoint | Method | Purpose | Speed |
|----------|--------|---------|-------|
| `/diagnostic` | POST | Symptoms → diagnosis | ⏱️ ~200ms |
| `/query` | POST | Smart intent detection | ⏱️ ~200ms |

---

## 💡 Common Usage Patterns

### Pattern 1: Get Today's Schedule
```bash
curl "http://localhost:8080/api/v1/hybrid/clinic/schedule?day=星期一"
```

### Pattern 2: Find Specific Doctor
```bash
curl "http://localhost:8080/api/v1/hybrid/clinic/staff?position=主治醫師"
```

### Pattern 3: Check Low Stock Items
```bash
curl "http://localhost:8080/api/v1/hybrid/clinic/supplies?status=LOW_STOCK"
```

### Pattern 4: Medical Information
```bash
curl -X POST http://localhost:8080/api/v1/hybrid/medical/condition \
  -H "Content-Type: application/json" \
  -d '{"condition": "糖尿病"}'
```

### Pattern 5: Patient Symptom Check
```bash
curl -X POST http://localhost:8080/api/v1/hybrid/diagnostic \
  -H "Content-Type: application/json" \
  -d '{"symptoms": "頭痛、發燒"}'
```

### Pattern 6: Smart Query (Automatic Routing)
```bash
curl -X POST http://localhost:8080/api/v1/hybrid/query \
  -H "Content-Type: application/json" \
  -d '{"query": "When can Dr. Wang see patients with diabetes?"}'
```

---

## 🔄 Architecture Summary

```
┌─────────────────────────────────────────────────┐
│            Flask REST API Server                │
│         (src/api/routes/hybrid.py)             │
└──────────────────┬──────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
   ┌────▼────┐          ┌────▼─────┐
   │ Database │          │ RAG Search│
   │ Queries  │          │ (Chroma)  │
   └────┬────┘          └────┬─────┘
        │                    │
   ┌────▼────┐          ┌────▼──────────┐
   │medical  │          │general_medical│
   │clinic   │          │clinic_specific│
   └─────────┘          └────────────────┘
   
Facts & Operations      Medical Knowledge
  (Exact, Fast)         (Semantic, Smart)
```

---

## 🐛 Troubleshooting

### API won't start
```bash
# Check Python imports
python3 << 'EOF'
import sys
sys.path.insert(0, 'src')
from api.app import create_app
app = create_app()
print("✓ App created successfully")
EOF
```

### Connection refused
```bash
# Make sure API is running
ps aux | grep python3
# Should show: python3 src/api/app.py
```

### Tests fail
```bash
# Ensure databases exist
ls -lh data/local_db/
# Should show: medical.db, clinic.db

# Ensure data is populated
python3 scripts/populate_databases.py --all
```

### RAG unavailable
```bash
# Check Chroma database
python3 << 'EOF'
from scripts.hybrid_query import HybridQueryEngine
engine = HybridQueryEngine()
print(f"RAG Available: {engine.rag_available}")
EOF
```

---

## 📚 Next Steps

1. **Integrate with Frontend**: Use the API endpoints in your web/mobile app
2. **Add Your Clinic Data**: Modify `scripts/populate_databases.py` with real info
3. **Load Medical Documents**: Use `/rag/ingest` endpoint to add documents
4. **Deploy to Production**: Use gunicorn or Docker
5. **Add Authentication**: Implement JWT tokens for security

---

## 📖 Full Documentation

- **API Details**: See `HYBRID_API_GUIDE.md`
- **Database Schema**: See `schema/` directory
- **Population Script**: See `scripts/populate_databases.py`
- **Hybrid Query Engine**: See `scripts/hybrid_query.py`

---

## ✅ Verify Everything Works

Run this to ensure all components are functional:

```bash
#!/bin/bash

echo "🔍 Checking all components..."

# 1. Check databases
echo "1. Checking databases..."
python3 << 'EOF'
import sqlite3
for db in ['medical.db', 'clinic.db']:
    conn = sqlite3.connect(f'data/local_db/{db}')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
    count = cursor.fetchone()[0]
    print(f"   ✓ {db}: {count} tables")
    conn.close()
EOF

# 2. Check Flask app
echo "2. Checking Flask app..."
python3 << 'EOF'
import sys
sys.path.insert(0, 'src')
from api.app import create_app
app = create_app()
print("   ✓ Flask app loads successfully")
EOF

# 3. Check hybrid engine
echo "3. Checking hybrid query engine..."
python3 << 'EOF'
from scripts.hybrid_query import HybridQueryEngine
engine = HybridQueryEngine()
print("   ✓ Hybrid engine initializes successfully")
engine.close()
EOF

echo ""
echo "✅ All systems ready!"
echo ""
echo "Start the API server with:"
echo "  python3 src/api/app.py"
```

---

**Last Updated**: 2026-05-07  
**Status**: ✅ Ready to Use
