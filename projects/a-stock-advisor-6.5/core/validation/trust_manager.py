"""
结果可信度管理器

管理整个管线的输出结果可信度。
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from .contracts import (
    TrustLevel,
    LayerCheckResult,
    PipelineCheckResult,
    CheckResult,
    RequirementType
)


class TrustManager:
    """
    结果可信度管理器
    
    管理整个管线的输出结果可信度，实现可信度传递规则和失败回退机制。
    """
    
    def __init__(self):
        """初始化可信度管理器"""
        self.layer_results: Dict[str, LayerCheckResult] = {}
        self.current_trust_level = TrustLevel.TRUSTED
        self.failed_layer: Optional[str] = None
        self.check_history: List[Dict[str, Any]] = []
    
    def update_layer_result(self, result: LayerCheckResult) -> TrustLevel:
        """
        更新层检查结果
        
        Args:
            result: 层检查结果
            
        Returns:
            TrustLevel: 更新后的整体可信度
        """
        self.layer_results[result.layer_name] = result
        
        # 更新整体可信度
        self._update_overall_trust_level()
        
        # 记录历史
        self.check_history.append({
            'timestamp': datetime.now().isoformat(),
            'layer': result.layer_name,
            'trust_level': result.trust_level.value,
            'score': result.score,
            'passed': result.passed
        })
        
        return self.current_trust_level
    
    def _update_overall_trust_level(self):
        """更新整体可信度"""
        # 按层序号排序
        sorted_results = sorted(
            self.layer_results.values(),
            key=lambda r: r.layer_step
        )
        
        # 检查是否有硬性失败
        has_hard_failure = any(
            r.trust_level == TrustLevel.UNTRUSTED 
            for r in sorted_results
        )
        
        if has_hard_failure:
            self.current_trust_level = TrustLevel.UNTRUSTED
            # 找到第一个失败的层
            for r in sorted_results:
                if r.trust_level == TrustLevel.UNTRUSTED:
                    self.failed_layer = r.layer_name
                    break
        else:
            # 检查是否有弹性警告
            has_warnings = any(
                r.trust_level == TrustLevel.PARTIAL 
                for r in sorted_results
            )
            
            if has_warnings:
                self.current_trust_level = TrustLevel.PARTIAL
            else:
                self.current_trust_level = TrustLevel.TRUSTED
            
            self.failed_layer = None
    
    def get_overall_result(self) -> PipelineCheckResult:
        """
        获取整体检查结果
        
        Returns:
            PipelineCheckResult: 管线整体检查结果
        """
        # 计算整体分数
        if self.layer_results:
            overall_score = sum(r.score for r in self.layer_results.values()) / len(self.layer_results)
        else:
            overall_score = 100.0
        
        # 按层序号排序
        sorted_results = sorted(
            self.layer_results.values(),
            key=lambda r: r.layer_step
        )
        
        return PipelineCheckResult(
            overall_trust_level=self.current_trust_level,
            overall_score=overall_score,
            layer_results=sorted_results,
            failed_layer=self.failed_layer,
            timestamp=datetime.now().isoformat()
        )
    
    def can_proceed(self) -> bool:
        """
        是否可以继续执行
        
        Returns:
            bool: 是否可以继续
        """
        return self.current_trust_level != TrustLevel.UNTRUSTED
    
    def get_failed_layer(self) -> Optional[str]:
        """
        获取首次失败的层
        
        Returns:
            Optional[str]: 失败层名称
        """
        return self.failed_layer
    
    def get_layer_result(self, layer_name: str) -> Optional[LayerCheckResult]:
        """
        获取指定层的结果
        
        Args:
            layer_name: 层名称
            
        Returns:
            Optional[LayerCheckResult]: 层检查结果
        """
        return self.layer_results.get(layer_name)
    
    def get_hard_failures(self) -> List[CheckResult]:
        """
        获取所有硬性失败项
        
        Returns:
            List[CheckResult]: 硬性失败列表
        """
        failures = []
        for result in self.layer_results.values():
            failures.extend(result.hard_failures)
        return failures
    
    def get_elastic_warnings(self) -> List[CheckResult]:
        """
        获取所有弹性警告项
        
        Returns:
            List[CheckResult]: 弹性警告列表
        """
        warnings = []
        for result in self.layer_results.values():
            warnings.extend(result.elastic_warnings)
        return warnings
    
    def reset(self):
        """重置状态"""
        self.layer_results.clear()
        self.current_trust_level = TrustLevel.TRUSTED
        self.failed_layer = None
        self.check_history.clear()
    
    def clear_from_layer(self, layer_name: str):
        """
        从指定层开始清除结果
        
        Args:
            layer_name: 层名称
        """
        # 找到该层的序号
        target_step = None
        for name, result in list(self.layer_results.items()):
            if name == layer_name:
                target_step = result.layer_step
                break
        
        if target_step is not None:
            # 清除该层及之后的所有结果
            for name, result in list(self.layer_results.items()):
                if result.layer_step >= target_step:
                    del self.layer_results[name]
        
        # 重新计算可信度
        self._update_overall_trust_level()


# 全局可信度管理器实例
_default_trust_manager: Optional[TrustManager] = None


def get_trust_manager() -> TrustManager:
    """
    获取全局可信度管理器实例
    
    Returns:
        TrustManager: 可信度管理器
    """
    global _default_trust_manager
    if _default_trust_manager is None:
        _default_trust_manager = TrustManager()
    return _default_trust_manager


def reset_trust_manager():
    """重置全局可信度管理器"""
    global _default_trust_manager
    _default_trust_manager = TrustManager()
