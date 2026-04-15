"""
策略执行流程模块

完整的策略执行链路:
  因子 → 信号 → 选股 → 权重优化 → 仓位计算 → 订单生成

使用示例:
    from core.strategy.execution import StrategyExecutor
    
    executor = StrategyExecutor()
    result = executor.execute(
        strategy_id="STR001",
        date="2026-03-29",
        total_capital=1000000
    )
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

import pandas as pd
import numpy as np

from .registry import StrategyMetadata, get_strategy_registry
from .selector import StockSelector, SelectionResult, get_stock_selector
from ..factor import get_factor_storage, get_factor_engine


class SignalGenerator:
    """简单的信号生成器"""
    
    def generate_batch(
        self,
        signal_ids: List[str],
        factor_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """批量生成信号"""
        signals = {}
        for signal_id in signal_ids:
            signals[signal_id] = {"score": 0.5, "confidence": 0.8}
        return signals


def get_signal_generator() -> SignalGenerator:
    """获取信号生成器实例"""
    return SignalGenerator()
from ..portfolio import (
    PortfolioOptimizer,
    PositionSizer,
    SizingMethod,
    SizingResult,
    get_position_sizer
)
from ..trading import OrderManager, TradeOrder
from ..infrastructure.exceptions import StrategyException

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """执行状态"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    NO_SIGNALS = "no_signals"
    NO_SELECTIONS = "no_selections"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class ExecutionResult:
    """执行结果"""
    status: ExecutionStatus
    strategy_id: str
    date: str
    
    signal_count: int = 0
    selection_count: int = 0
    order_count: int = 0
    
    signals: List[Any] = field(default_factory=list)
    selections: List[Any] = field(default_factory=list)
    weights: Dict[str, float] = field(default_factory=dict)
    positions: List[Any] = field(default_factory=list)
    orders: List[TradeOrder] = field(default_factory=list)
    
    total_capital: float = 0.0
    allocated_capital: float = 0.0
    
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'strategy_id': self.strategy_id,
            'date': self.date,
            'signal_count': self.signal_count,
            'selection_count': self.selection_count,
            'order_count': self.order_count,
            'weights': self.weights,
            'total_capital': self.total_capital,
            'allocated_capital': self.allocated_capital,
            'message': self.message,
            'details': self.details
        }


@dataclass
class ExecutionConfig:
    """执行配置"""
    optimization_method: str = "equal_weight"
    sizing_method: SizingMethod = SizingMethod.EQUAL
    max_single_weight: float = 0.15
    min_position_value: float = 5000.0
    reserve_cash_ratio: float = 0.02
    allow_fallback: bool = True


