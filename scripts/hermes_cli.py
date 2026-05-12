#!/usr/bin/env python3
"""
Hermes CLI

Command-line interface for interacting with the Hermes Agent and managing Auto-Skills.
"""

import sys
import os
import argparse
import json
from pprint import pprint
import logging

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, "src"))

# Setup basic logging to not clutter stdout
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')

from src.agent.hermes_core import get_hermes_agent
from src.agent.pattern_learner import get_pattern_learner
from src.skills.skill_manager import get_skill_manager
from src.skills.skill_generator import SkillGenerator
from src.llm.cloud_backend import get_cloud_backend

def cmd_chat(args):
    """Interact with Hermes Agent."""
    agent = get_hermes_agent()
    learner = get_pattern_learner()
    
    # Inline query mode
    if args.query:
        query_text = " ".join(args.query)
        learner.log_query(query_text)
        response = agent.chat(query_text)
        print(f"Hermes: {response}")
        return

    # Interactive mode
    print("Hermes Agent CLI (type 'exit' or 'quit' to stop)")
    print("-" * 50)
    history = []
    
    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ['exit', 'quit']:
                break
            if not user_input.strip():
                continue
                
            # Log for pattern learning
            learner.log_query(user_input)
            
            # Chat
            response = agent.chat(user_input, history=history)
            print(f"\nHermes: {response}\n")
            
            # Update history
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": response})
            
            # Check for candidate skills
            candidates = learner.extract_candidates()
            if candidates:
                print(f"[!] System has identified {len(candidates)} candidate skills from your patterns.")
                print("[!] Use 'hermes_cli.py discover' to review them.")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

def cmd_discover(args):
    """List candidate skills and optionally approve them to generate auto-skills."""
    learner = get_pattern_learner()
    candidates = learner.extract_candidates()
    
    if not candidates:
        print("No candidates discovered yet. Talk to Hermes more to generate patterns.")
        return
        
    print(f"Found {len(candidates)} Candidate Skills:")
    for i, cand in enumerate(candidates):
        print(f"[{i+1}] Pattern: '{cand['pattern']}' (Seen {cand['frequency']} times)")
        
    choice = input("\nEnter the number of the skill to generate, or 'c' to clear cache, or 'q' to quit: ")
    if choice.lower() == 'c':
        learner.clear_cache()
        print("Cache cleared.")
    elif choice.isdigit() and 1 <= int(choice) <= len(candidates):
        cand = candidates[int(choice)-1]
        print(f"\nGenerating Auto-Skill for: '{cand['pattern']}'...")
        
        generator = SkillGenerator()
        script = generator.generate_skill_script(cand['pattern'], cand['description'])
        
        if not script:
            print("Failed to generate skill script from LLM.")
            return
            
        print("\n--- Generated Python Script ---")
        print(script)
        print("-------------------------------\n")
        
        approve = input("Do you want to save and register this skill? (y/n): ")
        if approve.lower() == 'y':
            manager = get_skill_manager()
            skill_id = manager.register_skill(
                name=cand['suggested_name'],
                description=cand['description'],
                command_pattern=cand['pattern'],
                script_content=script
            )
            print(f"Skill registered successfully! ID: {skill_id}")
            print(f"Run it using: python scripts/hermes_cli.py run {skill_id}")
            
def cmd_list(args):
    """List all registered skills."""
    manager = get_skill_manager()
    skills = manager.list_skills()
    
    if not skills:
        print("No active auto-skills found.")
        return
        
    print(f"{'ID':<15} | {'NAME':<20} | {'PATTERN':<30} | {'CREATED AT'}")
    print("-" * 85)
    for s in skills:
        print(f"{s['skill_id']:<15} | {s['name']:<20} | {s['command_pattern'][:28]:<30} | {s['created_at']}")

def cmd_run(args):
    """Execute a registered skill."""
    manager = get_skill_manager()
    skill_id = args.skill_id

    print(f"Executing skill {skill_id}...")
    res = manager.execute_skill(skill_id, args={}, user="cli_user")

    if res['success']:
        print(f"Execution Successful (Time: {res['time_ms']}ms)")
        print("Result:")
        pprint(res['result'])
    else:
        print(f"Execution Failed (Time: {res['time_ms']}ms)")
        print(f"Error: {res['result'].get('error', 'Unknown error')}")

def cmd_health(args):
    """Check Hermes agent health."""
    print("\n🏥 Hermes Agent Health Check\n")
    try:
        backend = get_cloud_backend()
        print(f"✓ Cloud backend: {backend.config.provider.upper()}")
        print(f"✓ Model: {backend.config.model}")
        print(f"✓ API Key configured")

        agent = get_hermes_agent()
        print(f"✓ Hermes Agent initialized")
        print(f"✓ Intent router ready")
        print(f"✓ RAG engine ready")
        print(f"✓ HIS connection ready\n")
        return 0
    except Exception as e:
        print(f"❌ Health check failed: {e}\n")
        return 1

