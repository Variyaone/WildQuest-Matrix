"""
AI信号到交易决策的完整链路

整合AI信号到交易流程：
1. AI信号注册到信号库
2. 信号自动触发交易决策
3. RL策略优化仓位
4. RL执行器优化订单执行
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import pandas as pd
import numpy as np

from ..signal import (
    SignalRegistry,
    SignalMetadata,
    SignalStatus,
    SignalType,
    SignalDirection,
    get_signal_registry
)
from ..strategy import (
    StrategyRegistry,
    StrategyMetadata,
    get_strategy_registry
)
from ..trading import (
    OrderManager,
    TradeOrder,
    OrderSide,
    OrderType
)
from ..portfolio import (
    PositionSizer,
    SizingMethod,
    get_position_sizer
)
from ..infrastructure.logging import get_logger
from ..infrastructure.config import get_data_paths

logger = get_logger("trading.ai_pipeline")


@dataclass
class AITradingConfig:
    """AI交易配置"""
    enable_ai_signal: bool = True
    enable_rl_strategy: bool = True
    enable_rl_execution: bool = True
    
    signal_confidence_threshold: float = 0.6
    max_position_weight: float = 0.15
    min_position_value: float = 5000.0
    reserve_cash_ratio: float = 0.02
    
    rl_execution_method: str = "rl"
    max_execution_time: int = 30
    
    auto_register_signals: bool = True
    signal_validity_days: int = 1


@dataclass
class AITradingResult:
    """AI交易结果"""
    success: bool
    date: str
    
    signal_count: int = 0
    order_count: int = 0
    
    signals: List[Dict] = field(default_factory=list)
    target_portfolio: Dict[str, float] = field(default_factory=dict)
    orders: List[TradeOrder] = field(default_factory=list)
    
    signal_confidence: float = 0.0
    execution_method: str = "standard"
    
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class AISignalRegistrar:
    """
    AI信号注册器
    
    将AI生成的信号注册到信号库，使其可被策略使用
    """
    
    def __init__(self, signal_registry: SignalRegistry = None):
        self.registry = signal_registry or get_signal_registry()
        self.logger = get_logger("signal.registrar")
    
    def register_ai_signal(
        self,
        signal_id: str,
        name: str,
        description: str,
        model_type: str,
        factor_dependencies: List[str] = None,
        performance_metrics: Dict[str, float] = None,
        tags: List[str] = None
    ) -> bool:
        """
        注册AI信号到信号库
        
        Args:
            signal_id: 信号ID
            name: 信号名称
            description: 描述
            model_type: 模型类型 (lstm/transformer/xgboost等)
            factor_dependencies: 依赖因子
            performance_metrics: 性能指标
            tags: 标签
            
        Returns:
            是否注册成功
        """
        try:
            metadata = SignalMetadata(
                signal_id=signal_id,
                name=name,
                signal_type=SignalType.STOCK_SELECTION,
                direction=SignalDirection.LONG,
                status=SignalStatus.ACTIVE,
                description=description,
                factors=factor_dependencies or [],
                rules={
                    "model_type": model_type,
                    "is_ai_signal": True,
                    "performance": performance_metrics or {}
                },
                tags=tags or ["ai", model_type, "auto_registered"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.registry.register(metadata)
            
            self.logger.info(f"AI信号注册成功: {signal_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"AI信号注册失败: {e}")
            return False
    
    def register_batch(
        self,
        signals: List[Dict[str, Any]]
    ) -> Tuple[int, int]:
        """
        批量注册AI信号
        
        Args:
            signals: 信号列表
            
        Returns:
            (成功数, 失败数)
        """
        success_count = 0
        fail_count = 0
        
        for sig in signals:
            if self.register_ai_signal(**sig):
                success_count += 1
            else:
                fail_count += 1
        
        return success_count, fail_count
    
    def auto_register_from_training(
        self,
        model_type: str,
        training_result: Dict[str, Any],
        factor_list: List[str] = None
    ) -> Optional[str]:
        """
        从训练结果自动注册信号
        
        Args:
            model_type: 模型类型
            training_result: 训练结果
            factor_list: 因子列表
            
        Returns:
            注册的信号ID
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        signal_id = f"ai_{model_type}_{timestamp}"
        
        performance = {
            "train_loss": training_result.get("train_loss", 0),
            "val_loss": training_result.get("val_loss", 0),
            "accuracy": training_result.get("accuracy", 0),
            "ic": training_result.get("ic", 0)
        }
        
        if self.register_ai_signal(
            signal_id=signal_id,
            name=f"AI信号-{model_type.upper()}-{timestamp}",
            description=f"自动注册的{model_type}模型信号",
            model_type=model_type,
            factor_dependencies=factor_list,
            performance_metrics=performance
        ):
            return signal_id
        
        return None


