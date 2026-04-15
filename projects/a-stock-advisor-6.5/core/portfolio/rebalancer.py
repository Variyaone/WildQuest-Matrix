"""
组合再平衡策略模块

支持多种再平衡触发方式:
- 定期再平衡: 固定周期（周/月/季）
- 阈值触发再平衡: 偏离度超过阈值
- 成本优化再平衡: 考虑交易成本
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta

from core.infrastructure.exceptions import AppException, ErrorCode

logger = logging.getLogger(__name__)


class RebalanceTrigger(Enum):
    """再平衡触发类型"""
    PERIODIC = "periodic"
    THRESHOLD = "threshold"
    COST_OPTIMIZED = "cost_optimized"
    MANUAL = "manual"


class RebalanceStatus(Enum):
    """再平衡状态"""
    NEEDED = "needed"
    NOT_NEEDED = "not_needed"
    ERROR = "error"


@dataclass
class Trade:
    """交易指令"""
    stock_code: str
    action: str
    weight_diff: float
    current_weight: float
    target_weight: float
    shares: Optional[float] = None
    amount: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'stock_code': self.stock_code,
            'action': self.action,
            'weight_diff': self.weight_diff,
            'current_weight': self.current_weight,
            'target_weight': self.target_weight,
            'shares': self.shares,
            'amount': self.amount
        }


@dataclass
class RebalanceResult:
    """再平衡结果"""
    status: RebalanceStatus
    need_rebalance: bool = False
    trades: List[Trade] = field(default_factory=list)
    turnover: float = 0.0
    message: str = ""
    trigger_type: RebalanceTrigger = RebalanceTrigger.THRESHOLD
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'need_rebalance': self.need_rebalance,
            'trades': [t.to_dict() for t in self.trades],
            'turnover': self.turnover,
            'message': self.message,
            'trigger_type': self.trigger_type.value,
            'details': self.details
        }


class RebalanceError(AppException):
    """再平衡错误异常"""
    
    def __init__(self, message: str, details: Optional[Dict] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.TRADING_ERROR,
            details=details or {},
            cause=cause
        )


@dataclass
class RebalanceConfig:
    """再平衡配置"""
    trigger_type: RebalanceTrigger = RebalanceTrigger.THRESHOLD
    threshold: float = 0.05
    frequency: str = "weekly"
    min_trade_amount: float = 10000
    max_turnover: float = 0.20
    commission_rate: float = 0.0003
    stamp_duty: float = 0.001
    slippage: float = 0.001


class PortfolioRebalancer:
    """
    组合再平衡器
    
    功能:
    - 判断是否需要再平衡
    - 计算再平衡交易
    - 估算再平衡成本
    """
    
    def __init__(self, config: RebalanceConfig = None):
        self.config = config or RebalanceConfig()
    
    def should_rebalance(
        self,
        current_positions: dict,
        target_positions: dict,
        last_rebalance_date: datetime = None,
        current_date: datetime = None,
        threshold: float = None
    ) -> Tuple[bool, dict]:
        """
        判断是否需要再平衡
        
        Args:
            current_positions: 当前持仓 {stock_code: weight}
            target_positions: 目标持仓 {stock_code: weight}
            last_rebalance_date: 上次再平衡日期
            current_date: 当前日期
            threshold: 再平衡阈值
            
        Returns:
            (是否需要再平衡, 详细信息)
        """
        if threshold is None:
            threshold = self.config.threshold
        
        if current_positions is not None:
            valid, error_msg = self._validate_weights(current_positions, "当前持仓")
            if not valid:
                logger.error(f"当前持仓验证失败: {error_msg}")
                return False, {"reason": error_msg, "error": True}
        
        if target_positions is not None:
            valid, error_msg = self._validate_weights(target_positions, "目标持仓")
            if not valid:
                logger.error(f"目标持仓验证失败: {error_msg}")
                return False, {"reason": error_msg, "error": True}
        
        current_positions = current_positions or {}
        target_positions = target_positions or {}
        
        if not current_positions and not target_positions:
            return False, {"reason": "当前持仓和目标持仓都为空"}
        
        if not current_positions:
            return True, {"reason": "当前持仓为空，需要建仓"}
        
        if not target_positions:
            return True, {"reason": "目标持仓为空，需要清仓"}
        
        if self.config.trigger_type == RebalanceTrigger.PERIODIC:
            return self._check_periodic_rebalance(last_rebalance_date, current_date)
        elif self.config.trigger_type == RebalanceTrigger.COST_OPTIMIZED:
            return self._check_cost_optimized_rebalance(current_positions, target_positions)
        else:
            return self._check_threshold_rebalance(current_positions, target_positions, threshold)
    
    def _check_threshold_rebalance(
        self,
        current_positions: dict,
        target_positions: dict,
        threshold: float
    ) -> Tuple[bool, dict]:
        """检查阈值触发再平衡"""
        all_stocks = set(current_positions.keys()) | set(target_positions.keys())
        
        max_deviation = 0
        deviations = {}
        
        for stock in all_stocks:
            current_weight = current_positions.get(stock, 0)
            target_weight = target_positions.get(stock, 0)
            deviation = abs(current_weight - target_weight)
            deviations[stock] = deviation
            max_deviation = max(max_deviation, deviation)
        
        details = {
            "max_deviation": max_deviation,
            "deviations": deviations,
            "threshold": threshold,
            "current_stock_count": len(current_positions),
            "target_stock_count": len(target_positions),
            "trigger_type": "threshold"
        }
        
        if max_deviation > threshold:
            details["reason"] = f"最大偏离度 {max_deviation*100:.2f}% 超过阈值 {threshold*100:.2f}%"
            return True, details
        else:
            details["reason"] = f"最大偏离度 {max_deviation*100:.2f}% 未超过阈值 {threshold*100:.2f}%"
            return False, details
    
    def _check_periodic_rebalance(
        self,
        last_rebalance_date: datetime,
        current_date: datetime
    ) -> Tuple[bool, dict]:
        """检查定期再平衡"""
        if last_rebalance_date is None:
            return True, {"reason": "无上次再平衡记录，需要再平衡", "trigger_type": "periodic"}
        
        if current_date is None:
            current_date = datetime.now()
        
        days_since_rebalance = (current_date - last_rebalance_date).days
        
        frequency_days = {
            "daily": 1,
            "weekly": 7,
            "biweekly": 14,
            "monthly": 30,
            "quarterly": 90,
            "yearly": 365
        }
        
        target_days = frequency_days.get(self.config.frequency, 7)
        
        details = {
            "last_rebalance_date": last_rebalance_date.isoformat() if last_rebalance_date else None,
            "current_date": current_date.isoformat() if current_date else None,
            "days_since_rebalance": days_since_rebalance,
            "target_days": target_days,
            "frequency": self.config.frequency,
            "trigger_type": "periodic"
        }
        
        if days_since_rebalance >= target_days:
            details["reason"] = f"距离上次再平衡 {days_since_rebalance} 天，超过 {self.config.frequency} 周期"
            return True, details
        else:
            details["reason"] = f"距离上次再平衡 {days_since_rebalance} 天，未超过 {self.config.frequency} 周期"
            return False, details
    
    def _check_cost_optimized_rebalance(
        self,
        current_positions: dict,
        target_positions: dict
    ) -> Tuple[bool, dict]:
        """检查成本优化再平衡"""
        need_rebalance, threshold_details = self._check_threshold_rebalance(
            current_positions, target_positions, self.config.threshold
        )
        
        if not need_rebalance:
            return False, threshold_details
        
        trades = self.calculate_trades(current_positions, target_positions)
        turnover = trades.get('turnover', 0)
        
        estimated_cost = turnover * (self.config.commission_rate + self.config.stamp_duty + self.config.slippage)
        
        details = {
            **threshold_details,
            "turnover": turnover,
            "estimated_cost": estimated_cost,
            "trigger_type": "cost_optimized"
        }
        
        if estimated_cost > 0.005:
            details["reason"] = f"再平衡成本 {estimated_cost*100:.2f}% 较高，建议谨慎"
            details["cost_warning"] = True
        
        return True, details
    
    def calculate_trades(
        self,
        current_positions: dict,
        target_positions: dict,
        prices: dict = None,
        portfolio_value: float = 1000000
    ) -> dict:
        """
        计算再平衡交易
        
        Args:
            current_positions: 当前持仓 {stock_code: weight}
            target_positions: 目标持仓 {stock_code: weight}
            prices: 价格字典 {stock_code: price}
            portfolio_value: 组合价值
            
        Returns:
            交易计划
        """
        if current_positions is not None:
            valid, error_msg = self._validate_weights(current_positions, "当前持仓")
            if not valid:
                logger.error(f"当前持仓验证失败: {error_msg}")
                return {
                    'trades': [],
                    'turnover': 0,
                    'error': error_msg
                }
        
        if target_positions is not None:
            valid, error_msg = self._validate_weights(target_positions, "目标持仓")
            if not valid:
                logger.error(f"目标持仓验证失败: {error_msg}")
                return {
                    'trades': [],
                    'turnover': 0,
                    'error': error_msg
                }
        
        current_positions = current_positions or {}
        target_positions = target_positions or {}
        
        trades = []
        all_stocks = set(current_positions.keys()) | set(target_positions.keys())
        
        for stock in all_stocks:
            current_weight = current_positions.get(stock, 0)
            target_weight = target_positions.get(stock, 0)
            weight_diff = target_weight - current_weight
            
            if abs(weight_diff) < 0.001:
                action = 'hold'
            elif weight_diff > 0:
                action = 'buy'
            else:
                action = 'sell'
            
            trade = Trade(
                stock_code=stock,
                action=action,
                weight_diff=weight_diff,
                current_weight=current_weight,
                target_weight=target_weight
            )
            
            if prices and stock in prices:
                price = prices[stock]
                if price > 0:
                    amount = abs(weight_diff) * portfolio_value
                    shares = amount / price
                    trade.shares = shares
                    trade.amount = amount
            
            trades.append(trade)
        
        turnover = sum(abs(t.weight_diff) for t in trades) / 2
        
        logger.info(f"再平衡交易计算完成: {len(trades)} 只股票, 换手率 {turnover*100:.2f}%")
        
        return {
            'trades': trades,
            'turnover': turnover,
            'buy_count': sum(1 for t in trades if t.action == 'buy'),
            'sell_count': sum(1 for t in trades if t.action == 'sell'),
            'hold_count': sum(1 for t in trades if t.action == 'hold')
        }
    
    def estimate_rebalance_cost(
        self,
        trades: List[Trade],
        prices: dict,
        portfolio_value: float = 1000000
    ) -> dict:
        """
        估算再平衡成本
        
        Args:
            trades: 交易列表
            prices: 价格字典
            portfolio_value: 组合价值
            
        Returns:
            成本估算
        """
        if not isinstance(trades, list):
            trades = trades.get('trades', [])
        
        total_commission = 0
        total_stamp_duty = 0
        total_slippage = 0
        
        for trade in trades:
            if not isinstance(trade, Trade):
                continue
            
            if trade.action == 'hold':
                continue
            
            weight_diff = trade.weight_diff
            trade_value = abs(weight_diff) * portfolio_value
            
            if prices and trade.stock_code in prices:
                price = prices[trade.stock_code]
                if price <= 0:
                    continue
                
                shares = trade_value / price
                
                commission = shares * price * self.config.commission_rate
                total_commission += commission
                
                if trade.action == 'sell':
                    stamp_duty_cost = shares * price * self.config.stamp_duty
                    total_stamp_duty += stamp_duty_cost
                
                slippage_cost = shares * price * self.config.slippage
                total_slippage += slippage_cost
        
        total_cost = total_commission + total_stamp_duty + total_slippage
        cost_ratio = total_cost / portfolio_value if portfolio_value > 0 else 0
        
        cost_estimate = {
            'total_commission': total_commission,
            'total_stamp_duty': total_stamp_duty,
            'total_slippage': total_slippage,
            'total_cost': total_cost,
            'cost_ratio': cost_ratio,
            'portfolio_value': portfolio_value,
            'commission_rate': self.config.commission_rate,
            'stamp_duty_rate': self.config.stamp_duty,
            'slippage_rate': self.config.slippage
        }
        
        logger.info(f"再平衡成本估算: 总成本 {total_cost:.2f}, 成本率 {cost_ratio*100:.3f}%")
        
        return cost_estimate
    
    def execute_rebalance(
        self,
        current_positions: dict,
        target_positions: dict,
        prices: dict = None,
        portfolio_value: float = 1000000
    ) -> RebalanceResult:
        """
        执行再平衡
        
        Args:
            current_positions: 当前持仓
            target_positions: 目标持仓
            prices: 价格字典
            portfolio_value: 组合价值
            
        Returns:
            RebalanceResult: 再平衡结果
        """
        need_rebalance, details = self.should_rebalance(
            current_positions, target_positions
        )
        
        if not need_rebalance:
            return RebalanceResult(
                status=RebalanceStatus.NOT_NEEDED,
                need_rebalance=False,
                message=details.get("reason", "不需要再平衡"),
                details=details
            )
        
        trades_result = self.calculate_trades(
            current_positions, target_positions, prices, portfolio_value
        )
        
        trades = trades_result.get('trades', [])
        turnover = trades_result.get('turnover', 0)
        
        if turnover > self.config.max_turnover:
            logger.warning(f"换手率 {turnover:.2%} 超过限制 {self.config.max_turnover:.2%}")
            details['turnover_warning'] = True
        
        cost_estimate = self.estimate_rebalance_cost(trades, prices, portfolio_value)
        
        return RebalanceResult(
            status=RebalanceStatus.NEEDED,
            need_rebalance=True,
            trades=trades,
            turnover=turnover,
            message=f"需要再平衡，换手率 {turnover:.2%}，预计成本 {cost_estimate['cost_ratio']*100:.3f}%",
            trigger_type=self.config.trigger_type,
            details={
                **details,
                'cost_estimate': cost_estimate,
                'trade_count': len(trades)
            }
        )
    
    def _validate_weights(
        self, 
        positions: dict, 
        name: str = "positions"
    ) -> Tuple[bool, str]:
        """验证权重字典"""
        if not isinstance(positions, dict):
            return False, f"{name} 必须是字典类型，当前类型: {type(positions)}"
        
        for stock_code, weight in positions.items():
            if not isinstance(stock_code, str):
                return False, f"{name} 中的股票代码必须是字符串类型，当前类型: {type(stock_code)}"
            
            if not isinstance(weight, (int, float)):
                return False, f"{name} 中的权重必须是数值类型，{stock_code} 当前类型: {type(weight)}"
            
            if weight < 0:
                return False, f"{name} 中的权重不能为负数，{stock_code} = {weight}"
            
            if weight > 1:
                logger.warning(f"{name} 中的权重超过100%，{stock_code} = {weight:.4f}")
        
        return True, ""


__all__ = [
    'RebalanceTrigger',
    'RebalanceStatus',
    'Trade',
    'RebalanceResult',
    'RebalanceConfig',
    'RebalanceError',
    'PortfolioRebalancer',
]