class StrategyExecutor:
    """
    策略执行器
    
    完整的策略执行流程:
    1. 加载策略配置
    2. 获取因子数据
    3. 生成信号
    4. 选股
    5. 权重优化
    6. 仓位计算
    7. 生成订单
    """
    
    def __init__(self, config: ExecutionConfig = None):
        self.config = config or ExecutionConfig()
        
        self._registry = get_strategy_registry()
        self._signal_generator = get_signal_generator()
        self._stock_selector = get_stock_selector()
        self._factor_storage = get_factor_storage()
        self._optimizer = PortfolioOptimizer({
            "method": self.config.optimization_method,
            "max_single_weight": self.config.max_single_weight,
            "allow_fallback": self.config.allow_fallback
        })
        self._sizer = get_position_sizer()
        self._order_manager = OrderManager()
    
    def execute(
        self,
        strategy_id: str,
        date: str,
        total_capital: float,
        factor_data: Dict[str, pd.DataFrame] = None,
        prices: Dict[str, float] = None,
        current_positions: Dict[str, Dict] = None,
        stock_names: Dict[str, str] = None,
        cov_matrix: np.ndarray = None,
        expected_returns: Dict[str, float] = None
    ) -> ExecutionResult:
        """
        执行策略
        
        Args:
            strategy_id: 策略ID
            date: 执行日期
            total_capital: 总资金
            factor_data: 因子数据（可选，不提供则自动加载）
            prices: 股票价格字典
            current_positions: 当前持仓
            stock_names: 股票名称字典
            cov_matrix: 协方差矩阵（用于权重优化）
            expected_returns: 预期收益率（用于权重优化）
            
        Returns:
            ExecutionResult: 执行结果
        """
        logger.info(f"开始执行策略: {strategy_id}, 日期: {date}, 资金: {total_capital}")
        
        strategy = self._registry.get(strategy_id)
        if strategy is None:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                strategy_id=strategy_id,
                date=date,
                message=f"策略不存在: {strategy_id}"
            )
        
        if factor_data is None:
            factor_data = self._load_factor_data(strategy, date)
            if not factor_data:
                return ExecutionResult(
                    status=ExecutionStatus.INSUFFICIENT_DATA,
                    strategy_id=strategy_id,
                    date=date,
                    message="无法加载因子数据"
                )
        
        signal_results = self._generate_signals(strategy, factor_data)
        all_signals = []
        for signal_id, result in signal_results.items():
            if result.success:
                date_signals = [s for s in result.signals if s.date == date]
                all_signals.extend(date_signals)
        
        if not all_signals:
            return ExecutionResult(
                status=ExecutionStatus.NO_SIGNALS,
                strategy_id=strategy_id,
                date=date,
                message="未生成任何有效信号"
            )
        
        selection_result = self._stock_selector.select(
            strategy=strategy,
            date=date,
            factor_data=factor_data
        )
        
        if not selection_result.success or not selection_result.selections:
            return ExecutionResult(
                status=ExecutionStatus.NO_SELECTIONS,
                strategy_id=strategy_id,
                date=date,
                signal_count=len(all_signals),
                message="未选出任何股票"
            )
        
        stock_scores = {
            s.stock_code: s.score 
            for s in selection_result.selections
        }
        
        optimization_result = self._optimizer.optimize(
            stock_scores=stock_scores,
            expected_returns=expected_returns,
            cov_matrix=cov_matrix
        )
        
        if not optimization_result.is_success():
            logger.warning(f"权重优化失败: {optimization_result.message}")
        
        weights = optimization_result.weights
        
        if prices is None:
            prices = self._get_prices(list(weights.keys()), date)
        
        if not prices:
            return ExecutionResult(
                status=ExecutionStatus.INSUFFICIENT_DATA,
                strategy_id=strategy_id,
                date=date,
                signal_count=len(all_signals),
                selection_count=len(selection_result.selections),
                message="无法获取股票价格"
            )
        
        sizing_result = self._sizer.size(
            stock_selections=[s.to_dict() for s in selection_result.selections],
            total_capital=total_capital,
            prices=prices,
            weights=weights,
            method=self.config.sizing_method,
            stock_names=stock_names
        )
        
        target_positions = sizing_result.get_target_positions()
        
        orders = self._order_manager.create_orders_from_target_positions(
            target_positions=target_positions,
            current_positions=current_positions or {},
            prices=prices,
            available_cash=total_capital
        )
        
        status = ExecutionStatus.SUCCESS
        if sizing_result.status.value != "success":
            status = ExecutionStatus.PARTIAL
        
        result = ExecutionResult(
            status=status,
            strategy_id=strategy_id,
            date=date,
            signal_count=len(all_signals),
            selection_count=len(selection_result.selections),
            order_count=len(orders),
            signals=all_signals,
            selections=selection_result.selections,
            weights=weights,
            positions=sizing_result.positions,
            orders=orders,
            total_capital=total_capital,
            allocated_capital=sizing_result.allocated_capital,
            message=f"成功执行策略，生成 {len(orders)} 个订单",
            details={
                'optimization_method': optimization_result.method,
                'sizing_method': sizing_result.method.value,
                'allocation_rate': sizing_result.allocation_rate
            }
        )
        
        logger.info(f"策略执行完成: {strategy_id}, 信号: {result.signal_count}, 选股: {result.selection_count}, 订单: {result.order_count}")
        
        return result
    
    def _load_factor_data(
        self,
        strategy: StrategyMetadata,
        date: str
    ) -> Dict[str, pd.DataFrame]:
        """加载因子数据"""
        factor_data = {}
        
        signal_ids = strategy.signals.signal_ids
        
        for signal_id in signal_ids:
            signal_meta = self._registry._signal_registry.get(signal_id)
            if signal_meta is None:
                continue
            
            for factor_id in signal_meta.rules.factors:
                if factor_id not in factor_data:
                    df = self._factor_storage.load_factor(factor_id, date)
                    if df is not None and not df.empty:
                        factor_data[factor_id] = df
        
        return factor_data
    
    def _generate_signals(
        self,
        strategy: StrategyMetadata,
        factor_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """生成信号"""
        return self._signal_generator.generate_batch(
            signal_ids=strategy.signals.signal_ids,
            factor_data=factor_data
        )
    
    def _get_prices(
        self,
        stock_codes: List[str],
        date: str
    ) -> Dict[str, float]:
        """获取股票价格"""
        prices = {}
        
        try:
            from core.data import get_unified_updater
            updater = get_unified_updater()
            
            for code in stock_codes:
                try:
                    df = updater.fetcher.fetch_daily(code, date, date)
                    if df is not None and not df.empty:
                        prices[code] = df['close'].iloc[-1]
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"获取价格失败: {e}")
        
        return prices
    
    def execute_with_rebalance(
        self,
        strategy_id: str,
        date: str,
        total_capital: float,
        current_positions: Dict[str, Dict],
        factor_data: Dict[str, pd.DataFrame] = None,
        prices: Dict[str, float] = None,
        rebalance_threshold: float = 0.05
    ) -> ExecutionResult:
        """
        执行策略并计算再平衡
        
        Args:
            strategy_id: 策略ID
            date: 执行日期
            total_capital: 总资金
            current_positions: 当前持仓
            factor_data: 因子数据
            prices: 价格字典
            rebalance_threshold: 再平衡阈值
            
        Returns:
            ExecutionResult: 执行结果
        """
        result = self.execute(
            strategy_id=strategy_id,
            date=date,
            total_capital=total_capital,
            factor_data=factor_data,
            prices=prices,
            current_positions=current_positions
        )
        
        if result.status not in [ExecutionStatus.SUCCESS, ExecutionStatus.PARTIAL]:
            return result
        
        target_weights = result.weights
        buy, sell, hold = self._sizer.rebalance(
            target_weights=target_weights,
            current_positions=current_positions,
            total_capital=total_capital,
            prices=prices or {}
        )
        
        result.details['rebalance'] = {
            'buy_count': len(buy),
            'sell_count': len(sell),
            'hold_count': len(hold),
            'buy_stocks': list(buy.keys()),
            'sell_stocks': list(sell.keys())
        }
        
        return result
    
    def preview(
        self,
        strategy_id: str,
        date: str,
        total_capital: float,
        factor_data: Dict[str, pd.DataFrame] = None,
        prices: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """
        预览策略执行结果（不生成订单）
        
        Args:
            strategy_id: 策略ID
            date: 执行日期
            total_capital: 总资金
            factor_data: 因子数据
            prices: 价格字典
            
        Returns:
            Dict: 预览结果
        """
        result = self.execute(
            strategy_id=strategy_id,
            date=date,
            total_capital=total_capital,
            factor_data=factor_data,
            prices=prices
        )
        
        preview_result = {
            'status': result.status.value,
            'strategy_id': result.strategy_id,
            'date': result.date,
            'signal_count': result.signal_count,
            'selection_count': result.selection_count,
            'total_capital': result.total_capital,
            'allocated_capital': result.allocated_capital,
            'allocation_rate': result.details.get('allocation_rate', 0),
            'weights': result.weights,
            'positions': [p.to_dict() for p in result.positions],
            'message': result.message
        }
        
        return preview_result


_default_executor: Optional[StrategyExecutor] = None


def get_strategy_executor() -> StrategyExecutor:
    """获取全局策略执行器实例"""
    global _default_executor
    if _default_executor is None:
        _default_executor = StrategyExecutor()
    return _default_executor


def reset_strategy_executor():
    """重置全局策略执行器"""
    global _default_executor
    _default_executor = None


__all__ = [
    'ExecutionStatus',
    'ExecutionResult',
    'ExecutionConfig',
    'StrategyExecutor',
    'get_strategy_executor',
    'reset_strategy_executor',
]
