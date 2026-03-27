"""
策略设计器模块

可视化策略设计和配置，支持信号组合配置、调仓频率设置、风控参数配置。
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .registry import (
    StrategyMetadata,
    StrategyType,
    StrategyStatus,
    RebalanceFrequency,
    RiskParams,
    SignalConfig,
    StrategyPerformance,
    get_strategy_registry
)
from ..signal import get_signal_registry
from ..infrastructure.exceptions import StrategyException


@dataclass
class StrategyTemplate:
    """策略模板"""
    name: str
    description: str
    strategy_type: StrategyType
    signal_config: SignalConfig
    rebalance_freq: RebalanceFrequency
    max_positions: int
    risk_params: RiskParams
    tags: List[str] = field(default_factory=list)


BUILTIN_TEMPLATES: Dict[str, StrategyTemplate] = {
    "multi_factor_basic": StrategyTemplate(
        name="多因子选股策略（基础版）",
        description="基于动量、价值、质量因子的量化选股策略",
        strategy_type=StrategyType.MULTI_FACTOR,
        signal_config=SignalConfig(
            signal_ids=["S00001", "S00002", "S00003"],
            weights=[0.4, 0.3, 0.3],
            combination_method="weighted_sum"
        ),
        rebalance_freq=RebalanceFrequency.WEEKLY,
        max_positions=20,
        risk_params=RiskParams(
            max_single_weight=0.1,
            max_industry_weight=0.3,
            stop_loss=-0.1,
            take_profit=0.2
        ),
        tags=["多因子", "选股", "基础"]
    ),
    "momentum_trend": StrategyTemplate(
        name="动量趋势策略",
        description="基于价格动量和趋势跟踪的策略",
        strategy_type=StrategyType.TREND_FOLLOWING,
        signal_config=SignalConfig(
            signal_ids=["S00010"],
            weights=[1.0],
            combination_method="weighted_sum"
        ),
        rebalance_freq=RebalanceFrequency.DAILY,
        max_positions=10,
        risk_params=RiskParams(
            max_single_weight=0.15,
            max_industry_weight=0.4,
            stop_loss=-0.08,
            take_profit=0.3
        ),
        tags=["动量", "趋势", "短线"]
    ),
    "value_investing": StrategyTemplate(
        name="价值投资策略",
        description="基于估值因子的长期价值投资策略",
        strategy_type=StrategyType.STOCK_SELECTION,
        signal_config=SignalConfig(
            signal_ids=["S00020", "S00021"],
            weights=[0.6, 0.4],
            combination_method="weighted_sum"
        ),
        rebalance_freq=RebalanceFrequency.MONTHLY,
        max_positions=15,
        risk_params=RiskParams(
            max_single_weight=0.12,
            max_industry_weight=0.35,
            stop_loss=-0.15,
            take_profit=0.5
        ),
        tags=["价值", "长期", "基本面"]
    ),
    "mean_reversion": StrategyTemplate(
        name="均值回归策略",
        description="基于价格偏离均值的回归策略",
        strategy_type=StrategyType.MEAN_REVERSION,
        signal_config=SignalConfig(
            signal_ids=["S00030"],
            weights=[1.0],
            combination_method="weighted_sum"
        ),
        rebalance_freq=RebalanceFrequency.WEEKLY,
        max_positions=25,
        risk_params=RiskParams(
            max_single_weight=0.08,
            max_industry_weight=0.25,
            stop_loss=-0.05,
            take_profit=0.1
        ),
        tags=["均值回归", "反转", "短线"]
    )
}


class StrategyDesigner:
    """
    策略设计器
    
    支持策略的可视化设计和配置。
    """
    
    def __init__(self):
        """初始化策略设计器"""
        self._registry = get_strategy_registry()
        self._signal_registry = get_signal_registry()
        self._templates = BUILTIN_TEMPLATES.copy()
    
    def list_templates(self) -> Dict[str, StrategyTemplate]:
        """列出所有策略模板"""
        return self._templates
    
    def get_template(self, template_id: str) -> Optional[StrategyTemplate]:
        """获取策略模板"""
        return self._templates.get(template_id)
    
    def add_template(self, template_id: str, template: StrategyTemplate):
        """添加策略模板"""
        self._templates[template_id] = template
    
    def create_from_template(
        self,
        template_id: str,
        name: Optional[str] = None,
        customizations: Optional[Dict[str, Any]] = None
    ) -> StrategyMetadata:
        """
        从模板创建策略
        
        Args:
            template_id: 模板ID
            name: 策略名称（可选）
            customizations: 自定义配置
            
        Returns:
            StrategyMetadata: 创建的策略元数据
        """
        template = self._templates.get(template_id)
        if template is None:
            raise StrategyException(f"模板不存在: {template_id}")
        
        customizations = customizations or {}
        
        signal_config = template.signal_config
        if "signals" in customizations:
            signal_config = SignalConfig(**customizations["signals"])
        
        risk_params = template.risk_params
        if "risk_params" in customizations:
            risk_params = RiskParams(**customizations["risk_params"])
        
        rebalance_freq = template.rebalance_freq
        if "rebalance_freq" in customizations:
            rebalance_freq = RebalanceFrequency(customizations["rebalance_freq"])
        
        max_positions = customizations.get("max_positions", template.max_positions)
        
        return self._registry.register(
            name=name or template.name,
            description=template.description,
            strategy_type=template.strategy_type,
            signals=signal_config,
            rebalance_freq=rebalance_freq,
            max_positions=max_positions,
            risk_params=risk_params,
            tags=template.tags.copy()
        )
    
    def create_custom(
        self,
        name: str,
        description: str,
        strategy_type: StrategyType,
        signal_ids: List[str],
        signal_weights: Optional[List[float]] = None,
        combination_method: str = "weighted_sum",
        rebalance_freq: RebalanceFrequency = RebalanceFrequency.WEEKLY,
        max_positions: int = 20,
        risk_params: Optional[RiskParams] = None,
        tags: Optional[List[str]] = None
    ) -> StrategyMetadata:
        """
        创建自定义策略
        
        Args:
            name: 策略名称
            description: 策略描述
            strategy_type: 策略类型
            signal_ids: 信号ID列表
            signal_weights: 信号权重列表
            combination_method: 组合方法
            rebalance_freq: 调仓频率
            max_positions: 最大持仓数
            risk_params: 风控参数
            tags: 标签列表
            
        Returns:
            StrategyMetadata: 创建的策略元数据
        """
        if signal_weights is None:
            signal_weights = [1.0 / len(signal_ids)] * len(signal_ids)
        
        signal_config = SignalConfig(
            signal_ids=signal_ids,
            weights=signal_weights,
            combination_method=combination_method
        )
        
        risk_params = risk_params or RiskParams()
        
        return self._registry.register(
            name=name,
            description=description,
            strategy_type=strategy_type,
            signals=signal_config,
            rebalance_freq=rebalance_freq,
            max_positions=max_positions,
            risk_params=risk_params,
            tags=tags or []
        )
    
    def validate_signal_config(self, signal_config: SignalConfig) -> Tuple[bool, List[str]]:
        """
        验证信号配置
        
        Args:
            signal_config: 信号配置
            
        Returns:
            Tuple[bool, List[str]]: 是否有效，错误信息列表
        """
        errors = []
        
        if not signal_config.signal_ids:
            errors.append("信号列表不能为空")
        
        if len(signal_config.signal_ids) != len(signal_config.weights):
            errors.append("信号数量与权重数量不匹配")
        
        if signal_config.weights:
            total_weight = sum(signal_config.weights)
            if abs(total_weight - 1.0) > 0.001:
                errors.append(f"权重总和应为1，当前为{total_weight:.4f}")
            
            if any(w < 0 for w in signal_config.weights):
                errors.append("权重不能为负数")
        
        for signal_id in signal_config.signal_ids:
            signal = self._signal_registry.get(signal_id)
            if signal is None:
                errors.append(f"信号不存在: {signal_id}")
        
        return len(errors) == 0, errors
    
    def validate_risk_params(self, risk_params: RiskParams) -> Tuple[bool, List[str]]:
        """
        验证风控参数
        
        Args:
            risk_params: 风控参数
            
        Returns:
            Tuple[bool, List[str]]: 是否有效，错误信息列表
        """
        errors = []
        
        if risk_params.max_single_weight <= 0 or risk_params.max_single_weight > 1:
            errors.append("单票权重上限应在0-1之间")
        
        if risk_params.max_industry_weight <= 0 or risk_params.max_industry_weight > 1:
            errors.append("行业权重上限应在0-1之间")
        
        if risk_params.max_single_weight > risk_params.max_industry_weight:
            errors.append("单票权重上限不应超过行业权重上限")
        
        if risk_params.stop_loss >= 0:
            errors.append("止损线应为负数")
        
        if risk_params.take_profit <= 0:
            errors.append("止盈线应为正数")
        
        if risk_params.max_drawdown >= 0:
            errors.append("最大回撤应为负数")
        
        return len(errors) == 0, errors
    
    def get_available_signals(self) -> List[Dict[str, Any]]:
        """获取可用信号列表"""
        signals = self._signal_registry.list_all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "type": s.signal_type.value,
                "direction": s.direction.value
            }
            for s in signals
        ]
    
    def calculate_signal_correlation(
        self,
        signal_ids: List[str]
    ) -> Dict[str, float]:
        """
        计算信号相关性
        
        Args:
            signal_ids: 信号ID列表
            
        Returns:
            Dict[str, float]: 相关性矩阵
        """
        return {f"{s1}_{s2}": 0.5 for s1 in signal_ids for s2 in signal_ids if s1 != s2}
    
    def suggest_weights(
        self,
        signal_ids: List[str],
        method: str = "equal"
    ) -> List[float]:
        """
        建议权重分配
        
        Args:
            signal_ids: 信号ID列表
            method: 分配方法 ('equal', 'performance', 'risk_parity')
            
        Returns:
            List[float]: 权重列表
        """
        n = len(signal_ids)
        
        if method == "equal":
            return [1.0 / n] * n
        
        elif method == "performance":
            scores = []
            for signal_id in signal_ids:
                signal = self._signal_registry.get(signal_id)
                if signal:
                    scores.append(signal.score + 1)
                else:
                    scores.append(1)
            
            total = sum(scores)
            return [s / total for s in scores]
        
        elif method == "risk_parity":
            return [1.0 / n] * n
        
        return [1.0 / n] * n
    
    def clone_strategy(
        self,
        strategy_id: str,
        new_name: str
    ) -> StrategyMetadata:
        """
        克隆策略
        
        Args:
            strategy_id: 原策略ID
            new_name: 新策略名称
            
        Returns:
            StrategyMetadata: 克隆的策略元数据
        """
        original = self._registry.get(strategy_id)
        if original is None:
            raise StrategyException(f"策略不存在: {strategy_id}")
        
        return self._registry.register(
            name=new_name,
            description=original.description + " (克隆)",
            strategy_type=original.strategy_type,
            signals=SignalConfig(
                signal_ids=original.signals.signal_ids.copy(),
                weights=original.signals.weights.copy(),
                combination_method=original.signals.combination_method
            ),
            rebalance_freq=original.rebalance_freq,
            max_positions=original.max_positions,
            risk_params=RiskParams(**original.risk_params.to_dict()),
            tags=original.tags.copy() + ["克隆"]
        )


from typing import Tuple


_default_designer: Optional[StrategyDesigner] = None


def get_strategy_designer() -> StrategyDesigner:
    """获取全局策略设计器实例"""
    global _default_designer
    if _default_designer is None:
        _default_designer = StrategyDesigner()
    return _default_designer


def reset_strategy_designer():
    """重置全局策略设计器"""
    global _default_designer
    _default_designer = None
