"""
RDAgent Configuration Module

Configuration settings for Microsoft RDAgent integration.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class LLMProvider(Enum):
    OPENAI = "openai"
    AZURE = "azure"
    DEEPSEEK = "deepseek"
    SILICONFLOW = "siliconflow"


class RDAgentScenario(Enum):
    FIN_QUANT = "fin_quant"
    FIN_FACTOR = "fin_factor"
    FIN_MODEL = "fin_model"
    FIN_FACTOR_REPORT = "fin_factor_report"
    GENERAL_MODEL = "general_model"
    DATA_SCIENCE = "data_science"


@dataclass
class RDAgentConfig:
    """Configuration for RDAgent integration"""
    
    llm_provider: LLMProvider = LLMProvider.OPENAI
    chat_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"
    
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    
    deepseek_api_key: Optional[str] = None
    azure_api_key: Optional[str] = None
    azure_api_base: Optional[str] = None
    azure_api_version: str = "2024-02-01"
    
    litellm_proxy_api_key: Optional[str] = None
    litellm_proxy_api_base: Optional[str] = None
    
    log_dir: str = "log/rdagent"
    port: int = 19899
    
    reasoning_think_rm: bool = False
    
    scenario: RDAgentScenario = RDAgentScenario.FIN_FACTOR
    
    report_folder: Optional[str] = None
    paper_url: Optional[str] = None
    competition_name: Optional[str] = None
    
    max_iterations: int = 10
    auto_register_factors: bool = True
    
    def __post_init__(self):
        self._load_from_env()
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        if not self.api_key:
            self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_base:
            self.api_base = os.getenv("OPENAI_API_BASE")
        if not self.deepseek_api_key:
            self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.azure_api_key:
            self.azure_api_key = os.getenv("AZURE_API_KEY")
        if not self.azure_api_base:
            self.azure_api_base = os.getenv("AZURE_API_BASE")
        if not self.litellm_proxy_api_key:
            self.litellm_proxy_api_key = os.getenv("LITELLM_PROXY_API_KEY")
        if not self.litellm_proxy_api_base:
            self.litellm_proxy_api_base = os.getenv("LITELLM_PROXY_API_BASE")
        
        reasoning_rm = os.getenv("REASONING_THINK_RM", "").lower()
        self.reasoning_think_rm = reasoning_rm in ("true", "1", "yes")
    
    def to_env_dict(self) -> dict:
        """Convert config to environment variables dict"""
        env_vars = {
            "CHAT_MODEL": self.chat_model,
            "EMBEDDING_MODEL": self.embedding_model,
        }
        
        if self.llm_provider == LLMProvider.OPENAI:
            if self.api_key:
                env_vars["OPENAI_API_KEY"] = self.api_key
            if self.api_base:
                env_vars["OPENAI_API_BASE"] = self.api_base
        
        elif self.llm_provider == LLMProvider.DEEPSEEK:
            if self.deepseek_api_key:
                env_vars["DEEPSEEK_API_KEY"] = self.deepseek_api_key
            if self.litellm_proxy_api_key:
                env_vars["LITELLM_PROXY_API_KEY"] = self.litellm_proxy_api_key
            if self.litellm_proxy_api_base:
                env_vars["LITELLM_PROXY_API_BASE"] = self.litellm_proxy_api_base
        
        elif self.llm_provider == LLMProvider.AZURE:
            if self.azure_api_key:
                env_vars["AZURE_API_KEY"] = self.azure_api_key
            if self.azure_api_base:
                env_vars["AZURE_API_BASE"] = self.azure_api_base
            env_vars["AZURE_API_VERSION"] = self.azure_api_version
        
        if self.reasoning_think_rm:
            env_vars["REASONING_THINK_RM"] = "True"
        
        return env_vars
    
    def validate(self) -> tuple[bool, str]:
        """Validate configuration"""
        if self.llm_provider == LLMProvider.OPENAI:
            if not self.api_key:
                return False, "OpenAI API key is required. Set OPENAI_API_KEY environment variable."
        
        elif self.llm_provider == LLMProvider.DEEPSEEK:
            if not self.deepseek_api_key:
                return False, "DeepSeek API key is required. Set DEEPSEEK_API_KEY environment variable."
            if not self.litellm_proxy_api_key:
                return False, "LiteLLM Proxy API key is required for embedding. Set LITELLM_PROXY_API_KEY environment variable."
        
        elif self.llm_provider == LLMProvider.AZURE:
            if not self.azure_api_key:
                return False, "Azure API key is required. Set AZURE_API_KEY environment variable."
            if not self.azure_api_base:
                return False, "Azure API base is required. Set AZURE_API_BASE environment variable."
        
        return True, "Configuration is valid."
    
    @classmethod
    def for_deepseek(cls, deepseek_key: str, embedding_key: str, embedding_base: str = "https://api.siliconflow.cn/v1") -> "RDAgentConfig":
        """Create config for DeepSeek provider"""
        return cls(
            llm_provider=LLMProvider.DEEPSEEK,
            chat_model="deepseek/deepseek-chat",
            embedding_model="litellm_proxy/BAAI/bge-m3",
            deepseek_api_key=deepseek_key,
            litellm_proxy_api_key=embedding_key,
            litellm_proxy_api_base=embedding_base,
        )
    
    @classmethod
    def for_openai(cls, api_key: str, api_base: Optional[str] = None, model: str = "gpt-4o") -> "RDAgentConfig":
        """Create config for OpenAI provider"""
        return cls(
            llm_provider=LLMProvider.OPENAI,
            chat_model=model,
            embedding_model="text-embedding-3-small",
            api_key=api_key,
            api_base=api_base,
        )
    
    @classmethod
    def for_azure(cls, api_key: str, api_base: str, chat_deployment: str, embedding_deployment: str, api_version: str = "2024-02-01") -> "RDAgentConfig":
        """Create config for Azure OpenAI provider"""
        return cls(
            llm_provider=LLMProvider.AZURE,
            chat_model=f"azure/{chat_deployment}",
            embedding_model=f"azure/{embedding_deployment}",
            azure_api_key=api_key,
            azure_api_base=api_base,
            azure_api_version=api_version,
        )
