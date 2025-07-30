from crewai.tools import BaseTool
from typing import Type, Any, Optional, Dict, List
from pydantic import BaseModel, Field
import subprocess
import tempfile
import os
import json
import asyncio
from pathlib import Path

# Import Anthropic SDK for real Claude integration
import anthropic
from anthropic import Anthropic

class ClaudeCodeInput(BaseModel):
    """Input schema for Claude Code tool"""
    task: str = Field(description="Coding task to complete")
    language: str = Field(default="python", description="Programming language")
    context: str = Field(default="", description="Additional context or requirements")
    include_tests: bool = Field(default=True, description="Whether to include unit tests")
    include_docs: bool = Field(default=True, description="Whether to include documentation")
    file_path: Optional[str] = Field(default=None, description="Optional file path for code context")

class ClaudeCodeWrapper(BaseTool):
    name: str = "claude_code"
    description: str = """
    Execute advanced coding tasks using Claude AI with real-time code generation, 
    testing, and documentation. Supports multiple programming languages and 
    follows industry best practices.
    """
    args_schema: Type[BaseModel] = ClaudeCodeInput
    
    def __init__(self):
        super().__init__()
        self.client = Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )
        self.model = "claude-3-5-sonnet-20241022"
    
    def _run(self, task: str, language: str = "python", context: str = "", 
             include_tests: bool = True, include_docs: bool = True, 
             file_path: Optional[str] = None) -> str:
        """Execute Claude Code for a specific task with real AI integration"""
        
        try:
            # Read existing file context if provided
            existing_code = ""
            if file_path and os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    existing_code = f.read()
            
            # Prepare the comprehensive prompt
            prompt = self._build_prompt(
                task=task,
                language=language,
                context=context,
                existing_code=existing_code,
                include_tests=include_tests,
                include_docs=include_docs
            )
            
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.3,  # Lower temperature for more consistent code
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Parse the response and extract code files
            result = self._parse_response(response.content[0].text, language, include_tests, include_docs)
            
            # Save generated files to temporary directory
            with tempfile.TemporaryDirectory() as tmpdir:
                saved_files = self._save_files(result['files'], tmpdir)
                
                # Run tests if generated
                test_results = None
                if include_tests and any(f['type'] == 'test' for f in result['files']):
                    test_results = self._run_tests(tmpdir, language)
                
                return json.dumps({
                    'status': 'success',
                    'files': result['files'],
                    'explanation': result.get('explanation', ''),
                    'test_results': test_results,
                    'commit_message': result.get('commit_message', ''),
                    'execution_summary': f"Generated {len(result['files'])} files for {language} task: {task[:100]}..."
                })
                
        except anthropic.APIError as e:
            return json.dumps({
                'status': 'error',
                'error': f'Claude API error: {str(e)}',
                'error_type': 'api_error'
            })
        except Exception as e:
            return json.dumps({
                'status': 'error',
                'error': f'Unexpected error: {str(e)}',
                'error_type': 'general_error'
            })
    
    def _build_prompt(self, task: str, language: str, context: str, 
                     existing_code: str, include_tests: bool, include_docs: bool) -> str:
        """Build a comprehensive prompt for Claude"""
        
        prompt = f"""
You are an expert {language} developer. I need you to complete the following coding task:

**Task**: {task}

**Programming Language**: {language}

**Additional Context**: {context}

**Existing Code** (if any):
```{language}
{existing_code}
```

**Requirements**:
1. Write clean, maintainable, and well-documented code
2. Follow {language} best practices and conventions
3. Include proper error handling
4. Use type hints (where applicable)
5. {"Include comprehensive unit tests" if include_tests else "Focus only on implementation"}
6. {"Include docstrings and comments" if include_docs else "Minimal documentation"}

**Output Format**:
Please structure your response as follows:

## Explanation
Brief explanation of your approach and key decisions.

## Implementation

### Main Code
```{language}
# Your main implementation here
```

{"### Tests" if include_tests else ""}
{f"```{language}" if include_tests else ""}
{"# Your test code here" if include_tests else ""}
{f"```" if include_tests else ""}

{"### Documentation" if include_docs else ""}
{"```markdown" if include_docs else ""}
{"# Your documentation here" if include_docs else ""}
{f"```" if include_docs else ""}

## Commit Message
Suggest a concise git commit message for these changes.

Please ensure the code is production-ready and follows industry standards.
"""
        return prompt
    
    def _parse_response(self, response: str, language: str, include_tests: bool, include_docs: bool) -> Dict[str, Any]:
        """Parse Claude's response and extract code files"""
        
        files = []
        explanation = ""
        commit_message = ""
        
        # Extract explanation
        if "## Explanation" in response:
            explanation_start = response.find("## Explanation") + len("## Explanation")
            explanation_end = response.find("## Implementation")
            if explanation_end > explanation_start:
                explanation = response[explanation_start:explanation_end].strip()
        
        # Extract commit message
        if "## Commit Message" in response:
            commit_start = response.find("## Commit Message") + len("## Commit Message")
            commit_message = response[commit_start:].strip()
            # Clean up the commit message
            commit_message = commit_message.split('\n')[0].strip()
        
        # Extract main code
        main_code = self._extract_code_block(response, "### Main Code", language)
        if main_code:
            file_ext = self._get_file_extension(language)
            files.append({
                'filename': f'main.{file_ext}',
                'content': main_code,
                'type': 'implementation',
                'language': language
            })
        
        # Extract tests if requested
        if include_tests:
            test_code = self._extract_code_block(response, "### Tests", language)
            if test_code:
                test_ext = self._get_file_extension(language)
                files.append({
                    'filename': f'test_main.{test_ext}',
                    'content': test_code,
                    'type': 'test',
                    'language': language
                })
        
        # Extract documentation if requested
        if include_docs:
            docs = self._extract_code_block(response, "### Documentation", "markdown")
            if docs:
                files.append({
                    'filename': 'README.md',
                    'content': docs,
                    'type': 'documentation',
                    'language': 'markdown'
                })
        
        return {
            'files': files,
            'explanation': explanation,
            'commit_message': commit_message
        }
    
    def _extract_code_block(self, text: str, section: str, language: str) -> Optional[str]:
        """Extract code block from a specific section"""
        
        section_start = text.find(section)
        if section_start == -1:
            return None
        
        # Find the start of the code block
        code_start = text.find(f"```{language}", section_start)
        if code_start == -1:
            code_start = text.find("```", section_start)
            if code_start == -1:
                return None
        
        # Find the end of the code block
        code_content_start = text.find('\n', code_start) + 1
        code_end = text.find("```", code_content_start)
        
        if code_end == -1:
            return None
        
        return text[code_content_start:code_end].strip()
    
    def _get_file_extension(self, language: str) -> str:
        """Get appropriate file extension for language"""
        extensions = {
            'python': 'py',
            'javascript': 'js',
            'typescript': 'ts',
            'java': 'java',
            'cpp': 'cpp',
            'c': 'c',
            'rust': 'rs',
            'go': 'go',
            'ruby': 'rb',
            'php': 'php',
            'swift': 'swift',
            'kotlin': 'kt',
            'scala': 'scala',
            'r': 'R',
            'sql': 'sql',
            'html': 'html',
            'css': 'css',
            'shell': 'sh',
            'bash': 'sh'
        }
        return extensions.get(language.lower(), 'txt')
    
    def _save_files(self, files: List[Dict], tmpdir: str) -> List[str]:
        """Save generated files to temporary directory"""
        saved_files = []
        
        for file_info in files:
            file_path = os.path.join(tmpdir, file_info['filename'])
            with open(file_path, 'w') as f:
                f.write(file_info['content'])
            saved_files.append(file_path)
        
        return saved_files
    
    def _run_tests(self, tmpdir: str, language: str) -> Optional[Dict[str, Any]]:
        """Run tests for the generated code"""
        
        try:
            if language == 'python':
                # Try to run pytest
                result = subprocess.run(
                    ['python', '-m', 'pytest', tmpdir, '-v'],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=tmpdir
                )
                
                return {
                    'exit_code': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'success': result.returncode == 0
                }
            elif language == 'javascript':
                # Try to run with node
                test_files = [f for f in os.listdir(tmpdir) if f.startswith('test_')]
                if test_files:
                    result = subprocess.run(
                        ['node', test_files[0]],
                        capture_output=True,
                        text=True,
                        timeout=60,
                        cwd=tmpdir
                    )
                    
                    return {
                        'exit_code': result.returncode,
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'success': result.returncode == 0
                    }
            
            return None
            
        except subprocess.TimeoutExpired:
            return {
                'exit_code': -1,
                'stdout': '',
                'stderr': 'Test execution timed out',
                'success': False
            }
        except Exception as e:
            return {
                'exit_code': -1,
                'stdout': '',
                'stderr': f'Test execution error: {str(e)}',
                'success': False
            }