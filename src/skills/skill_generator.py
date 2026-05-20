"""
Skill Generator

Uses the local LLM to generate Python code for Auto-Skills based on learned patterns.
"""

import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SkillGenerator:
    """Generates Python scripts for Auto-Skills using LLM."""
    
    def __init__(self, llama_url: str = "http://127.0.0.1:8080/v1/chat/completions"):
        self.llama_url = llama_url
        
    def generate_skill_script(self, pattern: str, description: str) -> Optional[str]:
        """
        Generate a python script containing a `run(**kwargs)` function that fulfills the pattern.
        """
        prompt = """You are an expert Python developer writing an Auto-Skill for a Clinic Intelligence System.
The skill must be a standalone Python script containing a single function: `def run(**kwargs):`.
This function should perform the task described below and return a dictionary with the results.

Task Pattern to automate: "{pattern}"
Task Description: "{description}"

Guidelines:
1. Return ONLY valid Python code. Do NOT wrap it in Markdown code blocks (like ```python).
2. The code must import any necessary standard libraries.
3. If it needs to query the HIS database, assume it can import from `src.db.his_connection` and use `HISConnection().execute_query()`.
4. The `run` function should handle exceptions and return a dict with "status" and "message" keys on failure.

Example structure:
import logging
from src.db.his_connection import HISConnection

def run(**kwargs):
    try:
        conn = HISConnection()
        # Do work
        return {{"status": "success", "data": "..."}}
    except Exception as e:
        return {{"status": "error", "message": str(e)}}
        
Write the script for the requested task now.
""".format(pattern=pattern, description=description)
        try:
            response = requests.post(
                self.llama_url,
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                    "temperature": 0.1
                },
                timeout=60
            )
            
            if response.status_code == 200:
                script_code = response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                # Clean markdown backticks if the model ignores the instruction
                if script_code.startswith("```python"):
                    script_code = script_code[9:]
                if script_code.startswith("```"):
                    script_code = script_code[3:]
                if script_code.endswith("```"):
                    script_code = script_code[:-3]
                    
                return script_code.strip()
            else:
                logger.error(f"LLM generation failed: {response.status_code}")
                # Fallback: generate a basic template script
                return self._generate_fallback_script(pattern, description)
        except Exception as e:
            logger.error(f"Failed to generate skill script: {e}")
            # Fallback: generate a basic template script
            return self._generate_fallback_script(pattern, description)
    
    def _generate_fallback_script(self, pattern: str, description: str) -> str:
        """Generate a basic template script when LLM is unavailable."""
        return f'''"""
Auto-Skill: {pattern}
Auto-generated from pattern learning system.
"""
import logging
from src.db.his_connection import HISConnection

logger = logging.getLogger(__name__)

def run(**kwargs):
    """
    Generated for pattern: {pattern}
    Description: {description}
    """
    try:
        conn = HISConnection()
        
        # TODO: Implement the specific logic for this pattern
        # Example: Query patient data, check schedules, etc.
        
        result = {{"message": "Skill executed for pattern: {pattern}"}}
        
        return {{"status": "success", "data": result}}
        
    except Exception as e:
        logger.error(f"Skill execution failed: {{e}}")
        return {{"status": "error", "message": str(e)}}
'''
