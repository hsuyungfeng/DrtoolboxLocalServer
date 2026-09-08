#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to export medical nodes from DrtoolboxLocalServer's SQLite database
and merge them into SoapVoice's keywords.json file.
"""

import os
import json
import sqlite3

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLINIC_DB = os.path.join(PROJECT_DIR, 'data', 'db', 'clinic.db')
KEYWORDS_JSON = '/home/hsuyungfeng/SoapVoice/keywords.json'

def export_keywords():
    if not os.path.exists(CLINIC_DB):
        print(f"Error: clinic.db not found at {CLINIC_DB}")
        return
    if not os.path.exists(KEYWORDS_JSON):
        print(f"Error: keywords.json not found at {KEYWORDS_JSON}")
        return
        
    print("Reading existing keywords.json from SoapVoice...")
    with open(KEYWORDS_JSON, 'r', encoding='utf-8') as f:
        keywords = json.load(f)
        
    # Ensure keys exist
    for key in ["subjective", "objective", "assessment", "plan"]:
        if key not in keywords:
            keywords[key] = []
            
    # Convert lists to sets for fast unique additions
    subjective_set = set(keywords["subjective"])
    objective_set = set(keywords["objective"])
    assessment_set = set(keywords["assessment"])
    plan_set = set(keywords["plan"])
    
    print("Connecting to clinic.db...")
    conn = sqlite3.connect(CLINIC_DB)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name, label FROM medical_nodes")
    rows = cursor.fetchall()
    
    print(f"Loaded {len(rows)} nodes from clinic.db. Mapping and merging...")
    
    added_counts = {"subjective": 0, "objective": 0, "assessment": 0, "plan": 0}
    
    for name, label in rows:
        name = name.strip()
        if not name:
            continue
            
        if label == "Symptom":
            if name not in subjective_set:
                subjective_set.add(name)
                added_counts["subjective"] += 1
        elif label == "Check":
            if name not in objective_set:
                objective_set.add(name)
                added_counts["objective"] += 1
        elif label == "Disease":
            if name not in assessment_set:
                assessment_set.add(name)
                added_counts["assessment"] += 1
        elif label in ["Drug", "Food"]:
            if name not in plan_set:
                plan_set.add(name)
                added_counts["plan"] += 1
                
    # Sort and save back to keywords.json
    keywords["subjective"] = sorted(list(subjective_set))
    keywords["objective"] = sorted(list(objective_set))
    keywords["assessment"] = sorted(list(assessment_set))
    keywords["plan"] = sorted(list(plan_set))
    
    print("Writing merged keywords back to keywords.json...")
    with open(KEYWORDS_JSON, 'w', encoding='utf-8') as f:
        json.dump(keywords, f, ensure_ascii=False, indent=2)
        
    conn.close()
    print("\nKeywords exported successfully!")
    print(f"Added Subjective (Symptoms): {added_counts['subjective']}")
    print(f"Added Objective (Checks): {added_counts['objective']}")
    print(f"Added Assessment (Diseases): {added_counts['assessment']}")
    print(f"Added Plan (Drugs/Foods): {added_counts['plan']}")

if __name__ == '__main__':
    export_keywords()
