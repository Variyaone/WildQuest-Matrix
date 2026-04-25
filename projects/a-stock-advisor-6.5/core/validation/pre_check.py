"""
前置检查管理器

统一管理所有模块的前置检查，确保输出结果可信。
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from .contracts import (
    TrustLevel,
    LayerCheckResult,
    PipelineCheckResult,
    LAYER_CONTRACTS
)
from .freshness import FreshnessPolicy, ExecutionMode, get_freshness_policy
from .trust_manager import TrustManager, get_trust_manager
from .reporter import CheckReporter
from .checkers import (
    DataLayerChecker,
    FactorLayerChecker,
    StrategyLayerChecker,
    PortfolioLayerChecker,
    RiskLayerChecker,
    TradingLayerChecker
)


class PreCheckManager:
    """
    前置检查管理器
    
    统一管理所有模块的前置检查，定义各层的硬性要求（H）、弹性要求（E）、
    边际要求（M），按顺序执行检查，记录检查结果，管理结果可信度。
    """
    
    # 层检查器映射
    LAYER_CHECKERS = {
        'data': DataLayerChecker,
        'factor': FactorLayerChecker,
        'strategy': StrategyLayerChecker,
        'portfolio': PortfolioLayerChecker,
        'risk': RiskLayerChecker,
        'trading': TradingLayerChecker,
    }
    
    def __init__(
        self,
        mode: ExecutionMode = ExecutionMode.LIVE_TRADING,
        trust_manager: Optional[TrustManager] = None,
        freshness_policy: Optional[FreshnessPolicy] = None
    ):
        """
        初始化前置检查管理器
        
        Args:
            mode: 执行场景模式
            trust_manager: 可信度管理器（默认创建新实例）
            freshness_policy: 新鲜度策略（默认根据mode创建）
        """
        self.mode = mode
        self.trust_manager = trust_manager or TrustManager()
        self.freshness_policy = freshness_policy or FreshnessPolicy(mode)
        self.reporter = CheckReporter()
        
        # 初始化检查器
        self.checkers = {
            name: checker_class()
            for name, checker_class in self.LAYER_CHECKERS.items()
        }
    
    def check_layer(
        self,
        layer_name: str,
        data: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> LayerCheckResult:
        """
        检查指定层
        
        Args:
            layer_name: 层名称 (data/factor/strategy/portfolio/risk/trading)
            data: 要检查的数据
            context: 检查上下文
            
        Returns:
            LayerCheckResult: 层检查结果
        """
        if layer_name not in self.checkers:
            raise ValueError(f"未知的层名称: {layer_name}")
        
        checker = self.checkers[layer_name]
        result = checker.check(data, context)
        
        # 更新可信度管理器
        self.trust_manager.update_layer_result(result)
        
        return result
    
    def check_all_layers(
        self,
        layer_data: Dict[str, Any],
        contexts: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> PipelineCheckResult:
        """
        检查所有层
        
        Args:
            layer_data: 各层数据 {layer_name: data}
            contexts: 各层检查上下文 {layer_name: context}
            
        Returns:
            PipelineCheckResult: 管线整体检查结果
        """
        contexts = contexts or {}
        
        # 按层序号排序
        sorted_layers = sorted(
            layer_data.items(),
            key=lambda x: self._get_layer_step(x[0])
        )
        
        for layer_name, data in sorted_layers:
            context = contexts.get(layer_name, {})
            result = self.check_layer(layer_name, data, context)
            
            # 如果硬性要求失败，停止检查
            if not result.passed:
                break
        
        return self.trust_manager.get_overall_result()
    
    def _get_layer_step(self, layer_name: str) -> int:
        """获取层序号"""
        step_map = {
            'data': 1,
            'factor': 2,
            'strategy': 3,
            'portfolio': 4,
            'risk': 5,
            'trading': 6,
        }
        return step_map.get(layer_name, 99)
    
    def check_freshness(
        self,
        layer: str,
        data_type: str,
        last_update: Optional[datetime],
        current_time: Optional[datetime] = None
    ) -> bool:
        """
        检查数据新鲜度
        
        Args:
            layer: 层名称
            data_type: 数据类型
            last_update: 最后更新时间
            current_time: 当前时间
            
        Returns:
            bool: 是否新鲜
        """
        result = self.freshness_policy.check_freshness(
            layer, data_type, last_update, current_time
        )
        return result.is_fresh
    
    def can_proceed(self) -> bool:
        """
        是否可以继续执行
        
        Returns:
            bool: 是否可以继续
        """
        return self.trust_manager.can_proceed()
    
    def get_trust_level(self) -> TrustLevel:
        """
        获取当前可信度等级
        
        Returns:
            TrustLevel: 可信度等级
        """
        return self.trust_manager.current_trust_level
    
    def generate_report(self) -> str:
        """
        生成检查报告
        
        Returns:
            str: 格式化的检查报告
        """
        result = self.trust_manager.get_overall_result()
        return self.reporter.generate_report(result)
    
    def generate_summary(self) -> Dict[str, Any]:
        """
        生成报告摘要
        
        Returns:
            Dict: 摘要信息
        """
        result = self.trust_manager.get_overall_result()
        return self.reporter.generate_summary(result)
    
    def reset(self):
        """重置状态"""
        self.trust_manager.reset()
    
    def get_failed_layer(self) -> Optional[str]:
        """
        获取首次失败的层
        
        Returns:
            Optional[str]: 失败层名称
        """
        return self.trust_manager.get_failed_layer()
    
    def clear_from_layer(self, layer_name: str):
        """
        从指定层开始清除结果
        
        Args:
            layer_name: 层名称
        """
        self.trust_manager.clear_from_layer(layer_name)


# 全局前置检查管理器实例
_default_pre_check_manager: Optional[PreCheckManager] = None


def get_pre_check_manager(
    mode: Optional[ExecutionMode] = None
) -> PreCheckManager:
    """
    获取全局前置检查管理器实例
    
    Args:
        mode: 执行场景模式（None则使用默认实例）
        
    Returns:
        PreCheckManager: 前置检查管理器
    """
    global _default_pre_check_manager
    
    if mode is not None or _default_pre_check_manager is None:
        _default_pre_check_manager = PreCheckManager(mode=mode or ExecutionMode.LIVE_TRADING)
    
    return _default_pre_check_manager


def reset_pre_check_manager():
    """重置全局前置检查管理器"""
    global _default_pre_check_manager
    _default_pre_check_manager = None
