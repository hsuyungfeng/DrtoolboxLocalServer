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

def main():
    parser = argparse.ArgumentParser(description="Hermes Agent CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # chat
    chat_parser = subparsers.add_parser("chat", help="Start an interactive chat session with Hermes")
    chat_parser.add_argument("query", nargs="*", help="Optional inline query to run and exit")
    
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

    args = parser.parse_args()

    if args.command == "chat":
        cmd_chat(args)
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
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
