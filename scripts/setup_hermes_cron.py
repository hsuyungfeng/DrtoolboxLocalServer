#!/usr/bin/env python3
"""
Hermes Agent Nightly CRM Cron Job Setup
設定夜間自動化 CRM 分析排程

在 hermes-agent 環境中執行此腳本以建立排程任務：
  cd hermes-agent && python ../scripts/setup_hermes_cron.py

排程任務：
  1. nightly-patient-retention  — 每日 02:00 回診追蹤分析
  2. nightly-health-trends       — 每日 03:00 健康趨勢分析
  3. nightly-appointment-reminders — 每日 01:00 預約提醒
  4. weekly-crm-insights         — 每週一 04:00 綜合週報 (含病患對話分析)
"""

import subprocess
import sys
import os
import json

HERMES_HOME = os.environ.get('HERMES_HOME', os.path.expanduser('~/.hermes'))

JOBS = [
    {
        'name': 'nightly-patient-retention',
        'schedule': '0 2 * * *',
        'skills': ['his-query', 'data-analysis'],
        'deliver': ['dashboard'],
        'prompt': 'Analyze the clinic database. Find patients with no visits in 6 months. Generate retention risk report.',
    },
    {
        'name': 'nightly-health-trends',
        'schedule': '0 3 * * *',
        'skills': ['his-query', 'data-analysis', 'trend-detection'],
        'deliver': ['dashboard'],
        'prompt': 'Analyze recent visit patterns. Identify trending medical conditions and demographic visit patterns.',
    },
    {
        'name': 'nightly-appointment-reminders',
        'schedule': '0 1 * * *',
        'skills': ['his-query'],
        'deliver': ['dashboard'],
        'prompt': 'Check appointments for the next 3 days. Generate reminder list.',
    },
    {
        'name': 'nightly-rag-fact-check',
        'schedule': '30 3 * * *',
        'skills': ['web-search', 'data-review'],
        'deliver': ['dashboard'],
        'prompt': 'Scan daily interaction logs. Perform web search to verify facts and generate correction drafts.',
    },
    {
        'name': 'nightly-proactive-qa',
        'schedule': '0 4 * * *',
        'skills': ['data-discovery', 'qa-generation'],
        'deliver': ['dashboard'],
        'prompt': 'Scan clinic documents. Generate 3 realistic patient questions and verified answers for each service found.',
    },
    {
        'name': 'weekly-crm-insights',
        'schedule': '0 4 * * 1',
        'skills': ['data-analysis', 'reporting', 'natural-language-processing'],
        'deliver': ['dashboard'],
        'prompt': (
            'Analyze all patient interaction logs from the past 7 days. Generate a '
            'comprehensive business intelligence report including: top requested procedures, '
            'common patient concerns/pain points, and suggested improvements for clinic marketing.'
        ),
    },
]

def find_hermes_binary():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    search_paths = [
        os.path.join(project_root, 'hermes-agent', '.venv', 'bin', 'hermes'),
        os.path.join(project_root, 'hermes-agent', 'hermes_cli', 'main.py'),
        'hermes',
        'python -m hermes_cli.main',
    ]
    for path in search_paths:
        if os.path.exists(path.split()[0] if ' ' not in path else path.split()[-1]):
            return path
    return 'hermes'

def run_hermes_command(cmd_parts: list) -> subprocess.CompletedProcess:
    hermes = find_hermes_binary()
    if hermes.startswith('python'):
        full_cmd = hermes.split() + cmd_parts
    else:
        full_cmd = [hermes] + cmd_parts
    return subprocess.run(full_cmd, capture_output=True, text=True, timeout=30)

def create_jobs():
    print('=== Hermes Agent CRM Cron Setup ===')
    for job in JOBS:
        print(f"  Setting up: {job['name']} ({job['schedule']})")
        try:
            cmd = ['cron', 'create', '--name', job['name'], '--deliver', ','.join(job['deliver'])]
            for skill in job['skills']: cmd.extend(['--skill', skill])
            cmd.extend([job['schedule'], job['prompt']])
            result = run_hermes_command(cmd)
            if result.returncode == 0: print(f'    ✅ Created successfully')
            elif 'already exists' in (result.stderr + result.stdout).lower(): print(f'    ⚠️  Already exists (skipped)')
            else: print(f'    ❌ Failed: {result.stderr.strip() or result.stdout.strip()}')
        except Exception as e: print(f'    ❌ Error: {e}')

def list_jobs():
    print('=== Current Cron Jobs ===')
    try:
        result = run_hermes_command(['cron', 'list'])
        if result.returncode == 0: print(result.stdout)
        else: print(f'  Failed to list: {result.stderr}')
    except Exception as e: print(f'  Error: {e}')

if __name__ == '__main__':
    create_jobs()
    list_jobs()
    print('\nSetup complete. CRM cron jobs will run automatically.')
