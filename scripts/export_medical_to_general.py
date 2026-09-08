#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exporter script to convert medical graph JSON data into general medical documents.
Groups diseases into text files under `./data/documents/general/` for RAG index ingestion.
"""

import os
import json
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(PROJECT_DIR, 'chatbot-base-on-Knowledge-Graph', 'data', 'medical.json')
OUTPUT_DIR = os.path.join(PROJECT_DIR, 'data', 'documents', 'general')

def export_data():
    if not os.path.exists(JSON_PATH):
        print(f"Error: Source file not found at {JSON_PATH}", file=sys.stderr)
        sys.exit(1)
        
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("Reading medical.json and generating text files for RAG...")
    
    diseases = []
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                diseases.append(record)
            except Exception as e:
                continue
                
    total_diseases = len(diseases)
    print(f"Loaded {total_diseases} diseases.")
    
    # Batch configuration: 200 diseases per file
    batch_size = 200
    for idx in range(0, total_diseases, batch_size):
        batch = diseases[idx:idx+batch_size]
        batch_num = idx // batch_size + 1
        output_file = os.path.join(OUTPUT_DIR, f"medical_kb_batch_{batch_num}.txt")
        
        content_parts = []
        for record in batch:
            name = record.get("name", "").strip()
            if not name:
                continue
                
            doc_str = f"【疾病名稱】：{name}\n"
            
            desc = record.get("desc")
            if desc:
                doc_str += f"【疾病描述】：{desc}\n"
            cause = record.get("cause")
            if cause:
                doc_str += f"【疾病病因】：{cause}\n"
            prevent = record.get("prevent")
            if prevent:
                doc_str += f"【預防措施】：{prevent}\n"
            cure_lasttime = record.get("cure_lasttime")
            if cure_lasttime:
                doc_str += f"【治療週期】：{cure_lasttime}\n"
            cured_prob = record.get("cured_prob")
            if cured_prob:
                doc_str += f"【治癒機率】：{cured_prob}\n"
                
            # Relationships
            def add_list_field(label, val):
                if val:
                    if isinstance(val, str):
                        val = [val]
                    items = [str(x).strip() for x in val if str(x).strip()]
                    if items:
                        return f"【{label}】：{'、'.join(items)}\n"
                return ""
                
            doc_str += add_list_field("伴隨症狀", record.get("symptom"))
            doc_str += add_list_field("併發症", record.get("acompany"))
            doc_str += add_list_field("推薦藥品", record.get("recommand_drug"))
            doc_str += add_list_field("常用藥品", record.get("common_drug"))
            doc_str += add_list_field("需要做的檢查", record.get("check"))
            doc_str += add_list_field("宜吃食物", record.get("do_eat"))
            doc_str += add_list_field("忌吃食物", record.get("no_eat"))
            doc_str += add_list_field("推薦食譜", record.get("recommand_eat"))
            
            content_parts.append(doc_str + "\n" + "="*40 + "\n")
            
        with open(output_file, 'w', encoding='utf-8') as out_f:
            out_f.write("\n".join(content_parts))
            
        print(f"Exported batch {batch_num} to {os.path.basename(output_file)}")
        
    print(f"\nSuccess: Exported {total_diseases} diseases into {batch_num} general medical documents.")

if __name__ == '__main__':
    export_data()
