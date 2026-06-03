#!/usr/bin/env python3
"""
Generate batch graph outputs from extract results and file content.
Takes existing extract results and produces proper GraphNode/GraphEdge objects.
"""

import json
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path("/home/hsuyungfeng/DrtoolboxLocalServer")
INTERMEDIATE = PROJECT_ROOT / ".understand-anything" / "intermediate"
TMP = PROJECT_ROOT / ".understand-anything" / "tmp"

# Project name for context
PROJECT_NAME = "DrtoolboxLocalServer"

# Flask framework detection
IS_FLASK = True

def read_file_content(rel_path):
    """Read file content, return None if not found."""
    try:
        return (PROJECT_ROOT / rel_path).read_text(encoding="utf-8", errors="replace")
    except:
        return None

def classify_file_type(file_category, language, path, extract_result):
    """Classify a file's primary type."""
    if file_category == "config":
        return "config"
    if file_category == "docs":
        return "document"
    if file_category == "markup" and path.endswith(".html"):
        return "file"  # templates are files
    if language == "service":
        return "resource"
    if language in ("key", "txt"):
        return "resource"
    if language == "jsonl":
        return "data"
    return "file"

def generate_summary(path, language, file_category, extract_result):
    """Generate a zh-TW summary for a file."""
    sections = extract_result.get("sections", [])
    functions = extract_result.get("functions", [])
    classes = extract_result.get("classes", [])
    endpoints = extract_result.get("endpoints", [])
    definitions = extract_result.get("definitions", [])
    metrics = extract_result.get("metrics", {})
    
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
    
    # Code/markup files
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
    
    # Fallback based on path
    if "templates" in path and path.endswith(".html"):
        return "HTML 模板檔案。"
    if "static" in path:
        return "靜態資源檔案。"
    if "scripts" in path:
        return f"Shell 腳本，共 {extract_result.get('totalLines', 0)} 行。"
    return f"{language} 檔案，共 {extract_result.get('totalLines', 0)} 行。"

def generate_tags(path, language, file_category, extract_result):
    """Generate tags for a file."""
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
    definitions = extract_result.get("definitions", [])
    
    # Flask framework tags
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

def get_edge_type(import_source, import_target):
    """Determine edge type between two imports."""
    return "imports"

