"""
Skill Manager

Handles the registration, discovery, and dynamic execution of Auto-Skills.
Stores skill metadata and execution metrics in the clinic database.
"""

import os
import json
import uuid
import time
import importlib.util
import logging
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SkillManager:
    """Manages Hermes Auto-Skills."""
    
    def __init__(self, db_path: str = "data/db/clinic.db", skills_dir: str = "src/skills/auto_skills"):
        self.db_path = db_path
        self.skills_dir = skills_dir
        
        # Ensure skills directory exists
        if not os.path.exists(self.skills_dir):
            os.makedirs(self.skills_dir)
            # Create an __init__.py so it can be treated as a package
            with open(os.path.join(self.skills_dir, "__init__.py"), "w") as f:
                f.write("# Auto-generated skills package\n")
                
    def _get_conn(self):
        return sqlite3.connect(self.db_path)
        
    def list_skills(self) -> List[Dict[str, Any]]:
        """Retrieve all active skills from the database."""
        try:
            with self._get_conn() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM auto_skills WHERE is_active = 1")
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to list skills: {e}")
            return []
            
    def register_skill(self, name: str, description: str, command_pattern: str, script_content: str) -> str:
        """Register a new auto-skill and save the script to disk."""
        skill_id = f"skill_{uuid.uuid4().hex[:8]}"
        script_filename = f"{skill_id}.py"
        script_path = os.path.join(self.skills_dir, script_filename)
        
        # Write script to disk
        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)
        except Exception as e:
            logger.error(f"Failed to write skill script {script_path}: {e}")
            raise
            
        # Register in database
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO auto_skills (skill_id, name, description, command_pattern, script_path)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (skill_id, name, description, command_pattern, script_path)
                )
                conn.commit()
            logger.info(f"Successfully registered auto-skill: {skill_id} ({name})")
            return skill_id
        except Exception as e:
            logger.error(f"Failed to register skill in database: {e}")
            # Rollback file creation
            if os.path.exists(script_path):
                os.remove(script_path)
            raise
            
    def execute_skill(self, skill_id: str, args: Dict[str, Any] = None, user: str = "system") -> Dict[str, Any]:
        """Dynamically load and execute a skill by ID."""
        if args is None:
            args = {}
            
        start_time = time.time()
        success = False
        result = None
        
        try:
            with self._get_conn() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT script_path FROM auto_skills WHERE skill_id = ?", (skill_id,))
                row = cursor.fetchone()
                
            if not row:
                raise ValueError(f"Skill {skill_id} not found.")
                
            script_path = row["script_path"]
            
            if not os.path.exists(script_path):
                raise FileNotFoundError(f"Skill script not found: {script_path}")
                
            # Dynamic import
            spec = importlib.util.spec_from_file_location(f"auto_skill_{skill_id}", script_path)
            skill_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(skill_module)
            
            # Expecting a run() function in the script
            if hasattr(skill_module, 'run'):
                result = skill_module.run(**args)
                success = True
            else:
                raise AttributeError(f"Skill script {script_path} does not have a 'run' function.")
                
        except Exception as e:
            logger.error(f"Error executing skill {skill_id}: {e}")
            result = {"error": str(e)}
            
        finally:
            execution_time_ms = int((time.time() - start_time) * 1000)
            self._log_metric(skill_id, execution_time_ms, success, user)
            
        return {"success": success, "result": result, "time_ms": execution_time_ms}
        
    def _log_metric(self, skill_id: str, execution_time_ms: int, success: bool, user: str):
        """Log skill execution metrics."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO skill_metrics (skill_id, execution_time_ms, is_successful, executed_by)
                    VALUES (?, ?, ?, ?)
                    """,
                    (skill_id, execution_time_ms, success, user)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log metric for skill {skill_id}: {e}")

# Singleton
_manager_instance = None

def get_skill_manager() -> SkillManager:
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = SkillManager()
    return _manager_instance