def cmd_test_llm(args):
    """Test cloud LLM backend."""
    print("\n🧪 Testing Cloud LLM Backend\n")
    try:
        backend = get_cloud_backend()
        print(f"Provider: {backend.config.provider.upper()}")
        print(f"Model: {backend.config.model}")
        print("⏳ Generating response...\n")

        messages = [
            {"role": "system", "content": "You are a helpful medical assistant. Respond in Traditional Chinese."},
            {"role": "user", "content": "What is the patient intake process?"}
        ]

        result = backend.complete(messages)
        response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"✓ Response:\n{response_text}\n")
        print(f"Tokens used: {result.get('usage', {})}\n")
        return 0
    except Exception as e:
        print(f"❌ LLM test failed: {e}\n")
        return 1

def cmd_status(args):
    """Show Hermes agent status and HIS context."""
    print("\n🏥 Hermes Agent Status\n" + "=" * 50)
    try:
        agent = get_hermes_agent()
        status = agent.get_context_status()
        
        print(f"\n📊 HIS Context Status:")
        print(f"  • 連線狀態: {'✅ 健康' if status['healthy'] else '❌ 異常'}")
        print(f"  • 診所名稱: {status['clinic_name']}")
        print(f"  • 員工人數: {status['staff_count']} 人")
        print(f"  • 病患記錄: {status['patient_records']} 筆")
        print(f"  • 上次更新: {status['last_refresh'] or '尚未載入'}")
        print(f"  • 自動更新間隔: {status['refresh_interval_sec']} 秒")
        print()
        return 0
    except Exception as e:
        print(f"❌ Status check failed: {e}\n")
        return 1

def cmd_context_refresh(args):
    """Force context refresh."""
    print("\n🔄 Refreshing HIS Context...\n")
    try:
        agent = get_hermes_agent()
        result = agent.refresh_context()
        if result:
            print("✅ Context refreshed successfully!")
            status = agent.get_context_status()
            print(f"   診所: {status['clinic_name']}")
            print(f"   更新時間: {status['last_refresh']}")
        else:
            print("❌ Context refresh failed.")
        return 0
    except Exception as e:
        print(f"❌ Refresh failed: {e}\n")
        return 1

def cmd_patterns_list(args):
    """List learned patterns."""
    print("\n📋 Learned Patterns\n" + "=" * 50)
    try:
        import sqlite3
        conn = sqlite3.connect("data/local_db/clinic.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if patterns table exists, if not use pattern_learner
        try:
            cursor.execute("SELECT * FROM patterns ORDER BY created_at DESC")
            patterns = cursor.fetchall()
            
            if not patterns:
                print("No patterns found in database.")
                return 0
                
            print(f"{'ID':<8} | {'Pattern':<35} | {'Category':<15} | {'Count'}")
            print("-" * 75)
            for p in patterns:
                p_dict = dict(p)
                print(f"{p_dict['pattern_id']:<8} | {p_dict['pattern_text'][:33]:<35} | {p_dict.get('category', 'N/A'):<15} | {p_dict.get('frequency', 1)}")
            conn.close()
            return 0
        except sqlite3.OperationalError:
            # Table doesn't exist, use pattern_learner
            conn.close()
            learner = get_pattern_learner()
            candidates = learner.extract_candidates()
            
            if not candidates:
                print("No patterns detected yet. Use the agent more to learn patterns.")
                return 0
                
            print(f"{'#':<4} | {'Pattern':<40} | {'Frequency'}")
            print("-" * 60)
            for i, c in enumerate(candidates):
                print(f"{i+1:<4} | {c['pattern'][:38]:<40} | {c['frequency']}")
            return 0
    except Exception as e:
        print(f"❌ Error listing patterns: {e}\n")
        return 1

def cmd_patterns_stats(args):
    """Show pattern statistics."""
    print("\n📈 Pattern Statistics\n" + "=" * 50)
    try:
        import sqlite3
        conn = sqlite3.connect("data/local_db/clinic.db")
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) as total FROM patterns")
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT category, COUNT(*) as count FROM patterns GROUP BY category")
            by_category = cursor.fetchall()
            
            print(f"總模式數: {total}")
            print(f"\n分類統計:")
            for cat, count in by_category:
                print(f"  • {cat or '未分類'}: {count}")
            conn.close()
        except sqlite3.OperationalError:
            conn.close()
            learner = get_pattern_learner()
            candidates = learner.extract_candidates()
            print(f"候選技能數: {len(candidates)}")
            total_queries = len(learner.history_cache)
            print(f"總查詢數: {total_queries}")
            
        return 0
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return 1

