"""
检查器基类

所有层检查器的抽象基类。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from datetime import datetime

from ..contracts import (
    CheckResult, 
    LayerCheckResult, 
    TrustLevel,
    RequirementType
)


class BaseLayerChecker(ABC):
    """层检查器基类"""
    
    def __init__(self, layer_name: str, layer_step: int):
        """
        初始化检查器
        
        Args:
            layer_name: 层名称
            layer_step: 层序号
        """
        self.layer_name = layer_name
        self.layer_step = layer_step
    
    @abstractmethod
    def check(self, data: Any, context: Dict[str, Any] = None) -> LayerCheckResult:
        """
        执行检查
        
        Args:
            data: 要检查的数据
            context: 检查上下文
            
        Returns:
            LayerCheckResult: 检查结果
        """
        pass
    
    def _create_result(
        self,
        results: List[CheckResult],
        timestamp: str = None
    ) -> LayerCheckResult:
        """
        创建检查结果
        
        Args:
            results: 各要求检查结果
            timestamp: 检查时间
            
        Returns:
            LayerCheckResult: 层检查结果
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        # 判断可信度等级
        hard_failures = [r for r in results if r.is_critical]
        elastic_warnings = [r for r in results 
                          if r.req_type == RequirementType.ELASTIC and not r.passed]
        
        if hard_failures:
            trust_level = TrustLevel.UNTRUSTED
        elif elastic_warnings:
            trust_level = TrustLevel.PARTIAL
        else:
            trust_level = TrustLevel.TRUSTED
        
        # 计算质量分数
        score = self._calculate_score(results)
        
        return LayerCheckResult(
            layer_name=self.layer_name,
            layer_step=self.layer_step,
            results=results,
            trust_level=trust_level,
            score=score,
            timestamp=timestamp
        )
    
    def _calculate_score(self, results: List[CheckResult]) -> float:
        """
        计算质量分数
        
        Args:
            results: 检查结果列表
            
        Returns:
            float: 质量分数 (0-100)
        """
        if not results:
            return 100.0
        
        # 硬性要求权重
        hard_results = [r for r in results if r.req_type == RequirementType.HARD]
        elastic_results = [r for r in results if r.req_type == RequirementType.ELASTIC]
        
        # 硬性要求不通过则0分
        if hard_results and not all(r.passed for r in hard_results):
            return 0.0
        
        # 弹性要求计算分数
        if not elastic_results:
            return 100.0
        
        passed_count = sum(1 for r in elastic_results if r.passed)
        score = (passed_count / len(elastic_results)) * 100
        
        return score
    
    def _create_check_result(
        self,
        req_id: str,
        req_name: str,
        req_type: RequirementType,
        passed: bool,
        actual_value: Any,
        expected_value: Any,
        message: str,
        details: Dict[str, Any] = None
    ) -> CheckResult:
        """
        创建单个检查结果
        
        Args:
            req_id: 要求编号
            req_name: 要求名称
            req_type: 要求类型
            passed: 是否通过
            actual_value: 实际值
            expected_value: 期望值
            message: 检查消息
            details: 详细信息
            
        Returns:
            CheckResult: 检查结果
        """
        return CheckResult(
            requirement_id=req_id,
            requirement_name=req_name,
            req_type=req_type,
            passed=passed,
            actual_value=actual_value,
            expected_value=expected_value,
            message=message,
            details=details or {}
        )
