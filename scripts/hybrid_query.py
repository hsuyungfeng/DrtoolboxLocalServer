#!/usr/bin/env python3
"""
Hybrid Query System: Combines Database Query + RAG Query for optimal results.

Strategy:
1. Factual/Operational queries → Use SQLite Database
2. Knowledge/Medical queries → Use RAG (Vector Search)
3. Combined queries → Use both and merge results
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Database paths
MEDICAL_DB = Path("data/local_db/medical.db")
CLINIC_DB = Path("data/local_db/clinic.db")

# RAG paths
CHROMA_DIR = Path("data/rag/chroma_new")


class HybridQueryEngine:
    """Combines SQL database queries with RAG vector search."""

    def __init__(self):
        self.medical_conn = sqlite3.connect(str(MEDICAL_DB))
        self.medical_cursor = self.medical_conn.cursor()

        self.clinic_conn = sqlite3.connect(str(CLINIC_DB))
        self.clinic_cursor = self.clinic_conn.cursor()

        # Try to initialize RAG (optional)
        self.rag_available = False
        try:
            import sys
            sys.path.insert(0, 'src')
            from rag.search import SemanticSearch
            self.rag_search = SemanticSearch(
                chroma_dir=str(CHROMA_DIR),
                collection_name="general_medical_docs"
            )
            self.rag_available = True
            print("✓ RAG engine initialized")
        except Exception as e:
            print(f"⚠️  RAG not available: {e}")

    # ========================================================================
    # DATABASE QUERIES (Factual/Operational)
    # ========================================================================

    def get_clinic_schedule(self, day_of_week: str) -> Dict[str, Any]:
        """Get clinic schedule for a specific day (SQL only)."""
        self.clinic_cursor.execute('''
            SELECT day_of_week, morning_start, morning_end, morning_doctor, morning_capacity,
                   afternoon_start, afternoon_end, afternoon_doctor, afternoon_capacity,
                   evening_start, evening_end, evening_doctor, evening_capacity
            FROM clinic_schedules
            WHERE day_of_week = ? AND is_active = 1
        ''', (day_of_week,))

        row = self.clinic_cursor.fetchone()
        if not row:
            return {"error": f"No schedule found for {day_of_week}"}

        return {
            "day": row[0],
            "morning": {
                "time": f"{row[1]}-{row[2]}",
                "doctor": row[3],
                "capacity": row[4]
            },
            "afternoon": {
                "time": f"{row[5]}-{row[6]}",
                "doctor": row[7],
                "capacity": row[8]
            },
            "evening": {
                "time": f"{row[9]}-{row[10]}" if row[9] else None,
                "doctor": row[11],
                "capacity": row[12]
            }
        }

    def get_clinic_staff_roster(self) -> List[Dict[str, Any]]:
        """Get active clinic staff (SQL only)."""
        self.clinic_cursor.execute('''
            SELECT staff_id, staff_name, position, specialty, phone, email
            FROM clinic_staff
            WHERE is_active = 1
            ORDER BY position, staff_name
        ''')

        return [
            {
                "id": row[0],
                "name": row[1],
                "position": row[2],
                "specialty": row[3],
                "phone": row[4],
                "email": row[5]
            }
            for row in self.clinic_cursor.fetchall()
        ]

    def get_clinic_supplies_status(self) -> List[Dict[str, Any]]:
        """Get inventory status - highlight low stock (SQL only)."""
        self.clinic_cursor.execute('''
            SELECT supply_name, quantity_on_hand, minimum_quantity,
                   maximum_quantity, unit, supplier_name
            FROM clinic_supplies
            WHERE is_active = 1
            ORDER BY quantity_on_hand / minimum_quantity ASC
        ''')

        return [
            {
                "name": row[0],
                "quantity": row[1],
                "min": row[2],
                "max": row[3],
                "unit": row[4],
                "supplier": row[5],
                "status": "🔴 LOW STOCK" if row[1] <= row[2] else "✓ OK"
            }
            for row in self.clinic_cursor.fetchall()
        ]

    # ========================================================================
    # RAG QUERIES (Medical Knowledge)
    # ========================================================================

    def search_medical_knowledge(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search medical knowledge using RAG (vector similarity)."""
        if not self.rag_available:
            return [{"error": "RAG engine not available"}]

        try:
            results = self.rag_search.search(query, top_k=top_k)
            return [
                {
                    "title": r.get("title", "Unknown"),
                    "content": r.get("content", "")[:300] + "...",
                    "similarity": r.get("similarity", 0),
                    "source": r.get("source", "unknown")
                }
                for r in results
            ]
        except Exception as e:
            return [{"error": str(e)}]

    def search_medical_conditions(self, condition: str) -> Dict[str, Any]:
        """Search medical conditions database (SQL + structured data)."""
        self.medical_cursor.execute('''
            SELECT condition_name, description, symptoms, causes, risk_factors,
                   treatment_options, prevention, severity_levels, icd_code
            FROM medical_conditions
            WHERE condition_name LIKE ? OR description LIKE ?
            LIMIT 1
        ''', (f"%{condition}%", f"%{condition}%"))

        row = self.medical_cursor.fetchone()
        if not row:
            return {"error": f"Condition '{condition}' not found"}

        return {
            "name": row[0],
            "description": row[1],
            "symptoms": json.loads(row[2]) if row[2] else [],
            "causes": json.loads(row[3]) if row[3] else [],
            "risk_factors": json.loads(row[4]) if row[4] else [],
            "treatments": json.loads(row[5]) if row[5] else [],
            "prevention": row[6],
            "severity": json.loads(row[7]) if row[7] else {},
            "icd_code": row[8]
        }

    # ========================================================================
    # HYBRID QUERIES (Combine SQL + RAG)
    # ========================================================================

    def hybrid_diagnostic_query(self, symptoms: str) -> Dict[str, Any]:
        """
        Hybrid query: User describes symptoms

        Steps:
        1. Search medical_knowledge with RAG for related articles
        2. Search medical_conditions for exact matches
        3. Combine and rank results
        """
        print(f"\n🔍 Hybrid Query: '{symptoms}'")
        print("=" * 70)

        result = {
            "query": symptoms,
            "rag_results": [],
            "db_results": [],
            "recommendation": ""
        }

        # Step 1: RAG search for knowledge articles
        if self.rag_available:
            print("\n📚 Searching medical knowledge (RAG)...")
            rag_results = self.search_medical_knowledge(symptoms, top_k=3)
            result["rag_results"] = rag_results
            print(f"   Found {len(rag_results)} knowledge articles")

        # Step 2: Search database for exact conditions
        print("\n🔬 Searching medical conditions (Database)...")
        self.medical_cursor.execute('''
            SELECT condition_name, description, symptoms
            FROM medical_conditions
            ORDER BY CASE
                WHEN symptoms LIKE ? THEN 1
                WHEN description LIKE ? THEN 2
                ELSE 3
            END
            LIMIT 3
        ''', (f"%{symptoms}%", f"%{symptoms}%"))

        for row in self.medical_cursor.fetchall():
            result["db_results"].append({
                "condition": row[0],
                "description": row[1],
                "symptoms": json.loads(row[2]) if row[2] else []
            })
        print(f"   Found {len(result['db_results'])} matching conditions")

        # Step 3: Generate recommendation
        if result["db_results"]:
            top_condition = result["db_results"][0]["condition"]
            result["recommendation"] = f"Possible conditions: {top_condition}. Please consult a healthcare professional for proper diagnosis."
        elif result["rag_results"]:
            result["recommendation"] = f"Found related medical knowledge. Please see knowledge articles above."
        else:
            result["recommendation"] = "No matching information found. Please consult a healthcare professional."

        return result

    def hybrid_clinic_medical_query(self, query: str) -> Dict[str, Any]:
        """
        Hybrid query: Understand query intent and route appropriately

        Examples:
        - "When is Dr. Wang available?" → SQL (clinic schedule)
        - "What causes diabetes?" → RAG (medical knowledge)
        - "Can Dr. Wang treat my diabetes?" → Both (doctor + medical info)
        """
        print(f"\n🎯 Hybrid Query: '{query}'")
        print("=" * 70)

        result = {
            "query": query,
            "query_type": "unknown",
            "clinic_info": None,
            "medical_info": None
        }

        # Simple intent detection
        clinic_keywords = ["clinic", "schedule", "doctor", "staff", "appointment",
                          "時間", "醫生", "掛號", "預約", "門診"]
        medical_keywords = ["treat", "symptom", "disease", "medicine", "diabetes",
                           "症狀", "疾病", "治療", "藥物", "糖尿病"]

        has_clinic = any(kw.lower() in query.lower() for kw in clinic_keywords)
        has_medical = any(kw.lower() in query.lower() for kw in medical_keywords)

        # Route to appropriate system
        if has_clinic and has_medical:
            result["query_type"] = "hybrid"
            print("🔄 Type: HYBRID (Clinic + Medical)")
            # Extract components and query both
            if "doctor" in query.lower() or "醫生" in query:
                result["clinic_info"] = self.get_clinic_staff_roster()
            result["medical_info"] = self.search_medical_knowledge(query, top_k=2)

        elif has_clinic:
            result["query_type"] = "clinic"
            print("🏥 Type: CLINIC (Operational)")
            if "schedule" in query.lower() or "時間" in query:
                result["clinic_info"] = {
                    "type": "schedules",
                    "data": [self.get_clinic_schedule("星期一"),  # Example
                             self.get_clinic_schedule("星期二")]
                }
            elif "staff" in query.lower() or "醫生" in query:
                result["clinic_info"] = {
                    "type": "staff",
                    "data": self.get_clinic_staff_roster()
                }

        elif has_medical:
            result["query_type"] = "medical"
            print("📚 Type: MEDICAL (Knowledge)")
            result["medical_info"] = self.search_medical_knowledge(query, top_k=5)

        else:
            print("❓ Type: UNKNOWN")

        return result

    def close(self):
        """Close database connections."""
        self.medical_conn.close()
        self.clinic_conn.close()


