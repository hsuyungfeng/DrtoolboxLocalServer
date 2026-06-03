#!/usr/bin/env python3
"""
Generate batch graph outputs for batches 2-8 using existing extract results.
"""

import json
import os
import re
from pathlib import Path

PROJECT_ROOT = Path("/home/hsuyungfeng/DrtoolboxLocalServer")
INTERMEDIATE = PROJECT_ROOT / ".understand-anything" / "intermediate"
TMP = PROJECT_ROOT / ".understand-anything" / "tmp"

IS_FLASK = True

def read_file_content(rel_path):
    try:
        return (PROJECT_ROOT / rel_path).read_text(encoding="utf-8", errors="replace")
    except:
        return None

def classify_file_type(file_category, language, path, extract_result):
    if file_category == "config":
        return "config"
    if file_category == "docs":
        return "document"
    if language == "service":
        return "resource"
    if language in ("key", "txt"):
        return "resource"
    if language == "jsonl":
        return "data"
    return "file"

def generate_summary(path, language, file_category, extract_result):
    sections = extract_result.get("sections", [])
    functions = extract_result.get("functions", [])
    classes = extract_result.get("classes", [])
    endpoints = extract_result.get("endpoints", [])
    definitions = extract_result.get("definitions", [])
    
    if file_category == "config":
        return f"設定檔，包含 {len(definitions) if definitions else 0} 個設定項目。"
    if file_category == "docs":
        if sections:
            return f"文件，包含 {len(sections)} 個章節，概述專案相關資訊。"
        return "文件。"
    if language == "service":
        return "系統服務組態檔案 (systemd service)。"
    if language in ("key",):
        return "金鑰檔案。"
    if language == "jsonl":
        lines = extract_result.get("totalLines", 0)
        return f"JSONL 資料檔案，共 {lines} 列。"
    
    parts = []
    if classes:
        cls_names = [c["name"] for c in classes[:3]]
        parts.append(f"定義類別 {', '.join(cls_names)}")
    if functions:
        fn_names = [f["name"] for f in functions[:3]]
        parts.append(f"提供函數 {', '.join(fn_names)}")
    if endpoints:
        parts.append(f"定義 {len(endpoints)} 個端點")
    
    if parts:
        return f"提供{'、'.join(parts)}。"
    
    if "templates" in path and path.endswith(".html"):
        return "HTML 模板檔案。"
    if "static" in path:
        return "靜態資源檔案。"
    if "scripts" in path:
        return f"Shell 腳本，共 {extract_result.get('totalLines', 0)} 行。"
    return f"{language} 檔案，共 {extract_result.get('totalLines', 0)} 行。"

def generate_tags(path, language, file_category, extract_result):
    tags = set()
    
    if file_category == "config":
        tags.add("設定")
        tags.add("configuration")
        return list(tags)
    if file_category == "docs":
        tags.add("文件")
        tags.add("documentation")
        return list(tags)
    
    metrics = extract_result.get("metrics", {})
    functions = extract_result.get("functions", [])
    classes = extract_result.get("classes", [])
    endpoints = extract_result.get("endpoints", [])
    
    if IS_FLASK:
        if "routes" in path and ".py" in path:
            tags.add("api-handler")
            tags.add("routing")
        if "app.py" in path:
            tags.add("entry-point")
            tags.add("配置")
        if "templates" in path and ".html" in path:
            tags.add("ui")
        if "static" in path:
            tags.add("assets")
        if "services" in path and ".py" in path:
            tags.add("服務")
            tags.add("business-logic")
        if "db" in path and ".py" in path:
            tags.add("資料層")
            tags.add("database")
        if "rag" in path.lower() and ".py" in path:
            tags.add("RAG")
            tags.add("檢索")
        if "skills" in path and ".py" in path:
            tags.add("工具")
            tags.add("skill")
        if "agent" in path and ".py" in path:
            tags.add("代理")
            tags.add("agent")
        if "llm" in path.lower():
            tags.add("LLM")
            tags.add("推理")
        if "data_loader" in path:
            tags.add("資料載入")
            tags.add("ETL")
        if "rag_engine" in path:
            tags.add("RAG")
            tags.add("檢索")
        if "pageindex" in path.lower():
            tags.add("索引")
            tags.add("indexing")
        if "clinical" in path.lower():
            tags.add("臨床")
            tags.add("分析")
        if "search" in path.lower():
            tags.add("搜尋")
            tags.add("search")
    
    if endpoints:
        tags.add("端點")
        tags.add("endpoint")
    if classes:
        tags.add("類別")
        tags.add("class")
    if functions and len(functions) > 3:
        tags.add("函數")
        tags.add("function")
    
    if "template" in path.lower():
        tags.add("模板")
        tags.add("template")
    if "static" in path:
        tags.add("靜態")
        tags.add("static")
    if "scripts" in path:
        if language == "shell":
            tags.add("腳本")
            tags.add("script")
        elif language == "python":
            tags.add("工具腳本")
            tags.add("utility")
    
    if not tags:
        tags.add(language) if language != "unknown" else tags.add("未知")
    
    return list(tags)