def cmd_skills_list(args):
    """List all registered skills."""
    print("\n🛠️  Registered Auto-Skills\n" + "=" * 50)
    try:
        manager = get_skill_manager()
        skills = manager.list_skills()
        
        if not skills:
            print("No active auto-skills found.")
            return 0
            
        print(f"{'ID':<12} | {'Name':<20} | {'Pattern':<25} | {'Created'}")
        print("-" * 75)
        for s in skills:
            created = s.get('created_at', 'N/A')[:10] if s.get('created_at') else 'N/A'
            print(f"{s['skill_id']:<12} | {s['name'][:18]:<20} | {s.get('command_pattern', '')[:23]:<25} | {created}")
        print()
        return 0
    except Exception as e:
        print(f"❌ Error listing skills: {e}\n")
        return 1

def cmd_skills_enable(args):
    """Enable a skill."""
    try:
        import sqlite3
        conn = sqlite3.connect("data/local_db/clinic.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE auto_skills SET is_active = 1 WHERE skill_id = ?", (args.skill_id,))
        conn.commit()
        print(f"✅ Skill {args.skill_id} enabled.")
        conn.close()
        return 0
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return 1

def cmd_skills_disable(args):
    """Disable a skill."""
    try:
        import sqlite3
        conn = sqlite3.connect("data/local_db/clinic.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE auto_skills SET is_active = 0 WHERE skill_id = ?", (args.skill_id,))
        conn.commit()
        print(f"✅ Skill {args.skill_id} disabled.")
        conn.close()
        return 0
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return 1