def main():
    """Demo the hybrid query engine."""
    print("\n" + "=" * 70)
    print("🔗 HYBRID QUERY ENGINE DEMO")
    print("=" * 70)

    engine = HybridQueryEngine()

    # Example 1: Pure SQL query (Clinic schedule)
    print("\n\n📌 EXAMPLE 1: SQL Query (Clinic Schedule)")
    print("-" * 70)
    schedule = engine.get_clinic_schedule("星期一")
    print(json.dumps(schedule, ensure_ascii=False, indent=2))

    # Example 2: Pure SQL query (Staff roster)
    print("\n\n📌 EXAMPLE 2: SQL Query (Staff Roster)")
    print("-" * 70)
    staff = engine.get_clinic_staff_roster()
    for s in staff[:3]:
        print(f"  {s['name']:10} - {s['position']:10} ({s['phone']})")
    print(f"  ... and {len(staff)-3} more staff members")

    # Example 3: Pure SQL query (Inventory)
    print("\n\n📌 EXAMPLE 3: SQL Query (Inventory Status)")
    print("-" * 70)
    supplies = engine.get_clinic_supplies_status()
    for s in supplies:
        print(f"  {s['status']:15} {s['name']:20} ({s['quantity']}/{s['min']} {s['unit']})")

    # Example 4: Medical knowledge search
    print("\n\n📌 EXAMPLE 4: RAG Query (Medical Knowledge)")
    print("-" * 70)
    print("Query: 'What causes high blood pressure?'")
    results = engine.search_medical_knowledge("高血壓原因", top_k=2)
    for i, r in enumerate(results, 1):
        if "error" not in r:
            print(f"\n  Result {i}: {r['title']} (similarity: {r['similarity']:.2f})")
            print(f"  {r['content'][:150]}...")

    # Example 5: Hybrid diagnostic query
    print("\n\n📌 EXAMPLE 5: Hybrid Query (Diagnostic)")
    print("-" * 70)
    diagnostic = engine.hybrid_diagnostic_query("多渴、多尿、疲勞")
    print(f"\nRecommendation: {diagnostic['recommendation']}")

    # Example 6: Hybrid clinic+medical query
    print("\n\n📌 EXAMPLE 6: Hybrid Query (Clinic + Medical)")
    print("-" * 70)
    hybrid = engine.hybrid_clinic_medical_query("Can Dr. Wang treat my diabetes?")
    print(json.dumps({
        "type": hybrid["query_type"],
        "clinic_count": len(hybrid["clinic_info"]) if hybrid["clinic_info"] else 0,
        "medical_count": len(hybrid["medical_info"]) if hybrid["medical_info"] else 0
    }, ensure_ascii=False, indent=2))

    engine.close()
    print("\n" + "=" * 70)
    print("✅ Demo Complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()