def build_nodes_and_edges(batch_index, batch_files, extract_results, import_data):
    """Build nodes and edges for a batch."""
    nodes = []
    edges = []
    
    # First pass: create nodes for all files
    file_id_map = {}
    
    for i, file_info in enumerate(batch_files):
        path = file_info["path"]
        language = file_info["language"]
        file_category = file_info["fileCategory"]
        
        # Find extract result
        ext_result = None
        if extract_results:
            for r in extract_results:
                if r.get("path") == path:
                    ext_result = r
                    break
        
        if not ext_result:
            # Fallback: create minimal node
            node_id = f"file:{path}"
            file_id_map[path] = node_id
            node = {
                "id": node_id,
                "type": "file",
                "name": os.path.basename(path),
                "filePath": path,
                "summary": f"{language} 檔案，共 {file_info.get('sizeLines', 0)} 行。",
                "tags": [language if language != "unknown" else "未知"],
                "complexity": "simple",
            }
            nodes.append(node)
            continue
        
        # Classify type
        file_type = classify_file_type(file_category, language, path, ext_result)
        
        # Generate node ID
        if file_type == "config":
            node_id = f"config:{path}"
        elif file_type == "document":
            node_id = f"document:{path}"
        elif file_type == "resource":
            node_id = f"resource:{path}"
        else:
            node_id = f"file:{path}"
        
        file_id_map[path] = node_id
        
        # Generate summary and tags
        summary = generate_summary(path, language, file_category, ext_result)
        tags = generate_tags(path, language, file_category, ext_result)
        
        # Complexity
        complexity = "moderate"
        total_lines = ext_result.get("totalLines", file_info.get("sizeLines", 0))
        metrics = ext_result.get("metrics", {})
        fn_count = metrics.get("functionCount", 0)
        if total_lines > 500 or fn_count > 20:
            complexity = "complex"
        elif total_lines < 30 and fn_count < 3:
            complexity = "simple"
        
        node = {
            "id": node_id,
            "type": file_type,
            "name": os.path.basename(path),
            "filePath": path,
            "summary": summary,
            "tags": tags,
            "complexity": complexity,
        }
        
        # Add functions as sub-nodes for code files
        functions = ext_result.get("functions", [])
        classes = ext_result.get("classes", [])
        
        for fn in functions:
            fn_id = f"function:{path}:{fn['name']}"
            node = {
                "id": fn_id,
                "type": "function",
                "name": fn["name"],
                "filePath": path,
                "summary": f"函數 {fn['name']}，起始於第 {fn.get('startLine', '?')} 行。",
                "tags": ["函數", "function"],
                "complexity": "simple",
            }
            nodes.append(node)
            edges.append({
                "source": node_id,
                "target": fn_id,
                "type": "contains",
                "description": f"{os.path.basename(path)} 包含函數 {fn['name']}"
            })
        
        for cls in classes:
            cls_id = f"class:{path}:{cls['name']}"
            node = {
                "id": cls_id,
                "type": "class",
                "name": cls["name"],
                "filePath": path,
                "summary": f"類別 {cls['name']}，起始於第 {cls.get('startLine', '?')} 行。",
                "tags": ["類別", "class"],
                "complexity": "moderate" if cls.get("methods", []) else "simple",
            }
            nodes.append(node)
            edges.append({
                "source": node_id,
                "target": cls_id,
                "type": "contains",
                "description": f"{os.path.basename(path)} 定義類別 {cls['name']}"
            })
        
        # Main file node
        file_node = {
            "id": node_id,
            "type": file_type,
            "name": os.path.basename(path),
            "filePath": path,
            "summary": summary,
            "tags": tags,
            "complexity": complexity,
        }
        nodes.append(file_node)
    
    # Second pass: create import edges using batchImportData
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
    
    # For Python files, add depends_on edges between related files
    for path, file_info in enumerate(batch_files):
        p = file_info["path"]
        if not p.endswith(".py"):
            continue
        content = read_file_content(p)
        if not content:
            continue
        
        # Find imports that reference other files in this batch
        imports = re.findall(r'from\s+(\.\w+(?:\.\w+)*)\s+import', content)
        imports += re.findall(r'import\s+(\.\w+(?:\.\w+)*)', content)
        
        for imp in imports:
            # Convert dotted import to file path
            parts = imp.split(".")
            candidate = os.path.join(*parts) + ".py"
            if candidate in file_id_map:
                edges.append({
                    "source": file_id_map[p],
                    "target": file_id_map[candidate],
                    "type": "imports",
                    "description": f"{os.path.basename(p)} 匯入 {os.path.basename(candidate)}"
                })
    
    return nodes, edges


def main():
    all_files_analyzed = 0
    
    for batch_index in [1, 9, 10, 11, 12, 13, 14]:
        # Load batch definition
        with open(INTERMEDIATE / "batches.json") as f:
            batches_data = json.load(f)
        
        batch_def = None
        for b in batches_data["batches"]:
            if b["batchIndex"] == batch_index:
                batch_def = b
                break
        
        if not batch_def:
            print(f"Batch {batch_index} not found in batches.json")
            continue
        
        batch_files = batch_def["files"]
        batch_import_data = batch_def.get("batchImportData", {})
        neighbor_map = batch_def.get("neighborMap", {})
        
        # Load extract results
        extract_path = TMP / f"ua-file-extract-results-{batch_index}.json"
        extract_results = []
        if extract_path.exists():
            with open(extract_path) as f:
                extract_data = json.load(f)
            extract_results = extract_data.get("results", [])
        
        # Build nodes and edges
        nodes, edges = build_nodes_and_edges(
            batch_index, batch_files, extract_results, batch_import_data
        )
        
        # Write batch output
        output = {
            "batchIndex": batch_index,
            "nodes": nodes,
            "edges": edges,
        }
        
        output_path = INTERMEDIATE / f"batch-{batch_index}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        all_files_analyzed += len(batch_files)
        print(f"Batch {batch_index}: {len(nodes)} nodes, {len(edges)} edges ({len(batch_files)} files)")
    
    print(f"\nTotal files analyzed: {all_files_analyzed}")


if __name__ == "__main__":
    main()
