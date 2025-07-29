from crewai.tools import BaseTool
from typing import Type, Any
from pydantic import BaseModel, Field
import subprocess
import tempfile
import os
import json

class ClaudeCodeInput(BaseModel):
    """Input schema for Claude Code tool"""
    task: str = Field(description="Coding task to complete")
    language: str = Field(default="python", description="Programming language")
    context: str = Field(default="", description="Additional context or requirements")

class ClaudeCodeWrapper(BaseTool):
    name: str = "claude_code"
    description: str = "Execute coding tasks using Claude Code SDK"
    args_schema: Type[BaseModel] = ClaudeCodeInput
    
    def _run(self, task: str, language: str = "python", context: str = "") -> str:
        """Execute Claude Code for a specific task"""
        
        # Prepare the prompt
        prompt = f"""
        Task: {task}
        Language: {language}
        Context: {context}
        
        Please complete this coding task following best practices.
        """
        
        # Create temporary directory for code execution
        with tempfile.TemporaryDirectory() as tmpdir:
            # Call Claude Code CLI (assuming it's installed in container)
            cmd = [
                "claude-code",
                "execute",
                "--prompt", prompt,
                "--output-dir", tmpdir,
                "--language", language
            ]
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                if result.returncode == 0:
                    # Read generated files
                    generated_files = []
                    for filename in os.listdir(tmpdir):
                        filepath = os.path.join(tmpdir, filename)
                        if os.path.isfile(filepath):
                            with open(filepath, 'r') as f:
                                generated_files.append({
                                    'filename': filename,
                                    'content': f.read()
                                })
                    
                    return json.dumps({
                        'status': 'success',
                        'files': generated_files,
                        'output': result.stdout
                    })
                else:
                    return json.dumps({
                        'status': 'error',
                        'error': result.stderr
                    })
                    
            except subprocess.TimeoutExpired:
                return json.dumps({
                    'status': 'error',
                    'error': 'Task execution timed out'
                })
            except Exception as e:
                return json.dumps({
                    'status': 'error',
                    'error': str(e)
                })