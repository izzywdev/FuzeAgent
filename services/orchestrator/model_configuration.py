"""
Model Configuration and API Key Management for FuzeAgent

Manages model configurations and API keys for different AI providers at the
organization level, with secure storage and agent-specific model selection.

Supports:
- Multiple AI model providers (Anthropic, OpenAI, Google, etc.)
- Organization-level API key management
- Agent-specific model configurations
- Secure credential storage and access
- Model capability matching
- Cost optimization
"""

import base64
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from cryptography.fernet import Fernet

from .database import DatabaseManager

logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"
    COHERE = "cohere"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"
    CUSTOM = "custom"


class ModelCapability(str, Enum):
    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    REASONING = "reasoning"
    ANALYSIS = "analysis"
    CONVERSATION = "conversation"
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"
    EMBEDDINGS = "embeddings"


@dataclass
class ModelSpec:
    """Specification for an AI model"""

    model_id: str
    provider: ModelProvider
    name: str
    description: str
    capabilities: List[ModelCapability]
    context_window: int
    max_output_tokens: int
    cost_per_input_token: float  # USD per 1K tokens
    cost_per_output_token: float  # USD per 1K tokens
    supports_streaming: bool = True
    supports_function_calling: bool = False
    supports_vision: bool = False
    supports_json_mode: bool = False
    temperature_range: tuple = (0.0, 2.0)
    recommended_use_cases: List[str] = field(default_factory=list)


@dataclass
class ProviderCredentials:
    """Secure storage for provider API credentials"""

    provider: ModelProvider
    encrypted_api_key: str
    endpoint_url: Optional[str] = None
    additional_config: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    is_active: bool = True


