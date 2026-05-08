#!/usr/bin/env python3
"""
Populate both medical.db and clinic.db with initial data.

Usage:
    python3 scripts/populate_databases.py [--medical] [--clinic] [--all]

Examples:
    python3 scripts/populate_databases.py --all          # Populate both
    python3 scripts/populate_databases.py --medical      # Only medical.db
    python3 scripts/populate_databases.py --clinic       # Only clinic.db
"""

import sqlite3
import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Database paths
DB_DIR = Path("data/local_db")
MEDICAL_DB = DB_DIR / "medical.db"
CLINIC_DB = DB_DIR / "clinic.db"

# Data paths
DATA_DIR = Path("data/rag")
MEDICAL_JSON = DATA_DIR / "general_docs/medical_o1_sft_Chinese.json"


class MedicalDatabasePopulator:
    """Populate medical.db with medical knowledge, conditions, and case templates."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.cursor = self.conn.cursor()

    def close(self):
        self.conn.commit()
        self.conn.close()

    def populate_medical_knowledge(self):
        """Load medical knowledge from JSON file."""
        if not MEDICAL_JSON.exists():
            print(f"⚠️  {MEDICAL_JSON} not found, skipping medical knowledge import")
            return 0

        print(f"📚 Loading medical knowledge from {MEDICAL_JSON.name}...")
        try:
            with open(MEDICAL_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            return 0

        count = 0
        if isinstance(data, dict):
            # Handle different JSON structures
            items = data.get('data', []) or data.get('items', []) or [data]
        elif isinstance(data, list):
            items = data
        else:
            items = [data]

        for item in items:
            try:
                if isinstance(item, dict):
                    category = item.get('category', item.get('disease', '未分類'))
                    subcategory = item.get('subcategory', item.get('type', ''))
                    title = item.get('title', item.get('name', ''))
                    content = item.get('content', item.get('description', ''))
                    keywords = item.get('keywords', '')

                    # Skip if no content
                    if not title or not content:
                        continue

                    # Ensure keywords is string
                    if isinstance(keywords, list):
                        keywords = ','.join(keywords)

                    self.cursor.execute('''
                        INSERT INTO medical_knowledge
                        (category, subcategory, title, content, keywords, language, confidence, is_active)
                        VALUES (?, ?, ?, ?, ?, 'zh_TW', 0.85, 1)
                    ''', (category, subcategory, title, content, keywords))
                    count += 1
            except Exception as e:
                print(f"⚠️  Error processing item: {e}")
                continue

        self.conn.commit()
        print(f"✓ Imported {count} medical knowledge entries")
        return count

    def populate_medical_conditions(self):
        """Add sample medical conditions."""
        print("🏥 Adding medical conditions...")

        conditions = [
            {
                'condition_name': '糖尿病',
                'description': '影響身體處理血糖方式的疾病',
                'symptoms': json.dumps(['多渴', '多尿', '疲勞', '視力模糊']),
                'causes': json.dumps(['胰島素分泌不足', '胰島素抵抗']),
                'risk_factors': json.dumps(['肥胖', '家族史', '年齡增長']),
                'treatment_options': json.dumps(['飲食控制', '運動', '藥物治療']),
                'prevention': '維持健康體重，規律運動，健康飲食',
                'severity_levels': json.dumps({'mild': '血糖輕微升高', 'moderate': '需要用藥控制', 'severe': '併發症出現'}),
                'icd_code': 'E10-E14',
            },
            {
                'condition_name': '高血壓',
                'description': '血液對血管壁的壓力過高',
                'symptoms': json.dumps(['頭痛', '胸悶', '呼吸困難']),
                'causes': json.dumps(['遺傳因素', '鹽分攝取過多', '缺乏運動']),
                'risk_factors': json.dumps(['肥胖', '年齡', '壓力']),
                'treatment_options': json.dumps(['生活方式改變', '藥物治療', '飲食控制']),
                'prevention': '減少鹽分攝取，規律運動，控制體重',
                'severity_levels': json.dumps({'mild': '130-139/80-89', 'moderate': '140-159/90-99', 'severe': '≥160/100'}),
                'icd_code': 'I10-I15',
            },
            {
                'condition_name': '感冒',
                'description': '由病毒引起的上呼吸道感染',
                'symptoms': json.dumps(['咳嗽', '喉嚨痛', '流鼻涕', '發燒']),
                'causes': json.dumps(['病毒感染', '接觸傳染']),
                'risk_factors': json.dumps(['免疫力低下', '季節變化', '人群聚集']),
                'treatment_options': json.dumps(['充分休息', '多喝水', '支持療法']),
                'prevention': '洗手衛生，避免接觸患者，增強免疫力',
                'severity_levels': json.dumps({'mild': '輕微症狀', 'moderate': '症狀明顯', 'severe': '併發細菌感染'}),
                'icd_code': 'J00-J06',
            },
        ]

        count = 0
        for cond in conditions:
            try:
                self.cursor.execute('''
                    INSERT OR IGNORE INTO medical_conditions
                    (condition_name, description, symptoms, causes, risk_factors,
                     treatment_options, prevention, severity_levels, icd_code)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (cond['condition_name'], cond['description'], cond['symptoms'],
                      cond['causes'], cond['risk_factors'], cond['treatment_options'],
                      cond['prevention'], cond['severity_levels'], cond['icd_code']))
                count += 1
            except Exception as e:
                print(f"⚠️  Error adding condition {cond['condition_name']}: {e}")

        self.conn.commit()
        print(f"✓ Added {count} medical conditions")
        return count

    def populate_medical_terminology(self):
        """Add sample medical terminology."""
        print("📖 Adding medical terminology...")

        terms = [
            ('Blood Pressure', '血壓', '血壓', '血压', 'xuè yā', '血液對血管壁施加的壓力'),
            ('Diabetes Mellitus', '糖尿病', '糖尿病', '糖尿病', 'táng niào bìng', '影響血糖控制的內分泌疾病'),
            ('Hypertension', '高血壓', '高血壓', '高血压', 'gāo xuè yā', '血液對血管壁的壓力過高'),
            ('Diagnosis', '診斷', '診斷', '诊断', 'zhěn duàn', '通過檢查判定疾病'),
            ('Prognosis', '預後', '預後', '预后', 'yù hòu', '疾病未來可能的發展過程'),
        ]

        count = 0
        for eng, chi, trad, simp, pinyin, defn in terms:
            try:
                self.cursor.execute('''
                    INSERT OR IGNORE INTO medical_terminology
                    (english_term, chinese_term, traditional_chinese, simplified_chinese,
                     pronunciation_pinyin, definition)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (eng, chi, trad, simp, pinyin, defn))
                count += 1
            except Exception as e:
                print(f"⚠️  Error adding term {eng}: {e}")

        self.conn.commit()
        print(f"✓ Added {count} medical terms")
        return count


class ClinicDatabasePopulator:
    """Populate clinic.db with clinic-specific operational data."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.cursor = self.conn.cursor()

    def close(self):
        self.conn.commit()
        self.conn.close()

    def populate_clinic_info(self):
        """Add clinic basic information."""
        print("🏪 Adding clinic information...")

        clinic = {
            'clinic_name': 'Healthy Life Clinic',
            'clinic_name_english': 'Healthy Life Clinic',
            'clinic_name_chinese': '健康生活診所',
            'phone': '(02) 2345-6789',
            'fax': '(02) 2345-6790',
            'email': 'info@healthyclinic.tw',
            'website': 'www.healthyclinic.tw',
            'address': '台北市信義區市府路1號',
            'district': '信義區',
            'city': '台北市',
            'postal_code': '11001',
            'gps_latitude': 25.0333,
            'gps_longitude': 121.5627,
            'established_year': 2015,
            'department_type': '綜合診所',
            'specialties': json.dumps(['內科', '外科', '小兒科', '婦產科']),
            'director_name': '王醫生',
            'director_title': '院長',
            'staff_count': 12,
            'num_beds': 6,
            'has_imaging': 1,
            'has_lab': 1,
            'has_emergency': 0,
            'notes': '提供24小時掛號預約服務',
        }

        try:
            self.cursor.execute('''
                INSERT INTO clinic_info
                (clinic_name, clinic_name_english, clinic_name_chinese, phone, fax, email, website,
                 address, district, city, postal_code, gps_latitude, gps_longitude,
                 established_year, department_type, specialties, director_name, director_title,
                 staff_count, num_beds, has_imaging, has_lab, has_emergency, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', tuple(clinic.values()))
            self.conn.commit()
            print(f"✓ Added clinic: {clinic['clinic_name_chinese']}")
            return 1
        except Exception as e:
            print(f"❌ Error adding clinic info: {e}")
            return 0

    def populate_clinic_schedules(self):
        """Add weekly clinic schedules."""
        print("📅 Adding clinic schedules...")

        # Get clinic_id
        self.cursor.execute("SELECT id FROM clinic_info LIMIT 1")
        clinic_id_row = self.cursor.fetchone()
        if not clinic_id_row:
            print("⚠️  No clinic found, skipping schedules")
            return 0

        clinic_id = clinic_id_row[0]

        schedules = [
            ('星期一', 1, '08:00', '12:00', '王醫生', 20, '14:00', '18:00', '李醫生', 20, '19:00', '21:00', '王醫生', 10),
            ('星期二', 2, '08:00', '12:00', '李醫生', 20, '14:00', '18:00', '王醫生', 20, '19:00', '21:00', '李醫生', 10),
            ('星期三', 3, '08:00', '12:00', '王醫生', 20, '14:00', '18:00', '李醫生', 20, None, None, None, None),
            ('星期四', 4, '08:00', '12:00', '李醫生', 20, '14:00', '18:00', '王醫生', 20, '19:00', '21:00', '李醫生', 10),
            ('星期五', 5, '08:00', '12:00', '王醫生', 20, '14:00', '18:00', '李醫生', 20, '19:00', '21:00', '王醫生', 10),
            ('星期六', 6, '08:00', '12:00', '李醫生', 20, '14:00', '17:00', '王醫生', 15, None, None, None, None),
            ('星期日', 7, None, None, None, None, None, None, None, None, None, None, None, None),
        ]

        count = 0
        for day_name, day_num, m_start, m_end, m_doc, m_cap, a_start, a_end, a_doc, a_cap, e_start, e_end, e_doc, e_cap in schedules:
            try:
                self.cursor.execute('''
                    INSERT INTO clinic_schedules
                    (clinic_id, day_of_week, day_number, morning_start, morning_end, morning_doctor, morning_capacity,
                     afternoon_start, afternoon_end, afternoon_doctor, afternoon_capacity,
                     evening_start, evening_end, evening_doctor, evening_capacity, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ''', (clinic_id, day_name, day_num, m_start, m_end, m_doc, m_cap,
                      a_start, a_end, a_doc, a_cap, e_start, e_end, e_doc, e_cap))
                count += 1
            except Exception as e:
                print(f"⚠️  Error adding schedule for {day_name}: {e}")

        self.conn.commit()
        print(f"✓ Added {count} weekly schedules")
        return count

    def populate_clinic_staff(self):
        """Add clinic staff."""
        print("👨‍⚕️ Adding clinic staff...")

        self.cursor.execute("SELECT id FROM clinic_info LIMIT 1")
        clinic_id_row = self.cursor.fetchone()
        if not clinic_id_row:
            return 0

        clinic_id = clinic_id_row[0]

        staff = [
            ('DOC001', '王醫生', 'Wang Doctor', '主治醫師', '內科', 'LIC123456', '2026-12-31', '0912345678', 'wang@clinic.tw', json.dumps(['星期一', '星期二', '星期四', '星期五', '星期六']), 'full-time'),
            ('DOC002', '李醫生', 'Li Doctor', '主治醫師', '外科', 'LIC123457', '2026-12-31', '0912345679', 'li@clinic.tw', json.dumps(['星期一', '星期二', '星期四', '星期五', '星期六']), 'full-time'),
            ('NUR001', '陳護士', 'Chen Nurse', '護士', None, 'NUR123456', '2026-12-31', '0912345680', 'chen@clinic.tw', json.dumps(['星期一', '星期二', '星期三', '星期四', '星期五']), 'full-time'),
            ('NUR002', '張護士', 'Zhang Nurse', '護士', None, 'NUR123457', '2026-12-31', '0912345681', 'zhang@clinic.tw', json.dumps(['星期一', '星期二', '星期四', '星期五', '星期六']), 'full-time'),
            ('LAB001', '劉技術員', 'Liu Technician', '檢驗技術員', None, 'LAB123456', '2026-12-31', '0912345682', 'liu@clinic.tw', json.dumps(['星期一', '星期二', '星期三', '星期四', '星期五']), 'full-time'),
            ('ADM001', '林行政', 'Lin Admin', '行政助理', None, None, None, '0912345683', 'lin@clinic.tw', json.dumps(['星期一', '星期二', '星期三', '星期四', '星期五']), 'full-time'),
        ]

        count = 0
        for staff_id, name, name_en, pos, spec, lic, lic_exp, phone, email, days, shift in staff:
            try:
                self.cursor.execute('''
                    INSERT INTO clinic_staff
                    (clinic_id, staff_id, staff_name, staff_name_english, position, specialty,
                     license_number, license_expiry, phone, email, available_days, shift_type,
                     is_active, hire_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                ''', (clinic_id, staff_id, name, name_en, pos, spec, lic, lic_exp, phone, email, days, shift, datetime.now().date()))
                count += 1
            except Exception as e:
                print(f"⚠️  Error adding staff {name}: {e}")

        self.conn.commit()
        print(f"✓ Added {count} staff members")
        return count

    def populate_clinic_protocols(self):
        """Add sample clinical protocols."""
        print("📋 Adding clinical protocols...")

        self.cursor.execute("SELECT id FROM clinic_info LIMIT 1")
        clinic_id_row = self.cursor.fetchone()
        if not clinic_id_row:
            return 0

        clinic_id = clinic_id_row[0]

        protocols = [
            {
                'protocol_name': '標準體檢流程',
                'protocol_category': '檢查',
                'description': '日常患者體檢的標準操作流程',
                'procedure_steps': json.dumps(['測量身高體重', '檢查血壓', '體格檢查', '記錄結果']),
                'equipment_needed': json.dumps(['血壓計', '身高體重計', '聽診器']),
                'safety_precautions': json.dumps(['使用一次性用具', '手套消毒', '患者隱私保護']),
                'responsible_staff': '護士',
                'indication': '一般健康檢查',
                'approval_status': 'approved',
            },
            {
                'protocol_name': '血液抽樣',
                'protocol_category': '檢驗',
                'description': '血液樣本採集的標準操作流程',
                'procedure_steps': json.dumps(['患者識別確認', '準備採集點', '抽取血液', '樣本標記']),
                'equipment_needed': json.dumps(['採血針', '採血管', '棉球', '紗布']),
                'safety_precautions': json.dumps(['穿著防護衣', '使用無菌採血針', '廢棄物處理規範']),
                'responsible_staff': '檢驗技術員',
                'indication': '血液檢驗',
                'approval_status': 'approved',
            },
        ]

        count = 0
        for proto in protocols:
            try:
                self.cursor.execute('''
                    INSERT INTO clinic_protocols
                    (clinic_id, protocol_name, protocol_category, description, procedure_steps,
                     equipment_needed, safety_precautions, responsible_staff, indication,
                     approval_status, is_active, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                ''', (clinic_id, proto['protocol_name'], proto['protocol_category'],
                      proto['description'], proto['procedure_steps'], proto['equipment_needed'],
                      proto['safety_precautions'], proto['responsible_staff'],
                      proto['indication'], proto['approval_status'], 'ADM001'))
                count += 1
            except Exception as e:
                print(f"⚠️  Error adding protocol {proto['protocol_name']}: {e}")

        self.conn.commit()
        print(f"✓ Added {count} clinical protocols")
        return count

    def populate_clinic_supplies(self):
        """Add clinic supplies/inventory."""
        print("📦 Adding clinic supplies...")

        self.cursor.execute("SELECT id FROM clinic_info LIMIT 1")
        clinic_id_row = self.cursor.fetchone()
        if not clinic_id_row:
            return 0

        clinic_id = clinic_id_row[0]

        supplies = [
            ('醫用手套', '耗材', 500, 100, 1000, 'box', '台灣醫療用品公司', '(02) 1234-5678', 7, 25.0, 'TWD'),
            ('消毒酒精', '耗材', 30, 5, 50, 'bottle', '台灣醫療用品公司', '(02) 1234-5678', 5, 150.0, 'TWD'),
            ('抗生素藥物', '藥物', 200, 50, 500, 'box', '藥廠供應商', '(02) 9876-5432', 10, 500.0, 'TWD'),
            ('綁帶', '耗材', 100, 20, 200, 'roll', '台灣醫療用品公司', '(02) 1234-5678', 7, 45.0, 'TWD'),
        ]

        count = 0
        for name, cat, qty, min_qty, max_qty, unit, supplier, supplier_ph, lead, cost, curr in supplies:
            try:
                self.cursor.execute('''
                    INSERT INTO clinic_supplies
                    (clinic_id, supply_name, supply_category, quantity_on_hand,
                     minimum_quantity, maximum_quantity, unit, supplier_name,
                     supplier_phone, lead_time_days, unit_cost, currency, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ''', (clinic_id, name, cat, qty, min_qty, max_qty, unit, supplier, supplier_ph, lead, cost, curr))
                count += 1
            except Exception as e:
                print(f"⚠️  Error adding supply {name}: {e}")

        self.conn.commit()
        print(f"✓ Added {count} supplies")
        return count


def main():
    parser = argparse.ArgumentParser(description='Populate medical and clinic databases')
    parser.add_argument('--medical', action='store_true', help='Populate medical.db only')
    parser.add_argument('--clinic', action='store_true', help='Populate clinic.db only')
    parser.add_argument('--all', action='store_true', help='Populate both databases')

    args = parser.parse_args()

    # Default to --all if no args specified
    if not (args.medical or args.clinic or args.all):
        args.all = True

    print("=" * 60)
    print("🗄️  DATABASE POPULATION SCRIPT")
    print("=" * 60)

    total_medical = 0
    total_clinic = 0

    if args.medical or args.all:
        print("\n📊 Populating medical.db...")
        try:
            med_pop = MedicalDatabasePopulator(MEDICAL_DB)
            total_medical += med_pop.populate_medical_knowledge()
            total_medical += med_pop.populate_medical_conditions()
            total_medical += med_pop.populate_medical_terminology()
            med_pop.close()
        except Exception as e:
            print(f"❌ Error populating medical.db: {e}")

    if args.clinic or args.all:
        print("\n📊 Populating clinic.db...")
        try:
            clinic_pop = ClinicDatabasePopulator(CLINIC_DB)
            total_clinic += clinic_pop.populate_clinic_info()
            total_clinic += clinic_pop.populate_clinic_schedules()
            total_clinic += clinic_pop.populate_clinic_staff()
            total_clinic += clinic_pop.populate_clinic_protocols()
            total_clinic += clinic_pop.populate_clinic_supplies()
            clinic_pop.close()
        except Exception as e:
            print(f"❌ Error populating clinic.db: {e}")

    print("\n" + "=" * 60)
    print(f"✅ Population Complete!")
    print(f"   Medical.db: {total_medical} records")
    print(f"   Clinic.db: {total_clinic} records")
    print("=" * 60)


if __name__ == '__main__':
    main()
