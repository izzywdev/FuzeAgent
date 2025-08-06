"""
Claude Client with Memory Integration

Enhanced Claude client that uses agent's persistent memory to provide
contextual, learning-based interactions. Integrates with AgentMemoryManager
to retrieve relevant memories and store new learnings.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import anthropic
from anthropic import Anthropic

from agent_memory_manager import (
    AgentMemoryManager, MemoryType, MemoryQueryResult, AgentMemory
)

logger = logging.getLogger(__name__)

class ClaudeClientWithMemory:
    """
    Enhanced Claude client with persistent memory integration.
    
    Features:
    - Memory-enhanced context building
    - Learning from interactions
    - Pattern recognition across tasks
    - Expertise-aware prompting
    - Conversation continuity across container instances
    """
    
    def __init__(
        self, 
        memory_manager: AgentMemoryManager,
        agent_id: str,
        anthropic_api_key: str,
        model: str = "claude-3-5-sonnet-20241022"
    ):
        self.memory_manager = memory_manager
        self.agent_id = agent_id
        self.model = model
        
        # Initialize Claude client
        self.claude_client = Anthropic(api_key=anthropic_api_key)
        
        # Configuration
        self.max_context_memories = 15
        self.context_relevance_threshold = 0.7
        self.learning_confidence_threshold = 0.8
        
        # Statistics
        self.interactions_count = 0
        self.memory_enhanced_interactions = 0
        self.learned_patterns_count = 0
    
    async def execute_with_memory_context(
        self,
        task_description: str,
        task_id: str,
        task_context: Optional[Dict[str, Any]] = None,
        code_context: Optional[Dict[str, Any]] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        enable_learning: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a task with Claude using memory-enhanced context.
        
        This method:
        1. Queries relevant memories based on the task
        2. Builds enhanced context from memories
        3. Executes Claude interaction with context
        4. Learns from the interaction outcome
        5. Stores new memories for future use
        """
        
        self.interactions_count += 1
        start_time = time.time()
        
        try:
            # Step 1: Query relevant memories
            relevant_memories = await self._get_relevant_memories(
                task_description, task_context
            )
            
            # Step 2: Build memory-enhanced context
            memory_context = await self._build_memory_context(
                relevant_memories, task_description, task_context
            )
            
            # Step 3: Build comprehensive prompt
            prompt = await self._build_enhanced_prompt(
                task_description=task_description,
                memory_context=memory_context,
                task_context=task_context or {},
                code_context=code_context or {}
            )
            
            # Step 4: Execute Claude interaction
            response = await self._execute_claude_interaction(
                prompt, temperature, max_tokens
            )
            
            execution_time = time.time() - start_time
            
            # Step 5: Process and analyze response
            result = await self._process_claude_response(
                response, task_id, task_description, execution_time
            )
            
            # Step 6: Learn from interaction (if enabled)
            if enable_learning:
                await self._learn_from_interaction(
                    task_id=task_id,
                    task_description=task_description,
                    task_context=task_context,
                    code_context=code_context,
                    memories_used=relevant_memories,
                    claude_response=response,
                    result=result
                )
            
            # Update statistics
            if relevant_memories:
                self.memory_enhanced_interactions += 1
            
            logger.info(f"Completed memory-enhanced interaction for task {task_id} "
                       f"in {execution_time:.2f}s with {len(relevant_memories)} memories")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in memory-enhanced execution: {e}")
            
            # Store error for learning
            if enable_learning:
                await self.memory_manager.store_memory(
                    task_id=task_id,
                    memory_type=MemoryType.ERROR,
                    content=f"Claude execution error: {str(e)}",
                    task_context=task_context or {},
                    outcome_context={'error': str(e), 'task_description': task_description},
                    confidence_score=0.9
                )
            
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    async def get_expertise_enhanced_prompt(
        self,
        base_prompt: str,
        skill_area: str,
        include_examples: bool = True
    ) -> str:
        """
        Enhance a base prompt with agent's expertise and successful patterns
        in the specified skill area.
        """
        
        try:
            # Get agent's expertise summary
            expertise_summary = await self.memory_manager.get_agent_expertise_summary()
            
            # Find relevant expertise area
            relevant_expertise = None
            for expertise in expertise_summary.get('expertise_areas', []):
                if skill_area.lower() in expertise['skill_area'].lower():
                    relevant_expertise = expertise
                    break
            
            # Query successful patterns in this skill area
            if include_examples:
                success_memories = await self.memory_manager.query_memories(
                    query=f"{skill_area} successful implementation patterns",
                    memory_types=[MemoryType.SUCCESS, MemoryType.PATTERN],
                    limit=5,
                    min_confidence=0.8
                )
            else:
                success_memories = []
            
            # Build enhanced prompt
            enhanced_prompt = base_prompt
            
            if relevant_expertise:
                enhanced_prompt += f"\n\n**Your Expertise in {skill_area}:**\n"
                enhanced_prompt += f"- Expertise Level: {relevant_expertise['expertise_level']:.1%}\n"
                enhanced_prompt += f"- Tasks Completed: {relevant_expertise['task_count']}\n"
                enhanced_prompt += f"- Success Rate: {relevant_expertise['success_rate']:.1%}\n"
                enhanced_prompt += f"- Performance Trend: {relevant_expertise['performance_trend']}\n"
                
                if relevant_expertise.get('key_learnings'):
                    enhanced_prompt += f"- Key Learnings: {json.dumps(relevant_expertise['key_learnings'], indent=2)}\n"
            
            if success_memories:
                enhanced_prompt += f"\n\n**Successful Patterns from Your Experience:**\n"
                for i, memory_result in enumerate(success_memories, 1):
                    memory = memory_result.memory
                    enhanced_prompt += f"{i}. {memory.content[:200]}...\n"
                    if memory.outcome_context:
                        enhanced_prompt += f"   Result: {memory.outcome_context.get('summary', 'Success')}\n"
            
            return enhanced_prompt
            
        except Exception as e:
            logger.error(f"Error enhancing prompt with expertise: {e}")
            return base_prompt
    
    async def _get_relevant_memories(
        self,
        task_description: str,
        task_context: Optional[Dict[str, Any]] = None
    ) -> List[MemoryQueryResult]:
        """Get memories relevant to the current task"""
        
        try:
            # Query different types of relevant memories
            memory_queries = [
                # Recent successful patterns
                (f"successful {task_context.get('task_type', 'development')} implementation", 
                 [MemoryType.SUCCESS, MemoryType.PATTERN]),
                
                # Related learning experiences
                (task_description, 
                 [MemoryType.LEARNING, MemoryType.TASK_OUTCOME]),
                
                # Error patterns to avoid
                (f"common errors in {task_context.get('task_type', 'development')}", 
                 [MemoryType.ERROR]),
                
                # Code patterns and solutions
                (task_description, 
                 [MemoryType.CODE_PATTERN, MemoryType.OPTIMIZATION])
            ]
            
            all_memories = []
            for query, memory_types in memory_queries:
                memories = await self.memory_manager.query_memories(
                    query=query,
                    memory_types=memory_types,
                    task_context=task_context,
                    limit=5,
                    min_confidence=self.context_relevance_threshold
                )
                all_memories.extend(memories)
            
            # Remove duplicates and sort by relevance
            unique_memories = {}
            for memory_result in all_memories:
                memory_id = memory_result.memory.id
                if memory_id not in unique_memories or \
                   memory_result.relevance_score > unique_memories[memory_id].relevance_score:
                    unique_memories[memory_id] = memory_result
            
            # Sort by relevance and limit
            sorted_memories = sorted(
                unique_memories.values(),
                key=lambda mr: (mr.relevance_score, mr.memory.confidence_score, mr.memory.usage_count),
                reverse=True
            )[:self.max_context_memories]
            
            logger.debug(f"Found {len(sorted_memories)} relevant memories for task context")
            return sorted_memories
            
        except Exception as e:
            logger.error(f"Error getting relevant memories: {e}")
            return []
    
    async def _build_memory_context(
        self,
        memories: List[MemoryQueryResult],
        task_description: str,
        task_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build structured context from relevant memories"""
        
        context = {
            'successful_patterns': [],
            'lessons_learned': [],
            'error_patterns_to_avoid': [],
            'code_patterns': [],
            'optimization_tips': [],
            'related_experience': []
        }
        
        for memory_result in memories:
            memory = memory_result.memory
            relevance = memory_result.relevance_score
            
            memory_info = {
                'content': memory.content,
                'confidence': memory.confidence_score,
                'relevance': relevance,
                'usage_count': memory.usage_count,
                'outcome': memory.outcome_context.get('success', 'unknown')
            }
            
            # Categorize memories by type
            if memory.memory_type == MemoryType.SUCCESS:
                context['successful_patterns'].append(memory_info)
            elif memory.memory_type == MemoryType.LEARNING:
                context['lessons_learned'].append(memory_info)
            elif memory.memory_type == MemoryType.ERROR:
                context['error_patterns_to_avoid'].append(memory_info)
            elif memory.memory_type == MemoryType.CODE_PATTERN:
                context['code_patterns'].append(memory_info)
            elif memory.memory_type == MemoryType.OPTIMIZATION:
                context['optimization_tips'].append(memory_info)
            else:
                context['related_experience'].append(memory_info)
        
        # Add summary statistics
        context['summary'] = {
            'total_memories': len(memories),
            'avg_relevance': sum(mr.relevance_score for mr in memories) / max(1, len(memories)),
            'avg_confidence': sum(mr.memory.confidence_score for mr in memories) / max(1, len(memories)),
            'high_usage_memories': len([mr for mr in memories if mr.memory.usage_count > 5])
        }
        
        return context
    
    async def _build_enhanced_prompt(
        self,
        task_description: str,
        memory_context: Dict[str, Any],
        task_context: Dict[str, Any],
        code_context: Dict[str, Any]
    ) -> str:
        """Build comprehensive prompt with memory context"""
        
        # Get agent expertise summary for prompt personalization
        expertise_summary = await self.memory_manager.get_agent_expertise_summary()
        
        prompt = f"""You are an expert AI developer with persistent memory and learning capabilities. 

**Current Task:**
{task_description}

**Task Context:**
- Type: {task_context.get('task_type', 'development')}
- Complexity: {task_context.get('complexity', 'medium')}
- Language/Framework: {task_context.get('language', 'unknown')}
- Estimated Duration: {task_context.get('estimated_duration', 'unknown')}

**Your Expertise Profile:**
- Total Memories: {expertise_summary.get('memory_statistics', {}).get('total_memories', 0)}
- Skill Areas: {len(expertise_summary.get('expertise_areas', []))}
- Container Instances: {len(expertise_summary.get('container_history', []))}
"""

        # Add code context if available
        if code_context:
            prompt += f"\n**Code Context:**\n"
            for key, value in code_context.items():
                prompt += f"- {key}: {value}\n"
        
        # Add memory-based context
        if memory_context['successful_patterns']:
            prompt += f"\n**Your Successful Patterns (from experience):**\n"
            for i, pattern in enumerate(memory_context['successful_patterns'][:5], 1):
                prompt += f"{i}. {pattern['content'][:150]}... (confidence: {pattern['confidence']:.1%})\n"
        
        if memory_context['lessons_learned']:
            prompt += f"\n**Key Lessons from Your Experience:**\n"
            for i, lesson in enumerate(memory_context['lessons_learned'][:5], 1):
                prompt += f"{i}. {lesson['content'][:150]}... (relevance: {lesson['relevance']:.1%})\n"
        
        if memory_context['error_patterns_to_avoid']:
            prompt += f"\n**Error Patterns to Avoid (from your past errors):**\n"
            for i, error in enumerate(memory_context['error_patterns_to_avoid'][:3], 1):
                prompt += f"{i}. {error['content'][:150]}...\n"
        
        if memory_context['code_patterns']:
            prompt += f"\n**Relevant Code Patterns from Your Experience:**\n"
            for i, pattern in enumerate(memory_context['code_patterns'][:3], 1):
                prompt += f"{i}. {pattern['content'][:200]}...\n"
        
        # Add requirements and expectations
        prompt += f"""

**Requirements:**
1. Use your accumulated experience and patterns shown above
2. Avoid the error patterns you've encountered before
3. Apply successful patterns where relevant
4. Write clean, maintainable, well-documented code
5. Include appropriate error handling and validation
6. Follow best practices for the target language/framework
7. Consider performance and security implications

**Expected Output:**
Please provide a comprehensive solution that includes:
1. Implementation code with clear explanations
2. Test cases or validation steps
3. Documentation or usage examples
4. Any deployment or setup instructions
5. Potential improvements or alternatives

**Learning Note:** 
Your response will be analyzed and stored as part of your learning experience. 
Focus on providing high-quality, reusable patterns that will benefit future tasks.
"""

        return prompt
    
    async def _execute_claude_interaction(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Execute the actual Claude API interaction"""
        
        try:
            response = self.claude_client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            return response.content[0].text
            
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Claude interaction: {e}")
            raise
    
    async def _process_claude_response(
        self,
        response: str,
        task_id: str,
        task_description: str,
        execution_time: float
    ) -> Dict[str, Any]:
        """Process Claude's response and extract structured information"""
        
        # Basic response processing
        result = {
            'success': True,
            'response': response,
            'execution_time': execution_time,
            'task_id': task_id,
            'response_length': len(response),
            'timestamp': datetime.now().isoformat()
        }
        
        # Extract code blocks if present
        code_blocks = self._extract_code_blocks(response)
        if code_blocks:
            result['code_blocks'] = code_blocks
            result['languages_used'] = list(set(block.get('language', 'unknown') for block in code_blocks))
        
        # Extract file operations if mentioned
        file_operations = self._extract_file_operations(response)
        if file_operations:
            result['file_operations'] = file_operations
        
        # Analyze for learning patterns
        learning_insights = self._extract_learning_insights(response)
        if learning_insights:
            result['learning_insights'] = learning_insights
        
        # Determine if this appears to be a successful solution
        success_indicators = ['implementation', 'solution', 'complete', 'working', 'tested']
        error_indicators = ['error', 'failed', 'cannot', 'unable', 'issue']
        
        success_score = sum(1 for indicator in success_indicators if indicator in response.lower())
        error_score = sum(1 for indicator in error_indicators if indicator in response.lower())
        
        result['confidence_score'] = min(1.0, max(0.1, (success_score - error_score * 0.5) / 10))
        result['appears_successful'] = success_score > error_score
        
        return result
    
    async def _learn_from_interaction(
        self,
        task_id: str,
        task_description: str,
        task_context: Optional[Dict[str, Any]],
        code_context: Optional[Dict[str, Any]],
        memories_used: List[MemoryQueryResult],
        claude_response: str,
        result: Dict[str, Any]
    ):
        """Learn from the interaction and store new memories"""
        
        try:
            # Store the interaction as a conversation memory
            await self.memory_manager.store_memory(
                task_id=task_id,
                memory_type=MemoryType.CONVERSATION,
                content=f"Task: {task_description}\nResponse: {claude_response[:500]}...",
                task_context=task_context or {},
                code_context=code_context or {},
                outcome_context=result,
                confidence_score=result.get('confidence_score', 0.5)
            )
            
            # If the response appears successful, store as learning
            if result.get('appears_successful', False) and result.get('confidence_score', 0) > self.learning_confidence_threshold:
                
                # Extract and store successful patterns
                if result.get('code_blocks'):
                    for i, code_block in enumerate(result['code_blocks']):
                        await self.memory_manager.store_memory(
                            task_id=task_id,
                            memory_type=MemoryType.CODE_PATTERN,
                            content=f"Successful {code_block.get('language', 'code')} pattern for {task_context.get('task_type', 'development')}: {code_block.get('code', '')[:300]}",
                            code_context={
                                'language': code_block.get('language'),
                                'code_type': 'implementation',
                                'block_index': i
                            },
                            task_context=task_context or {},
                            outcome_context={'success': True, 'confidence': result.get('confidence_score')},
                            confidence_score=result.get('confidence_score', 0.8)
                        )
                
                # Store general learning
                learning_content = f"Successfully completed {task_context.get('task_type', 'development')} task: {task_description}"
                if result.get('learning_insights'):
                    learning_content += f"\nKey insights: {result['learning_insights']}"
                
                await self.memory_manager.store_memory(
                    task_id=task_id,
                    memory_type=MemoryType.SUCCESS,
                    content=learning_content,
                    task_context=task_context or {},
                    code_context=code_context or {},
                    outcome_context=result,
                    confidence_score=result.get('confidence_score', 0.8)
                )
                
                self.learned_patterns_count += 1
            
            # Store optimization patterns if found
            if 'optimization' in claude_response.lower() or 'performance' in claude_response.lower():
                await self.memory_manager.store_memory(
                    task_id=task_id,
                    memory_type=MemoryType.OPTIMIZATION,
                    content=f"Optimization approach for {task_description}: {claude_response[:400]}...",
                    task_context=task_context or {},
                    code_context=code_context or {},
                    outcome_context=result,
                    confidence_score=result.get('confidence_score', 0.6)
                )
            
            logger.debug(f"Stored learning memories for task {task_id}")
            
        except Exception as e:
            logger.error(f"Error learning from interaction: {e}")
    
    def _extract_code_blocks(self, response: str) -> List[Dict[str, Any]]:
        """Extract code blocks from Claude's response"""
        import re
        
        # Pattern to match code blocks with language specification
        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        
        code_blocks = []
        for language, code in matches:
            code_blocks.append({
                'language': language or 'unknown',
                'code': code.strip(),
                'length': len(code.strip())
            })
        
        return code_blocks
    
    def _extract_file_operations(self, response: str) -> List[str]:
        """Extract file operations mentioned in response"""
        import re
        
        file_operations = []
        
        # Look for file-related operations
        patterns = [
            r'create.*?file.*?`([^`]+)`',
            r'modify.*?file.*?`([^`]+)`',
            r'save.*?to.*?`([^`]+)`',
            r'write.*?to.*?`([^`]+)`'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            file_operations.extend(matches)
        
        return list(set(file_operations))  # Remove duplicates
    
    def _extract_learning_insights(self, response: str) -> List[str]:
        """Extract learning insights from response"""
        insights = []
        
        # Look for key insight phrases
        insight_indicators = [
            'important to note',
            'key consideration',
            'best practice',
            'common mistake',
            'optimization tip',
            'security consideration',
            'performance tip'
        ]
        
        lines = response.split('\n')
        for line in lines:
            line_lower = line.lower()
            for indicator in insight_indicators:
                if indicator in line_lower:
                    insights.append(line.strip())
                    break
        
        return insights[:5]  # Limit to top 5 insights
    
    async def get_interaction_statistics(self) -> Dict[str, Any]:
        """Get statistics about interactions with memory enhancement"""
        
        return {
            'total_interactions': self.interactions_count,
            'memory_enhanced_interactions': self.memory_enhanced_interactions,
            'memory_enhancement_rate': self.memory_enhanced_interactions / max(1, self.interactions_count),
            'learned_patterns_count': self.learned_patterns_count,
            'agent_id': self.agent_id,
            'model': self.model
        }