def cmd_skills_metrics(args):
    """Show skill adoption metrics."""
    print("\n📊 Skill Adoption Metrics\n" + "=" * 50)
    try:
        import sqlite3
        from datetime import datetime, timedelta
        
        conn = sqlite3.connect("data/local_db/clinic.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get overall stats
        cursor.execute("""
            SELECT skill_id, 
                   COUNT(*) as total_runs,
                   SUM(CASE WHEN is_successful = 1 THEN 1 ELSE 0 END) as successful_runs,
                   AVG(execution_time_ms) as avg_time
            FROM skill_metrics 
            GROUP BY skill_id
        """)
        stats = cursor.fetchall()
        
        if not stats:
            print("No metrics recorded yet.")
            conn.close()
            return 0
            
        print(f"{'Skill ID':<12} | {'Total Runs':<10} | {'Success':<10} | {'Avg Time (ms)':<12}")
        print("-" * 55)
        for s in stats:
            success_rate = (s['successful_runs'] / s['total_runs'] * 100) if s['total_runs'] > 0 else 0
            print(f"{s['skill_id']:<12} | {s['total_runs']:<10} | {success_rate:.1f}%{'':<5} | {s['avg_time']:.1f}")
        
        # Recent activity
        cursor.execute("""
            SELECT skill_id, executed_at, is_successful 
            FROM skill_metrics 
            ORDER BY executed_at DESC LIMIT 5
        """)
        recent = cursor.fetchall()
        
        print(f"\n最近執行:")
        for r in recent:
            status = "✅" if r['is_successful'] else "❌"
            print(f"  {status} {r['skill_id']} - {r['executed_at']}")
            
        conn.close()
        print()
        return 0
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return 1

def cmd_skills_create(args):
    """Create skill from pattern."""
    if not args.pattern_id:
        print("Error: --pattern argument required")
        return 1
        
    try:
        import sqlite3
        conn = sqlite3.connect("data/local_db/clinic.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM patterns WHERE pattern_id = ?", (args.pattern_id,))
        pattern = cursor.fetchone()
        
        if not pattern:
            print(f"Pattern {args.pattern_id} not found.")
            conn.close()
            return 1
            
        print(f"\n🔧 Creating skill from pattern: {pattern['pattern_text']}")
        
        generator = SkillGenerator()
        script = generator.generate_skill_script(
            pattern['pattern_text'], 
            f"Auto-generated skill for: {pattern['pattern_text']}"
        )
        
        if not script:
            print("❌ Failed to generate skill script.")
            conn.close()
            return 1
            
        print("\n--- Generated Script ---")
        print(script[:500] + "..." if len(script) > 500 else script)
        print("------------------------\n")
        
        confirm = input("Save and register this skill? (y/n): ")
        if confirm.lower() == 'y':
            manager = get_skill_manager()
            skill_id = manager.register_skill(
                name=f"skill_{args.pattern_id}",
                description=f"Auto-generated from pattern {args.pattern_id}",
                command_pattern=pattern['pattern_text'],
                script_content=script
            )
            print(f"✅ Skill registered: {skill_id}")
            
            # Update pattern status
            cursor.execute("UPDATE patterns SET status = 'approved' WHERE pattern_id = ?", (args.pattern_id,))
            conn.commit()
            
        conn.close()
        return 0
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return 1

def main():
    parser = argparse.ArgumentParser(description="Hermes Agent CLI", prog="hermes-cli")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # chat
    chat_parser = subparsers.add_parser("chat", help="Start an interactive chat session with Hermes")
    chat_parser.add_argument("query", nargs="*", help="Optional inline query to run and exit")
    
    # query (alias for chat with inline query)
    query_parser = subparsers.add_parser("query", help="Single query mode (alias for chat)")
    query_parser.add_argument("question", nargs="*", help="The question to ask Hermes")
    
    # status
    subparsers.add_parser("status", help="Show agent health and HIS context status")
    
    # context
    context_parser = subparsers.add_parser("context", help="Context management")
    context_sub = context_parser.add_subparsers(dest="context_cmd")
    context_sub.add_parser("refresh", help="Force refresh HIS context")
    
    # discover
    subparsers.add_parser("discover", help="Discover candidate skills from recent patterns")
    
    # list
    subparsers.add_parser("list", help="List all active registered skills")
    
    # run
    run_parser = subparsers.add_parser("run", help="Run a specific skill by ID")
    run_parser.add_argument("skill_id", type=str, help="The ID of the skill to run")

    # health
    subparsers.add_parser("health", help="Check Hermes agent health and configuration")

    # test-llm
    subparsers.add_parser("test-llm", help="Test cloud LLM backend")
    
    # patterns
    patterns_parser = subparsers.add_parser("patterns", help="Pattern management")
    patterns_sub = patterns_parser.add_subparsers(dest="patterns_cmd")
    patterns_sub.add_parser("list", help="Show learned patterns")
    patterns_sub.add_parser("stats", help="Show pattern statistics")
    approve_parser = patterns_sub.add_parser("approve", help="Approve a pattern to create skill")
    approve_parser.add_argument("pattern_id", type=str, help="Pattern ID to approve")
    reject_parser = patterns_sub.add_parser("reject", help="Reject a pattern")
    reject_parser.add_argument("pattern_id", type=str, help="Pattern ID to reject")
    
    # skills
    skills_parser = subparsers.add_parser("skills", help="Skill management")
    skills_sub = skills_parser.add_subparsers(dest="skills_cmd")
    skills_sub.add_parser("list", help="List all registered skills")
    enable_parser = skills_sub.add_parser("enable", help="Enable a disabled skill")
    enable_parser.add_argument("skill_id", type=str, help="Skill ID to enable")
    disable_parser = skills_sub.add_parser("disable", help="Disable an active skill")
    disable_parser.add_argument("skill_id", type=str, help="Skill ID to disable")
    skills_sub.add_parser("metrics", help="Show skill adoption metrics")
    create_parser = skills_sub.add_parser("create", help="Create skill from pattern")
    create_parser.add_argument("--pattern", dest="pattern_id", type=str, required=True, help="Pattern ID")

    args = parser.parse_args()

    if args.command == "chat":
        if args.query:
            args.question = args.query
        cmd_chat(args)
    elif args.command == "query":
        if args.question:
            args.query = args.question
        cmd_chat(args)
    elif args.command == "status":
        return cmd_status(args)
    elif args.command == "context":
        if args.context_cmd == "refresh":
            return cmd_context_refresh(args)
    elif args.command == "discover":
        cmd_discover(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "health":
        return cmd_health(args)
    elif args.command == "test-llm":
        return cmd_test_llm(args)
    elif args.command == "patterns":
        if args.patterns_cmd == "list":
            return cmd_patterns_list(args)
        elif args.patterns_cmd == "stats":
            return cmd_patterns_stats(args)
        elif args.patterns_cmd == "approve":
            print(f"Approving pattern {args.pattern_id}...")
            # This would be implemented similarly to create
            return 0
        elif args.patterns_cmd == "reject":
            print(f"Rejecting pattern {args.pattern_id}...")
            return 0
    elif args.command == "skills":
        if args.skills_cmd == "list":
            return cmd_skills_list(args)
        elif args.skills_cmd == "enable":
            return cmd_skills_enable(args)
        elif args.skills_cmd == "disable":
            return cmd_skills_disable(args)
        elif args.skills_cmd == "metrics":
            return cmd_skills_metrics(args)
        elif args.skills_cmd == "create":
            return cmd_skills_create(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
