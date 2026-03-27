"""
数据新鲜度策略模块

检查各层数据是否过期，借鉴6.0版本main.py的实现。
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import pandas as pd


class FreshnessStatus(Enum):
    """数据新鲜度状态"""
    FRESH = "fresh"          # 新鲜 - 数据在有效期内
    WARNING = "warning"      # 警告 - 数据接近过期
    STALE = "stale"          # 过期 - 数据已过期


class ExecutionMode(Enum):
    """执行场景"""
    LIVE_TRADING = "live_trading"    # 实盘交易 - 严格要求
    BACKTEST = "backtest"            # 回测验证 - 宽松要求
    DEVELOPMENT = "development"      # 开发调试 - 中等要求
    MONITORING = "monitoring"        # 监控报告 - 中等要求
    RESEARCH = "research"            # 研究分析 - 宽松要求


@dataclass
class FreshnessConfig:
    """新鲜度配置"""
    max_delay_days: int      # 最大延迟天数
    warning_days: int        # 警告天数
    
    
@dataclass
class FreshnessResult:
    """新鲜度检查结果"""
    layer: str                       # 层名称
    data_type: str                   # 数据类型
    status: FreshnessStatus          # 新鲜度状态
    data_age: float                  # 数据年龄（小时或天）
    max_allowed_age: float           # 最大允许年龄
    last_update: Optional[datetime]  # 最后更新时间
    message: str                     # 检查消息
    
    @property
    def is_fresh(self) -> bool:
        """是否新鲜"""
        return self.status == FreshnessStatus.FRESH


class FreshnessPolicy:
    """
    数据新鲜度策略管理器
    
    检查各层数据是否过期，根据执行场景应用不同的标准。
    """
    
    # 默认配置（实盘模式）
    DEFAULT_CONFIGS: Dict[str, Dict[str, FreshnessConfig]] = {
        'data': {
            'market_data': FreshnessConfig(max_delay_days=0, warning_days=1),
            'financial_data': FreshnessConfig(max_delay_days=30, warning_days=7),
            'stock_list': FreshnessConfig(max_delay_days=1, warning_days=3),
        },
        'factor': {
            'daily_factors': FreshnessConfig(max_delay_days=0, warning_days=1),
            'weekly_factors': FreshnessConfig(max_delay_days=1, warning_days=2),
            'monthly_factors': FreshnessConfig(max_delay_days=5, warning_days=10),
        },
        'strategy': {
            'stock_selection': FreshnessConfig(max_delay_days=0, warning_days=1),
            'weights': FreshnessConfig(max_delay_days=0, warning_days=1),
        },
        'portfolio': {
            'optimized_weights': FreshnessConfig(max_delay_days=0, warning_days=1),
            'rebalance_signal': FreshnessConfig(max_delay_days=0, warning_days=1),
        },
        'risk': {
            'risk_check': FreshnessConfig(max_delay_days=0, warning_days=1),
        },
        'trading': {
            'trading_execution': FreshnessConfig(max_delay_days=0, warning_days=0),
        },
        'monitor': {
            'monitoring_data': FreshnessConfig(max_delay_days=0, warning_days=1),
        },
    }
    
    # 回测模式配置（更宽松）
    BACKTEST_CONFIGS: Dict[str, Dict[str, FreshnessConfig]] = {
        'data': {
            'market_data': FreshnessConfig(max_delay_days=365, warning_days=365),
            'financial_data': FreshnessConfig(max_delay_days=365, warning_days=365),
            'stock_list': FreshnessConfig(max_delay_days=365, warning_days=365),
        },
        'factor': {
            'daily_factors': FreshnessConfig(max_delay_days=365, warning_days=365),
            'weekly_factors': FreshnessConfig(max_delay_days=365, warning_days=365),
            'monthly_factors': FreshnessConfig(max_delay_days=365, warning_days=365),
        },
        'strategy': {
            'stock_selection': FreshnessConfig(max_delay_days=365, warning_days=365),
            'weights': FreshnessConfig(max_delay_days=365, warning_days=365),
        },
        'portfolio': {
            'optimized_weights': FreshnessConfig(max_delay_days=365, warning_days=365),
            'rebalance_signal': FreshnessConfig(max_delay_days=365, warning_days=365),
        },
        'risk': {
            'risk_check': FreshnessConfig(max_delay_days=365, warning_days=365),
        },
        'trading': {
            'trading_execution': FreshnessConfig(max_delay_days=365, warning_days=365),
        },
        'monitor': {
            'monitoring_data': FreshnessConfig(max_delay_days=365, warning_days=365),
        },
    }
    
    def __init__(self, mode: ExecutionMode = ExecutionMode.LIVE_TRADING):
        """
        初始化新鲜度策略
        
        Args:
            mode: 执行场景模式
        """
        self.mode = mode
        self.configs = self._get_configs_for_mode(mode)
    
    def _get_configs_for_mode(self, mode: ExecutionMode) -> Dict[str, Dict[str, FreshnessConfig]]:
        """根据模式获取配置"""
        if mode == ExecutionMode.BACKTEST or mode == ExecutionMode.RESEARCH:
            return self.BACKTEST_CONFIGS
        elif mode == ExecutionMode.DEVELOPMENT or mode == ExecutionMode.MONITORING:
            # 开发/监控模式：中等要求
            configs = {}
            for layer, types in self.DEFAULT_CONFIGS.items():
                configs[layer] = {}
                for data_type, config in types.items():
                    # 放宽要求
                    configs[layer][data_type] = FreshnessConfig(
                        max_delay_days=config.max_delay_days + 1,
                        warning_days=config.warning_days + 1
                    )
            return configs
        else:
            # 实盘模式：严格要求
            return self.DEFAULT_CONFIGS
    
    def check_freshness(
        self,
        layer: str,
        data_type: str,
        last_update: Optional[datetime],
        current_time: Optional[datetime] = None
    ) -> FreshnessResult:
        """
        检查数据新鲜度
        
        Args:
            layer: 层名称 (data/factor/strategy/portfolio/risk/trading/monitor)
            data_type: 数据类型
            last_update: 最后更新时间
            current_time: 当前时间（默认为现在）
            
        Returns:
            FreshnessResult: 新鲜度检查结果
        """
        if current_time is None:
            current_time = datetime.now()
        
        # 获取配置
        config = self.configs.get(layer, {}).get(data_type)
        if config is None:
            return FreshnessResult(
                layer=layer,
                data_type=data_type,
                status=FreshnessStatus.FRESH,
                data_age=0,
                max_allowed_age=0,
                last_update=last_update,
                message=f"未找到 {layer}.{data_type} 的新鲜度配置，默认通过"
            )
        
        # 如果没有最后更新时间，视为过期
        if last_update is None:
            return FreshnessResult(
                layer=layer,
                data_type=data_type,
                status=FreshnessStatus.STALE,
                data_age=float('inf'),
                max_allowed_age=config.max_delay_days,
                last_update=None,
                message=f"{layer}.{data_type} 无最后更新时间记录"
            )
        
        # 计算数据年龄（交易日）
        data_age = self._calculate_trading_days(last_update, current_time)
        
        # 判断新鲜度状态
        if data_age > config.max_delay_days:
            status = FreshnessStatus.STALE
            message = f"{layer}.{data_type} 已过期: {data_age}天 > {config.max_delay_days}天"
        elif data_age > config.warning_days:
            status = FreshnessStatus.WARNING
            message = f"{layer}.{data_type} 接近过期: {data_age}天 > {config.warning_days}天"
        else:
            status = FreshnessStatus.FRESH
            message = f"{layer}.{data_type} 新鲜: {data_age}天"
        
        return FreshnessResult(
            layer=layer,
            data_type=data_type,
            status=status,
            data_age=data_age,
            max_allowed_age=config.max_delay_days,
            last_update=last_update,
            message=message
        )
    
    def _calculate_trading_days(self, start: datetime, end: datetime) -> int:
        """
        计算交易日数量
        
        简化实现：假设每年250个交易日，周末和节假日不交易
        """
        # 计算自然日差
        days = (end - start).days
        
        # 简单估算：去除周末（约2/7）
        trading_days = int(days * 5 / 7)
        
        return max(0, trading_days)
    
    def check_all_layers(
        self,
        update_times: Dict[str, Dict[str, Optional[datetime]]],
        current_time: Optional[datetime] = None
    ) -> Dict[str, Dict[str, FreshnessResult]]:
        """
        检查所有层的新鲜度
        
        Args:
            update_times: 各层各数据类型的最后更新时间
                格式: {layer: {data_type: last_update}}
            current_time: 当前时间
            
        Returns:
            Dict: 各层各数据类型的检查结果
        """
        results = {}
        
        for layer, types in update_times.items():
            results[layer] = {}
            for data_type, last_update in types.items():
                results[layer][data_type] = self.check_freshness(
                    layer, data_type, last_update, current_time
                )
        
        return results
    
    def get_expired_data(
        self,
        results: Dict[str, Dict[str, FreshnessResult]]
    ) -> list:
        """
        获取已过期的数据列表
        
        Args:
            results: 检查结果
            
        Returns:
            list: 过期数据列表 [(layer, data_type), ...]
        """
        expired = []
        for layer, types in results.items():
            for data_type, result in types.items():
                if result.status == FreshnessStatus.STALE:
                    expired.append((layer, data_type))
        return expired
    
    def get_warning_data(
        self,
        results: Dict[str, Dict[str, FreshnessResult]]
    ) -> list:
        """
        获取警告状态的数据列表
        
        Args:
            results: 检查结果
            
        Returns:
            list: 警告数据列表 [(layer, data_type), ...]
        """
        warnings = []
        for layer, types in results.items():
            for data_type, result in types.items():
                if result.status == FreshnessStatus.WARNING:
                    warnings.append((layer, data_type))
        return warnings


# 全局新鲜度策略实例
_default_policy: Optional[FreshnessPolicy] = None


def get_freshness_policy(mode: Optional[ExecutionMode] = None) -> FreshnessPolicy:
    """
    获取新鲜度策略实例
    
    Args:
        mode: 执行场景模式（None则使用默认实例）
        
    Returns:
        FreshnessPolicy: 新鲜度策略实例
    """
    global _default_policy
    
    if mode is None:
        if _default_policy is None:
            _default_policy = FreshnessPolicy()
        return _default_policy
    
    return FreshnessPolicy(mode)


def set_execution_mode(mode: ExecutionMode):
    """
    设置执行场景模式
    
    Args:
        mode: 执行场景模式
    """
    global _default_policy
    _default_policy = FreshnessPolicy(mode)
