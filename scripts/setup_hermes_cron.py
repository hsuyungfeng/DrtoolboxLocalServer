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
  4. weekly-clinic-insights      — 每週一 04:00 綜合週報
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
        'prompt': (
            'Analyze the clinic database at ../clinic.db. Check the patients table '
            'for patients who have not had a visit in the last 6 months. '
            'Generate a retention risk report with: patient names, last visit date, '
            'contact information, and recommended follow-up actions. '
            'Output the report in markdown format for the CRM dashboard.'
        ),
        'deliver': ['dashboard'],
        'skills': ['his-query', 'data-analysis'],
    },
    {
        'name': 'nightly-health-trends',
        'schedule': '0 3 * * *',
        'prompt': (
            'Analyze recent patient visit patterns from the clinic database at ../clinic.db. '
            'Identify trending medical conditions, demographic visit patterns, '
            'and any seasonal health trends. Generate a structured trend report. '
            'Output the report in markdown format for the CRM dashboard.'
        ),
        'deliver': ['dashboard'],
        'skills': ['his-query', 'data-analysis', 'trend-detection'],
    },
    {
        'name': 'nightly-appointment-reminders',
        'schedule': '0 1 * * *',
        'prompt': (
            'Check the clinic database at ../clinic.db for patients with upcoming '
            'appointments in the next 3 days. Generate a reminder list with patient names, '
            'appointment dates, times, and contact phone numbers. '
            'Output the list in markdown format for the CRM dashboard.'
        ),
        'deliver': ['dashboard'],
        'skills': ['his-query'],
    },
    {
        'name': 'nightly-rag-fact-check',
        'schedule': '30 3 * * *',
        'prompt': (
            'Scan the daily interaction logs in ../data/logs/. For every medical or procedure '
            'related query, perform a web search to verify the facts. Generate a corrected '
            'draft response if the AI original answer was incomplete or slightly inaccurate. '
            'Save these drafts into ../data/logs/hermes_drafts_YYYY-MM-DD.jsonl for staff review.'
        ),
        'deliver': ['dashboard'],
        'skills': ['web-search', 'data-review'],
    },
    {
        'name': 'weekly-clinic-insights',
        'schedule': '0 4 * * 1',
        'prompt': (
            'Generate a comprehensive weekly clinic operations summary from the database '
            'at ../clinic.db. Include: patient volume trends, most common conditions treated, '
            'staff workload distribution, supply/equipment status, and strategic recommendations '
            'for the coming week. Output in markdown format for the CRM dashboard.'
        ),
        'deliver': ['dashboard'],
        'skills': ['his-query', 'data-analysis', 'trend-detection'],
    },
]


def find_hermes_binary():
    """尋找 hermes CLI 執行檔"""
    # 優先使用當前目錄的 hermes-agent 中的 CLI
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
    """執行 hermes CLI 指令"""
    hermes = find_hermes_binary()
    if hermes.startswith('python'):
        full_cmd = hermes.split() + cmd_parts
    else:
        full_cmd = [hermes] + cmd_parts

    return subprocess.run(full_cmd, capture_output=True, text=True, timeout=30)


def create_jobs():
    """建立所有 CRM Cron Jobs"""
    print('=== Hermes Agent CRM Cron Setup ===')
    print()
    
    for job in JOBS:
        print(f"  Setting up: {job['name']} ({job['schedule']})")
        try:
            cmd = [
                'cron', 'create',
                '--name', job['name'],
                '--deliver', ','.join(job['deliver']),
            ]
            for skill in job['skills']:
                cmd.extend(['--skill', skill])
            cmd.extend([job['schedule'], job['prompt']])
            result = run_hermes_command(cmd)

            if result.returncode == 0:
                print(f'    ✅ Created successfully')
            elif 'already exists' in (result.stderr + result.stdout).lower():
                print(f'    ⚠️  Already exists (skipped)')
            else:
                print(f'    ❌ Failed: {result.stderr.strip() or result.stdout.strip()}')
        except FileNotFoundError:
            print(f'    ❌ Hermes CLI not found. Please run in hermes-agent environment.')
            print(f'       Expected locations:')
            print(f'         - hermes-agent/.venv/bin/hermes')
            print(f'         - hermes (in PATH)')
            return
        except subprocess.TimeoutExpired:
            print(f'    ❌ Timed out')
        except Exception as e:
            print(f'    ❌ Error: {e}')

    print()


def list_jobs():
    """列出已存在的 jobs"""
    print('=== Current Cron Jobs ===')
    try:
        result = run_hermes_command(['cron', 'list'])
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f'  Failed to list: {result.stderr}')
    except Exception as e:
        print(f'  Error: {e}')


if __name__ == '__main__':
    create_jobs()
    list_jobs()
    print()
    print('Setup complete. CRM cron jobs will run automatically according to their schedules.')
