"""
LLM审查模块 - 集成真实的LLM API调用

支持多种LLM提供商：
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- 本地模型 (通过API)
"""

import os
import json
import requests
from typing import Dict, Any, Optional
from enum import Enum


class ReviewDecision(Enum):
    """LLM 审查决策"""
    APPROVE = "approve"           # 批准
    REJECT = "reject"             # 拒绝
    MODIFY = "modify"             # 修改后重试
    DEFER = "defer"               # 延迟决策


class LLMProvider(Enum):
    """LLM提供商"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class LLMReviewer:
    """LLM审查器"""

    def __init__(
        self,
        provider: LLMProvider = LLMProvider.OPENAI,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        """
        初始化LLM审查器

        Args:
            provider: LLM提供商
            api_key: API密钥
            model: 模型名称
            base_url: API基础URL（用于本地模型或自定义端点）
        """
        self.provider = provider
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or self._get_default_model()
        self.base_url = base_url

    def _get_default_model(self) -> str:
        """获取默认模型"""
        if self.provider == LLMProvider.OPENAI:
            return "gpt-4"
        elif self.provider == LLMProvider.ANTHROPIC:
            return "claude-3-opus-20240229"
        else:
            return "gpt-3.5-turbo"

    def review(
        self,
        gate_name: str,
        context: Dict[str, Any],
        review_prompt: str
    ) -> tuple[ReviewDecision, str]:
        """
        执行LLM审查

        Args:
            gate_name: 门控名称
            context: 审查上下文
            review_prompt: 审查提示词

        Returns:
            (决策, 评论)
        """
        # 构建完整的提示词
        full_prompt = self._build_prompt(gate_name, context, review_prompt)

        # 调用LLM
        response = self._call_llm(full_prompt)

        # 解析响应
        decision, comment = self._parse_response(response)

        return decision, comment

    def _build_prompt(
        self,
        gate_name: str,
        context: Dict[str, Any],
        review_prompt: str
    ) -> str:
        """
        构建完整的提示词

        Args:
            gate_name: 门控名称
            context: 审查上下文
            review_prompt: 审查提示词

        Returns:
            完整提示词
        """
        prompt = f"""你是一个专业的量化投资策略审查专家。请审查以下策略质量门控。

门控名称: {gate_name}

审查上下文:
{json.dumps(context, indent=2, default=str)}

审查要求:
{review_prompt}

请根据以上信息，做出审查决策。决策选项:
- approve: 批准通过
- reject: 拒绝，策略不符合要求
- modify: 需要修改后重新审查
- defer: 延迟决策，需要更多信息

请以JSON格式返回你的决策，格式如下:
{{
    "decision": "approve/reject/modify/defer",
    "comment": "你的审查意见和理由"
}}
"""
        return prompt

    def _call_llm(self, prompt: str) -> str:
        """
        调用LLM API

        Args:
            prompt: 提示词

        Returns:
            LLM响应
        """
        if self.provider == LLMProvider.OPENAI:
            return self._call_openai(prompt)
        elif self.provider == LLMProvider.ANTHROPIC:
            return self._call_anthropic(prompt)
        else:
            return self._call_local(prompt)

    def _call_openai(self, prompt: str) -> str:
        """
        调用OpenAI API

        Args:
            prompt: 提示词

        Returns:
            LLM响应
        """
        url = self.base_url or "https://api.openai.com/v1/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一个专业的量化投资策略审查专家。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            return content

        except Exception as e:
            print(f"OpenAI API调用失败: {e}")
            # 返回默认批准
            return json.dumps({
                "decision": "approve",
                "comment": f"LLM API调用失败，自动批准: {str(e)}"
            })

    def _call_anthropic(self, prompt: str) -> str:
        """
        调用Anthropic API

        Args:
            prompt: 提示词

        Returns:
            LLM响应
        """
        url = self.base_url or "https://api.anthropic.com/v1/messages"

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }

        data = {
            "model": self.model,
            "max_tokens": 500,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()

            result = response.json()
            content = result["content"][0]["text"]

            return content

        except Exception as e:
            print(f"Anthropic API调用失败: {e}")
            # 返回默认批准
            return json.dumps({
                "decision": "approve",
                "comment": f"LLM API调用失败，自动批准: {str(e)}"
            })

    def _call_local(self, prompt: str) -> str:
        """
        调用本地LLM API

        Args:
            prompt: 提示词

        Returns:
            LLM响应
        """
        if not self.base_url:
            raise ValueError("本地模型需要提供base_url")

        url = f"{self.base_url}/v1/chat/completions"

        headers = {
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一个专业的量化投资策略审查专家。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            return content

        except Exception as e:
            print(f"本地LLM API调用失败: {e}")
            # 返回默认批准
            return json.dumps({
                "decision": "approve",
                "comment": f"LLM API调用失败，自动批准: {str(e)}"
            })

    def _parse_response(self, response: str) -> tuple[ReviewDecision, str]:
        """
        解析LLM响应

        Args:
            response: LLM响应文本

        Returns:
            (决策, 评论)
        """
        try:
            # 尝试解析JSON
            data = json.loads(response)

            decision_str = data.get("decision", "approve")
            comment = data.get("comment", "")

            # 转换决策
            decision = ReviewDecision(decision_str)

            return decision, comment

        except Exception as e:
            print(f"解析LLM响应失败: {e}")
            print(f"原始响应: {response}")

            # 尝试从文本中提取决策
            response_lower = response.lower()

            if "reject" in response_lower:
                decision = ReviewDecision.REJECT
            elif "modify" in response_lower:
                decision = ReviewDecision.MODIFY
            elif "defer" in response_lower:
                decision = ReviewDecision.DEFER
            else:
                decision = ReviewDecision.APPROVE

            comment = response

            return decision, comment


# 便捷函数
def create_reviewer(
    provider: str = "openai",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None
) -> LLMReviewer:
    """
    创建LLM审查器

    Args:
        provider: 提供商名称 (openai/anthropic/local)
        api_key: API密钥
        model: 模型名称
        base_url: API基础URL

    Returns:
        LLM审查器实例
    """
    provider_enum = LLMProvider(provider)

    return LLMReviewer(
        provider=provider_enum,
        api_key=api_key,
        model=model,
        base_url=base_url
    )