@dataclass
class AgentModelConfig:
    """Model configuration for an agent"""

    agent_id: str
    primary_model: str  # model_id
    fallback_models: List[str] = field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    custom_instructions: str = ""
    use_function_calling: bool = True
    streaming_enabled: bool = True
    cost_limit_per_task: Optional[float] = None  # USD
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class ModelConfigurationManager:
    """
    Manages AI model configurations and provider credentials.

    Features:
    - Secure API key storage with encryption
    - Organization-level credential management
    - Agent-specific model configurations
    - Model capability matching
    - Cost tracking and limits
    - Automatic fallback handling
    """

    def __init__(self):
        self.encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key)
        self.available_models = self._initialize_model_specs()

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for API credentials"""
        key_file = "/tmp/fuzeagent_encryption.key"

        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            return key

    def _initialize_model_specs(self) -> Dict[str, ModelSpec]:
        """Initialize available model specifications"""
        models = {}

        # Anthropic Claude models
        models["claude-3-5-sonnet-20241022"] = ModelSpec(
            model_id="claude-3-5-sonnet-20241022",
            provider=ModelProvider.ANTHROPIC,
            name="Claude 3.5 Sonnet",
            description="Most intelligent model for complex reasoning and coding",
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.REASONING,
                ModelCapability.ANALYSIS,
                ModelCapability.CONVERSATION,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.VISION,
            ],
            context_window=200000,
            max_output_tokens=8192,
            cost_per_input_token=0.003,
            cost_per_output_token=0.015,
            supports_function_calling=True,
            supports_vision=True,
            supports_json_mode=True,
            recommended_use_cases=[
                "complex coding",
                "reasoning",
                "analysis",
                "research",
            ],
        )

        models["claude-3-haiku-20240307"] = ModelSpec(
            model_id="claude-3-haiku-20240307",
            provider=ModelProvider.ANTHROPIC,
            name="Claude 3 Haiku",
            description="Fastest and most cost-effective model for simple tasks",
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.CONVERSATION,
            ],
            context_window=200000,
            max_output_tokens=4096,
            cost_per_input_token=0.00025,
            cost_per_output_token=0.00125,
            supports_function_calling=True,
            supports_vision=True,
            recommended_use_cases=[
                "simple tasks",
                "quick responses",
                "cost optimization",
            ],
        )

        # OpenAI GPT models
        models["gpt-4o"] = ModelSpec(
            model_id="gpt-4o",
            provider=ModelProvider.OPENAI,
            name="GPT-4 Omni",
            description="OpenAI's most capable multimodal model",
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.REASONING,
                ModelCapability.ANALYSIS,
                ModelCapability.CONVERSATION,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.VISION,
            ],
            context_window=128000,
            max_output_tokens=4096,
            cost_per_input_token=0.005,
            cost_per_output_token=0.015,
            supports_function_calling=True,
            supports_vision=True,
            supports_json_mode=True,
            recommended_use_cases=[
                "multimodal tasks",
                "function calling",
                "complex reasoning",
            ],
        )

        models["gpt-4o-mini"] = ModelSpec(
            model_id="gpt-4o-mini",
            provider=ModelProvider.OPENAI,
            name="GPT-4 Omni Mini",
            description="Cost-effective model for simpler tasks",
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.CONVERSATION,
                ModelCapability.FUNCTION_CALLING,
            ],
            context_window=128000,
            max_output_tokens=16384,
            cost_per_input_token=0.00015,
            cost_per_output_token=0.0006,
            supports_function_calling=True,
            supports_json_mode=True,
            recommended_use_cases=["cost optimization", "simple tasks", "high volume"],
        )

        # Google Gemini models
        models["gemini-1.5-pro"] = ModelSpec(
            model_id="gemini-1.5-pro",
            provider=ModelProvider.GOOGLE,
            name="Gemini 1.5 Pro",
            description="Google's most capable model with long context",
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.REASONING,
                ModelCapability.ANALYSIS,
                ModelCapability.CONVERSATION,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.VISION,
            ],
            context_window=2000000,  # 2M tokens
            max_output_tokens=8192,
            cost_per_input_token=0.00125,
            cost_per_output_token=0.005,
            supports_function_calling=True,
            supports_vision=True,
            recommended_use_cases=[
                "long context",
                "document analysis",
                "multimodal tasks",
            ],
        )

        return models

    async def store_provider_credentials(
        self,
        organization_id: str,
        provider: ModelProvider,
        api_key: str,
        endpoint_url: Optional[str] = None,
        additional_config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Store encrypted API credentials for a provider"""
        try:
            # Encrypt the API key
            encrypted_key = self.fernet.encrypt(api_key.encode()).decode()

            credentials = ProviderCredentials(
                provider=provider,
                encrypted_api_key=encrypted_key,
                endpoint_url=endpoint_url,
                additional_config=additional_config or {},
            )

            # Store in database
            await DatabaseManager.store_provider_credentials(organization_id, credentials.__dict__)

            logger.info(f"Stored credentials for {provider} in organization {organization_id}")
            return True

        except Exception as e:
            logger.error(f"Error storing provider credentials: {e}")
            return False

    async def get_provider_credentials(self, organization_id: str, provider: ModelProvider) -> Optional[str]:
        """Get decrypted API key for a provider"""
        try:
            credentials_data = await DatabaseManager.get_provider_credentials(organization_id, provider.value)

            if not credentials_data:
                return None

            # Decrypt the API key
            encrypted_key = credentials_data["encrypted_api_key"]
            decrypted_key = self.fernet.decrypt(encrypted_key.encode()).decode()

            # Update last used timestamp
            await DatabaseManager.update_credentials_last_used(organization_id, provider.value)

            return decrypted_key

        except Exception as e:
            logger.error(f"Error retrieving provider credentials: {e}")
            return None

    async def configure_agent_model(self, agent_id: str, model_config: AgentModelConfig) -> bool:
        """Configure model settings for an agent"""
        try:
            # Validate primary model exists
            if model_config.primary_model not in self.available_models:
                raise ValueError(f"Unknown model: {model_config.primary_model}")

            # Validate fallback models
            for model_id in model_config.fallback_models:
                if model_id not in self.available_models:
                    raise ValueError(f"Unknown fallback model: {model_id}")

            # Store configuration
            await DatabaseManager.store_agent_model_config(agent_id, model_config.__dict__)

            logger.info(f"Configured model settings for agent {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Error configuring agent model: {e}")
            return False

    async def get_agent_model_config(self, agent_id: str) -> Optional[AgentModelConfig]:
        """Get model configuration for an agent"""
        try:
            config_data = await DatabaseManager.get_agent_model_config(agent_id)

            if not config_data:
                # Return default configuration
                return AgentModelConfig(
                    agent_id=agent_id,
                    primary_model="claude-3-5-sonnet-20241022",  # Default to Claude 3.5 Sonnet
                )

            return AgentModelConfig(**config_data)

        except Exception as e:
            logger.error(f"Error getting agent model config: {e}")
            return None

    async def get_model_for_task(
        self,
        agent_id: str,
        task_capabilities: List[ModelCapability],
        cost_limit: Optional[float] = None,
    ) -> Optional[str]:
        """Select best model for a task based on capabilities and cost"""
        try:
            agent_config = await self.get_agent_model_config(agent_id)
            if not agent_config:
                return None

            # Check if primary model supports required capabilities
            primary_model = self.available_models.get(agent_config.primary_model)
            if primary_model and all(cap in primary_model.capabilities for cap in task_capabilities):
                # Check cost limit if specified
                if cost_limit is None or self._estimate_task_cost(primary_model, 1000) <= cost_limit:
                    return agent_config.primary_model

            # Try fallback models
            for model_id in agent_config.fallback_models:
                model = self.available_models.get(model_id)
                if model and all(cap in model.capabilities for cap in task_capabilities):
                    if cost_limit is None or self._estimate_task_cost(model, 1000) <= cost_limit:
                        return model_id

            # No suitable model found
            logger.warning(f"No suitable model found for agent {agent_id} with capabilities {task_capabilities}")
            return None

        except Exception as e:
            logger.error(f"Error selecting model for task: {e}")
            return None

    def _estimate_task_cost(self, model: ModelSpec, estimated_tokens: int) -> float:
        """Estimate cost for a task with given token count"""
        # Simple estimation assuming 70% input, 30% output tokens
        input_tokens = int(estimated_tokens * 0.7)
        output_tokens = int(estimated_tokens * 0.3)

        input_cost = (input_tokens / 1000) * model.cost_per_input_token
        output_cost = (output_tokens / 1000) * model.cost_per_output_token

        return input_cost + output_cost

    async def get_available_models(
        self,
        organization_id: str,
        provider: Optional[ModelProvider] = None,
        capabilities: Optional[List[ModelCapability]] = None,
    ) -> List[Dict[str, Any]]:
        """Get available models with provider credential validation"""
        available = []

        for model_id, model in self.available_models.items():
            # Filter by provider if specified
            if provider and model.provider != provider:
                continue

            # Filter by capabilities if specified
            if capabilities and not all(cap in model.capabilities for cap in capabilities):
                continue

            # Check if organization has credentials for this provider
            has_credentials = await self.get_provider_credentials(organization_id, model.provider) is not None

            model_info = {
                "model_id": model_id,
                "provider": model.provider.value,
                "name": model.name,
                "description": model.description,
                "capabilities": [cap.value for cap in model.capabilities],
                "context_window": model.context_window,
                "max_output_tokens": model.max_output_tokens,
                "cost_per_input_token": model.cost_per_input_token,
                "cost_per_output_token": model.cost_per_output_token,
                "supports_streaming": model.supports_streaming,
                "supports_function_calling": model.supports_function_calling,
                "supports_vision": model.supports_vision,
                "supports_json_mode": model.supports_json_mode,
                "recommended_use_cases": model.recommended_use_cases,
                "has_credentials": has_credentials,
                "available": has_credentials,
            }

            available.append(model_info)

        return available

    async def get_organization_model_usage(self, organization_id: str, days: int = 30) -> Dict[str, Any]:
        """Get model usage statistics for an organization"""
        try:
            usage_data = await DatabaseManager.get_model_usage_stats(organization_id, days)

            return {
                "organization_id": organization_id,
                "period_days": days,
                "total_requests": usage_data.get("total_requests", 0),
                "total_tokens": usage_data.get("total_tokens", 0),
                "total_cost": usage_data.get("total_cost", 0.0),
                "model_breakdown": usage_data.get("model_breakdown", {}),
                "agent_breakdown": usage_data.get("agent_breakdown", {}),
                "daily_usage": usage_data.get("daily_usage", []),
            }

        except Exception as e:
            logger.error(f"Error getting model usage: {e}")
            return {}

    async def estimate_task_cost(self, agent_id: str, task_description: str, estimated_complexity: str = "medium") -> Dict[str, Any]:
        """Estimate cost for a task execution"""
        try:
            agent_config = await self.get_agent_model_config(agent_id)
            if not agent_config:
                return {"error": "Agent configuration not found"}

            model = self.available_models.get(agent_config.primary_model)
            if not model:
                return {"error": "Model specification not found"}

            # Estimate token usage based on complexity
            token_estimates = {
                "low": 2000,
                "medium": 5000,
                "high": 10000,
                "very_high": 20000,
            }

            estimated_tokens = token_estimates.get(estimated_complexity, 5000)
            estimated_cost = self._estimate_task_cost(model, estimated_tokens)

            return {
                "agent_id": agent_id,
                "model": model.model_id,
                "estimated_tokens": estimated_tokens,
                "estimated_cost_usd": round(estimated_cost, 4),
                "complexity": estimated_complexity,
                "cost_breakdown": {
                    "input_cost": (estimated_tokens * 0.7 / 1000) * model.cost_per_input_token,
                    "output_cost": (estimated_tokens * 0.3 / 1000) * model.cost_per_output_token,
                },
            }

        except Exception as e:
            logger.error(f"Error estimating task cost: {e}")
            return {"error": str(e)}


# Global instance
model_config_manager = ModelConfigurationManager()