def build_nodes_and_edges(batch_index, batch_files, extract_results, import_data, neighbor_map):
    nodes = []
    edges = []
    file_id_map = {}
    
    for file_info in batch_files:
        path = file_info["path"]
        language = file_info["language"]
        file_category = file_info["fileCategory"]
        
        ext_result = None
        if extract_results:
            for r in extract_results:
                if r.get("path") == path:
                    ext_result = r
                    break
        
        file_type = classify_file_type(file_category, language, path, ext_result) if ext_result else "file"
        
        if file_type == "config":
            node_id = f"config:{path}"
        elif file_type == "document":
            node_id = f"document:{path}"
        elif file_type == "resource":
            node_id = f"resource:{path}"
        else:
            node_id = f"file:{path}"
        
        file_id_map[path] = node_id
        
        summary = generate_summary(path, language, file_category, ext_result) if ext_result else f"{language} 檔案。"
        tags = generate_tags(path, language, file_category, ext_result) if ext_result else [language]
        
        complexity = "moderate"
        total_lines = ext_result.get("totalLines", file_info.get("sizeLines", 0)) if ext_result else file_info.get("sizeLines", 0)
        metrics = ext_result.get("metrics", {}) if ext_result else {}
        fn_count = metrics.get("functionCount", 0)
        if total_lines > 500 or fn_count > 20:
            complexity = "complex"
        elif total_lines < 30 and fn_count < 3:
            complexity = "simple"
        
        # Functions as sub-nodes
        functions = ext_result.get("functions", []) if ext_result else []
        classes = ext_result.get("classes", []) if ext_result else []
        
        for fn in functions:
            fn_id = f"function:{path}:{fn['name']}"
            nodes.append({
                "id": fn_id,
                "type": "function",
                "name": fn["name"],
                "filePath": path,
                "summary": f"函數 {fn['name']}，起始於第 {fn.get('startLine', '?')} 行。",
                "tags": ["函數", "function"],
                "complexity": "simple",
            })
            edges.append({
                "source": node_id,
                "target": fn_id,
                "type": "contains",
                "description": f"{os.path.basename(path)} 包含函數 {fn['name']}"
            })
        
        for cls in classes:
            cls_id = f"class:{path}:{cls['name']}"
            nodes.append({
                "id": cls_id,
                "type": "class",
                "name": cls["name"],
                "filePath": path,
                "summary": f"類別 {cls['name']}，起始於第 {cls.get('startLine', '?')} 行。",
                "tags": ["類別", "class"],
                "complexity": "moderate" if cls.get("methods", []) else "simple",
            })
            edges.append({
                "source": node_id,
                "target": cls_id,
                "type": "contains",
                "description": f"{os.path.basename(path)} 定義類別 {cls['name']}"
            })
        
        nodes.append({
            "id": node_id,
            "type": file_type,
            "name": os.path.basename(path),
            "filePath": path,
            "summary": summary,
            "tags": tags,
            "complexity": complexity,
        })
    
    # Import edges from batchImportData
    for path, imports in import_data.items():
        source_id = file_id_map.get(path)
        if not source_id:
            continue
        for imp in imports:
            target_path = imp
            target_id = file_id_map.get(target_path)
            if target_id:
                edges.append({
                    "source": source_id,
                    "target": target_id,
                    "type": "imports",
                    "description": f"{os.path.basename(path)} 匯入 {os.path.basename(target_path)}"
                })
    
    # Cross-batch neighbors from neighborMap
    if neighbor_map:
        for path, neighbors in neighbor_map.items():
            source_id = file_id_map.get(path)
            if not source_id:
                continue
            for neighbor in neighbors:
                neighbor_path = neighbor.get("path", "")
                target_id = file_id_map.get(neighbor_path)
                if target_id:
                    # Avoid duplicate edges
                    edge_key = (source_id, target_id, "imports")
                    if not any((e["source"], e["target"], e["type"]) == edge_key for e in edges):
                        edges.append({
                            "source": source_id,
                            "target": target_id,
                            "type": "imports",
                            "description": f"{os.path.basename(path)} 匯入 {neighbor_path}"
                        })
    
    # For Python files, scan imports against all files in project
    for file_info in batch_files:
        p = file_info["path"]
        if not p.endswith(".py"):
            continue
        content = read_file_content(p)
        if not content:
            continue
        # Find from X import Y patterns
        imports = re.findall(r'from\s+([\w.]+)\s+import', content)
        for imp in imports:
            parts = imp.split(".")
            if len(parts) >= 2 and parts[0] in ("src", "config", "scripts"):
                candidate = os.path.join(*parts) + ".py"
                if candidate in file_id_map:
                    edge_key = (file_id_map[p], file_id_map[candidate], "imports")
                    if not any((e["source"], e["target"], e["type"]) == edge_key for e in edges):
                        edges.append({
                            "source": file_id_map[p],
                            "target": file_id_map[candidate],
                            "type": "imports",
                            "description": f"{os.path.basename(p)} 匯入 {os.path.basename(candidate)}"
                        })
    
    return nodes, edges


def main():
    for batch_index in [2, 3, 4, 5, 6, 7, 8]:
        with open(INTERMEDIATE / "batches.json") as f:
            batches_data = json.load(f)
        
        batch_def = None
        for b in batches_data["batches"]:
            if b["batchIndex"] == batch_index:
                batch_def = b
                break
        
        if not batch_def:
            print(f"Batch {batch_index} not found")
            continue
        
        batch_files = batch_def["files"]
        batch_import_data = batch_def.get("batchImportData", {})
        neighbor_map = batch_def.get("neighborMap", {})
        
        extract_path = TMP / f"ua-file-extract-results-{batch_index}.json"
        extract_results = []
        if extract_path.exists():
            with open(extract_path) as f:
                extract_data = json.load(f)
            extract_results = extract_data.get("results", [])
        
        nodes, edges = build_nodes_and_edges(
            batch_index, batch_files, extract_results, batch_import_data, neighbor_map
        )
        
        output = {
            "batchIndex": batch_index,
            "nodes": nodes,
            "edges": edges,
        }
        
        output_path = INTERMEDIATE / f"batch-{batch_index}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"Batch {batch_index}: {len(nodes)} nodes, {len(edges)} edges ({len(batch_files)} files)")


if __name__ == "__main__":
    main()