class AITradingPipeline:
    """
    AI交易管线
    
    完整的AI增强交易流程:
    1. 生成AI增强信号
    2. 注册信号到信号库
    3. RL策略生成目标持仓
    4. 仓位计算
    5. RL执行器优化订单
    """
    
    def __init__(self, config: AITradingConfig = None):
        self.config = config or AITradingConfig()
        
        self._signal_registry = get_signal_registry()
        self._strategy_registry = get_strategy_registry()
        self._order_manager = OrderManager()
        self._position_sizer = get_position_sizer()
        self._signal_registrar = AISignalRegistrar(self._signal_registry)
        
        self._ai_signal_generator = None
        self._rl_strategy = None
        self._rl_executor = None
        
        self._init_components()
    
    def _init_components(self):
        """初始化组件"""
        try:
            from ..signal import get_enhanced_signal_generator
            self._ai_signal_generator = get_enhanced_signal_generator()
        except Exception as e:
            logger.warning(f"AI信号生成器初始化失败: {e}")
        
        if self.config.enable_rl_strategy:
            try:
                from ..strategy import create_rl_strategy
                self._rl_strategy = create_rl_strategy()
            except Exception as e:
                logger.warning(f"RL策略初始化失败: {e}")
        
        if self.config.enable_rl_execution:
            try:
                from ..trading import create_rl_executor
                self._rl_executor = create_rl_executor(
                    max_execution_time=self.config.max_execution_time
                )
            except Exception as e:
                logger.warning(f"RL执行器初始化失败: {e}")
    
    def generate_signals(
        self,
        factor_values: pd.DataFrame,
        market_data: pd.DataFrame = None,
        date: str = None,
        register: bool = True
    ) -> Tuple[List[Dict], float]:
        """
        生成AI增强信号
        
        Args:
            factor_values: 因子值
            market_data: 市场数据
            date: 日期
            register: 是否注册到信号库
            
        Returns:
            (信号列表, 置信度)
        """
        date = date or datetime.now().strftime("%Y-%m-%d")
        
        if self._ai_signal_generator is None:
            logger.warning("AI信号生成器未初始化，使用传统信号")
            from ..signal import get_signal_generator
            generator = get_signal_generator()
            result = generator.generate(factor_values, date=date)
            
            signals = []
            for s in result.signals:
                signals.append({
                    "stock_code": s.stock_code,
                    "strength": s.strength,
                    "direction": s.direction,
                    "confidence": 0.5,
                    "source": "traditional"
                })
            
            return signals, 0.5
        
        result = self._ai_signal_generator.generate(
            factor_values=factor_values,
            market_data=market_data,
            date=date,
            use_ensemble=True
        )
        
        signals = []
        confidence = 0.5
        
        if result.success:
            confidence = result.details.get("confidence", 0.5)
            
            for s in result.signals:
                signals.append({
                    "stock_code": s.stock_code,
                    "strength": s.strength,
                    "direction": s.direction,
                    "confidence": s.confidence if hasattr(s, 'confidence') else confidence,
                    "source": s.source if hasattr(s, 'source') else "ai"
                })
            
            if register and self.config.auto_register_signals:
                self._register_daily_signals(signals, date)
        
        return signals, confidence
    
    def _register_daily_signals(
        self,
        signals: List[Dict],
        date: str
    ):
        """注册每日信号到信号库"""
        signal_id = f"daily_ai_{date.replace('-', '')}"
        
        self._signal_registrar.register_ai_signal(
            signal_id=signal_id,
            name=f"AI信号-{date}",
            description=f"AI增强信号 {date}",
            model_type="ensemble",
            tags=["daily", "ai", "ensemble", date]
        )
    
    def generate_portfolio(
        self,
        signals: List[Dict],
        current_portfolio: Dict[str, float],
        market_data: pd.DataFrame = None,
        total_capital: float = 1000000.0
    ) -> Dict[str, float]:
        """
        生成目标持仓
        
        Args:
            signals: 信号列表
            current_portfolio: 当前持仓
            market_data: 市场数据
            total_capital: 总资金
            
        Returns:
            目标持仓 {股票代码: 权重}
        """
        signal_dict = {s["stock_code"]: s["strength"] for s in signals}
        
        if self._rl_strategy is not None and self.config.enable_rl_strategy:
            try:
                result = self._rl_strategy.execute(
                    signals=signal_dict,
                    current_portfolio=current_portfolio,
                    market_data=market_data
                )
                
                if result.success:
                    return result.target_portfolio
            except Exception as e:
                logger.warning(f"RL策略执行失败: {e}")
        
        sorted_signals = sorted(signals, key=lambda x: x["strength"], reverse=True)
        top_signals = sorted_signals[:int(1 / self.config.max_position_weight)]
        
        portfolio = {}
        for s in top_signals:
            weight = min(self.config.max_position_weight, abs(s["strength"]) * 0.3)
            portfolio[s["stock_code"]] = weight
        
        total_weight = sum(portfolio.values())
        if total_weight > (1 - self.config.reserve_cash_ratio):
            scale = (1 - self.config.reserve_cash_ratio) / total_weight
            portfolio = {k: v * scale for k, v in portfolio.items()}
        
        return portfolio
    
    def generate_orders(
        self,
        target_portfolio: Dict[str, float],
        current_positions: Dict[str, Dict],
        prices: Dict[str, float],
        total_capital: float,
        method: str = None
    ) -> List[TradeOrder]:
        """
        生成交易订单
        
        Args:
            target_portfolio: 目标持仓
            current_positions: 当前持仓
            prices: 价格
            total_capital: 总资金
            method: 执行方法 (rl/twap/vwap)
            
        Returns:
            订单列表
        """
        method = method or self.config.rl_execution_method
        
        target_positions = {}
        for stock, weight in target_portfolio.items():
            if stock in prices:
                shares = int(total_capital * weight / prices[stock] / 100) * 100
                target_positions[stock] = {
                    "shares": shares,
                    "weight": weight
                }
        
        orders = self._order_manager.create_orders_from_target_positions(
            target_positions=target_positions,
            current_positions=current_positions,
            prices=prices,
            available_cash=total_capital * (1 - self.config.reserve_cash_ratio)
        )
        
        return orders
    
    def execute_orders(
        self,
        orders: List[TradeOrder],
        market_data: pd.DataFrame,
        method: str = None
    ) -> List[TradeOrder]:
        """
        执行订单（使用RL执行器优化）
        
        Args:
            orders: 订单列表
            market_data: 市场数据
            method: 执行方法
            
        Returns:
            拆分后的子订单列表
        """
        if self._rl_executor is None or not self.config.enable_rl_execution:
            return orders
        
        method = method or self.config.rl_execution_method
        
        all_sub_orders = []
        
        for order in orders:
            result = self._rl_executor.split_order(
                order=order,
                market_data=market_data,
                method=method
            )
            
            if result.success:
                all_sub_orders.extend(result.sub_orders)
            else:
                all_sub_orders.append(order)
        
        return all_sub_orders
    
    def run(
        self,
        factor_values: pd.DataFrame,
        market_data: pd.DataFrame = None,
        current_positions: Dict[str, Dict] = None,
        prices: Dict[str, float] = None,
        total_capital: float = 1000000.0,
        date: str = None
    ) -> AITradingResult:
        """
        执行完整AI交易流程
        
        Args:
            factor_values: 因子值
            market_data: 市场数据
            current_positions: 当前持仓
            prices: 价格
            total_capital: 总资金
            date: 日期
            
        Returns:
            AITradingResult
        """
        date = date or datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"开始AI交易流程: {date}")
        
        signals, confidence = self.generate_signals(
            factor_values, market_data, date
        )
        
        if not signals:
            return AITradingResult(
                success=False,
                date=date,
                error_message="未生成有效信号"
            )
        
        if confidence < self.config.signal_confidence_threshold:
            logger.warning(f"信号置信度 {confidence:.2f} 低于阈值 {self.config.signal_confidence_threshold}")
        
        current_portfolio = {}
        if current_positions:
            total_value = sum(
                p.get("shares", 0) * prices.get(stock, 0)
                for stock, p in current_positions.items()
            )
            if total_value > 0:
                current_portfolio = {
                    stock: p.get("shares", 0) * prices.get(stock, 0) / total_value
                    for stock, p in current_positions.items()
                }
        
        target_portfolio = self.generate_portfolio(
            signals, current_portfolio, market_data, total_capital
        )
        
        if not target_portfolio:
            return AITradingResult(
                success=False,
                date=date,
                signal_count=len(signals),
                signal_confidence=confidence,
                error_message="未生成目标持仓"
            )
        
        orders = self.generate_orders(
            target_portfolio, current_positions or {}, prices or {}, total_capital
        )
        
        if market_data is not None and self.config.enable_rl_execution:
            orders = self.execute_orders(orders, market_data)
        
        logger.info(f"AI交易流程完成: 信号={len(signals)}, 订单={len(orders)}")
        
        return AITradingResult(
            success=True,
            date=date,
            signal_count=len(signals),
            order_count=len(orders),
            signals=signals,
            target_portfolio=target_portfolio,
            orders=orders,
            signal_confidence=confidence,
            execution_method=self.config.rl_execution_method,
            details={
                "ai_signal_enabled": self.config.enable_ai_signal,
                "rl_strategy_enabled": self.config.enable_rl_strategy,
                "rl_execution_enabled": self.config.enable_rl_execution
            }
        )


def create_ai_trading_pipeline(
    config: AITradingConfig = None
) -> AITradingPipeline:
    """创建AI交易管线"""
    return AITradingPipeline(config)


_ai_pipeline = None


def get_ai_trading_pipeline(
    config: AITradingConfig = None
) -> AITradingPipeline:
    """获取AI交易管线单例"""
    global _ai_pipeline
    if _ai_pipeline is None:
        _ai_pipeline = AITradingPipeline(config)
    return _ai_pipeline
