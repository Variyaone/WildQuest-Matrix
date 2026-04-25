"""
仓位计算器模块

将选股结果和权重优化结果转换为具体交易数量。

流程:
  选股结果 → 权重优化 → 仓位计算 → 具体股数
  
支持:
  - 等权重分配
  - 得分加权分配
  - 风险平价分配
  - 自定义权重分配
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

import numpy as np
import pandas as pd

from core.infrastructure.exceptions import AppException, ErrorCode

logger = logging.getLogger(__name__)


class SizingMethod(Enum):
    """仓位计算方法"""
    EQUAL = "equal"
    SCORE_WEIGHTED = "score_weighted"
    RISK_PARITY = "risk_parity"
    CUSTOM = "custom"
    KELLY = "kelly"


class SizingStatus(Enum):
    """仓位计算状态"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    INSUFFICIENT_FUNDS = "insufficient_funds"


@dataclass
class PositionSize:
    """仓位大小"""
    stock_code: str
    stock_name: str = ""
    weight: float = 0.0
    target_value: float = 0.0
    price: float = 0.0
    quantity: int = 0
    actual_value: float = 0.0
    score: float = 0.0
    round_lot: int = 100
    
    @property
    def actual_weight(self) -> float:
        if self.target_value > 0:
            return self.actual_value / self.target_value
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'weight': self.weight,
            'target_value': self.target_value,
            'price': self.price,
            'quantity': self.quantity,
            'actual_value': self.actual_value,
            'actual_weight': self.actual_weight,
            'score': self.score,
            'round_lot': self.round_lot
        }


@dataclass
class SizingResult:
    """仓位计算结果"""
    status: SizingStatus
    method: SizingMethod
    positions: List[PositionSize] = field(default_factory=list)
    total_capital: float = 0.0
    allocated_capital: float = 0.0
    remaining_capital: float = 0.0
    allocation_rate: float = 0.0
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'method': self.method.value,
            'positions': [p.to_dict() for p in self.positions],
            'total_capital': self.total_capital,
            'allocated_capital': self.allocated_capital,
            'remaining_capital': self.remaining_capital,
            'allocation_rate': self.allocation_rate,
            'message': self.message,
            'details': self.details
        }
    
    def get_target_positions(self) -> Dict[str, Dict]:
        """获取目标持仓字典"""
        return {
            p.stock_code: {
                'stock_name': p.stock_name,
                'quantity': p.quantity,
                'price': p.price,
                'value': p.actual_value,
                'weight': p.weight
            }
            for p in self.positions
        }


class PositionSizerError(AppException):
    """仓位计算错误"""
    
    def __init__(self, message: str, details: Optional[Dict] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.STRATEGY_ERROR,
            details=details or {},
            cause=cause
        )


@dataclass
class SizingConfig:
    """仓位计算配置"""
    round_lot: int = 100
    min_position_value: float = 5000.0
    max_single_weight: float = 0.15
    min_single_weight: float = 0.01
    reserve_cash_ratio: float = 0.02
    allow_fractional: bool = False
    kelly_fraction: float = 0.25


class PositionSizer:
    """
    仓位计算器
    
    将权重转换为具体股数。
    """
    
    def __init__(self, config: SizingConfig = None):
        self.config = config or SizingConfig()
    
    def size(
        self,
        stock_selections: List[Dict],
        total_capital: float,
        prices: Dict[str, float],
        weights: Dict[str, float] = None,
        method: SizingMethod = SizingMethod.EQUAL,
        stock_names: Dict[str, str] = None,
        volatilities: Dict[str, float] = None,
        expected_returns: Dict[str, float] = None
    ) -> SizingResult:
        """
        计算仓位大小
        
        Args:
            stock_selections: 选股结果列表 [{'stock_code': str, 'score': float, ...}]
            total_capital: 总资金
            prices: 股票价格字典 {stock_code: price}
            weights: 权重字典 {stock_code: weight}，可选
            method: 计算方法
            stock_names: 股票名称字典
            volatilities: 波动率字典（用于风险平价）
            expected_returns: 预期收益率字典（用于Kelly）
            
        Returns:
            SizingResult: 仓位计算结果
        """
        if not stock_selections:
            return SizingResult(
                status=SizingStatus.FAILED,
                method=method,
                total_capital=total_capital,
                message="选股结果为空"
            )
        
        stock_codes = [s['stock_code'] for s in stock_selections]
        scores = {s['stock_code']: s.get('score', 1.0) for s in stock_selections}
        stock_names = stock_names or {}
        
        missing_prices = [code for code in stock_codes if code not in prices]
        if missing_prices:
            return SizingResult(
                status=SizingStatus.FAILED,
                method=method,
                total_capital=total_capital,
                message=f"缺少价格数据: {missing_prices}"
            )
        
        if weights is None:
            weights = self._calculate_weights(
                stock_codes, scores, method, volatilities
            )
        
        weights = self._apply_constraints(weights)
        
        available_capital = total_capital * (1 - self.config.reserve_cash_ratio)
        
        positions = self._calculate_positions(
            weights, available_capital, prices, scores, stock_names
        )
        
        positions = self._adjust_for_min_position(positions)
        
        allocated = sum(p.actual_value for p in positions)
        remaining = total_capital - allocated
        
        if allocated < total_capital * 0.5:
            status = SizingStatus.PARTIAL
            message = f"仅分配了 {allocated/total_capital:.1%} 的资金"
        elif allocated < total_capital * 0.01:
            status = SizingStatus.INSUFFICIENT_FUNDS
            message = "资金不足，无法建立有效仓位"
        else:
            status = SizingStatus.SUCCESS
            message = f"成功分配 {len(positions)} 只股票的仓位"
        
        return SizingResult(
            status=status,
            method=method,
            positions=positions,
            total_capital=total_capital,
            allocated_capital=allocated,
            remaining_capital=remaining,
            allocation_rate=allocated / total_capital if total_capital > 0 else 0,
            message=message,
            details={
                'stock_count': len(positions),
                'reserve_cash': total_capital * self.config.reserve_cash_ratio
            }
        )
    
    def _calculate_weights(
        self,
        stock_codes: List[str],
        scores: Dict[str, float],
        method: SizingMethod,
        volatilities: Dict[str, float] = None
    ) -> Dict[str, float]:
        """计算权重"""
        if method == SizingMethod.EQUAL:
            n = len(stock_codes)
            return {code: 1.0 / n for code in stock_codes}
        
        elif method == SizingMethod.SCORE_WEIGHTED:
            total_score = sum(scores.values())
            if total_score > 0:
                return {code: scores[code] / total_score for code in stock_codes}
            return {code: 1.0 / len(stock_codes) for code in stock_codes}
        
        elif method == SizingMethod.RISK_PARITY:
            if volatilities:
                inv_vols = {code: 1.0 / volatilities.get(code, 0.2) for code in stock_codes}
                total_inv = sum(inv_vols.values())
                return {code: v / total_inv for code, v in inv_vols.items()}
            n = len(stock_codes)
            return {code: 1.0 / n for code in stock_codes}
        
        elif method == SizingMethod.KELLY:
            return {code: 1.0 / len(stock_codes) for code in stock_codes}
        
        else:
            n = len(stock_codes)
            return {code: 1.0 / n for code in stock_codes}
    
    def _apply_constraints(self, weights: Dict[str, float]) -> Dict[str, float]:
        """应用权重约束"""
        for code in weights:
            weights[code] = min(weights[code], self.config.max_single_weight)
            weights[code] = max(weights[code], self.config.min_single_weight)
        
        total = sum(weights.values())
        if total > 0:
            weights = {code: w / total for code, w in weights.items()}
        
        return weights
    
    def _calculate_positions(
        self,
        weights: Dict[str, float],
        capital: float,
        prices: Dict[str, float],
        scores: Dict[str, float],
        stock_names: Dict[str, str]
    ) -> List[PositionSize]:
        """计算具体仓位"""
        positions = []
        
        for code, weight in weights.items():
            price = prices.get(code, 0)
            if price <= 0:
                continue
            
            target_value = capital * weight
            
            if self.config.allow_fractional:
                quantity = int(target_value / price)
            else:
                raw_quantity = target_value / price
                quantity = int(raw_quantity // self.config.round_lot) * self.config.round_lot
            
            actual_value = quantity * price
            
            if quantity > 0:
                positions.append(PositionSize(
                    stock_code=code,
                    stock_name=stock_names.get(code, ""),
                    weight=weight,
                    target_value=target_value,
                    price=price,
                    quantity=quantity,
                    actual_value=actual_value,
                    score=scores.get(code, 0),
                    round_lot=self.config.round_lot
                ))
        
        return positions
    
    def _adjust_for_min_position(self, positions: List[PositionSize]) -> List[PositionSize]:
        """调整最小仓位"""
        return [
            p for p in positions
            if p.actual_value >= self.config.min_position_value
        ]
    
    def size_with_kelly(
        self,
        stock_selections: List[Dict],
        total_capital: float,
        prices: Dict[str, float],
        win_rates: Dict[str, float],
        win_loss_ratios: Dict[str, float],
        stock_names: Dict[str, str] = None
    ) -> SizingResult:
        """
        使用Kelly公式计算仓位
        
        Kelly公式: f* = (p * b - q) / b
        其中 p = 胜率, q = 1-p, b = 盈亏比
        
        Args:
            stock_selections: 选股结果
            total_capital: 总资金
            prices: 价格字典
            win_rates: 胜率字典
            win_loss_ratios: 盈亏比字典
            stock_names: 股票名称字典
            
        Returns:
            SizingResult: 仓位计算结果
        """
        kelly_weights = {}
        
        for selection in stock_selections:
            code = selection['stock_code']
            p = win_rates.get(code, 0.5)
            b = win_loss_ratios.get(code, 1.0)
            q = 1 - p
            
            kelly_fraction = (p * b - q) / b if b > 0 else 0
            kelly_fraction = max(0, min(kelly_fraction, self.config.max_single_weight))
            kelly_weights[code] = kelly_fraction * self.config.kelly_fraction
        
        total_kelly = sum(kelly_weights.values())
        if total_kelly > 1:
            kelly_weights = {k: v / total_kelly for k, v in kelly_weights.items()}
        
        return self.size(
            stock_selections=stock_selections,
            total_capital=total_capital,
            prices=prices,
            weights=kelly_weights,
            method=SizingMethod.KELLY,
            stock_names=stock_names
        )
    
    def size_from_optimizer_result(
        self,
        stock_selections: List[Dict],
        total_capital: float,
        prices: Dict[str, float],
        optimizer_result: Any,
        stock_names: Dict[str, str] = None
    ) -> SizingResult:
        """
        从优化器结果计算仓位
        
        Args:
            stock_selections: 选股结果
            total_capital: 总资金
            prices: 价格字典
            optimizer_result: PortfolioOptimizer.optimize() 的返回结果
            stock_names: 股票名称字典
            
        Returns:
            SizingResult: 仓位计算结果
        """
        if hasattr(optimizer_result, 'weights'):
            weights = optimizer_result.weights
        elif isinstance(optimizer_result, dict):
            weights = optimizer_result.get('weights', {})
        else:
            weights = None
        
        if not weights:
            return SizingResult(
                status=SizingStatus.FAILED,
                method=SizingMethod.CUSTOM,
                total_capital=total_capital,
                message="优化器结果中没有权重信息"
            )
        
        return self.size(
            stock_selections=stock_selections,
            total_capital=total_capital,
            prices=prices,
            weights=weights,
            method=SizingMethod.CUSTOM,
            stock_names=stock_names
        )
    
    def rebalance(
        self,
        target_weights: Dict[str, float],
        current_positions: Dict[str, Dict],
        total_capital: float,
        prices: Dict[str, float],
        stock_names: Dict[str, str] = None
    ) -> Tuple[Dict[str, PositionSize], Dict[str, PositionSize], List[str]]:
        """
        计算再平衡需要的调整
        
        Args:
            target_weights: 目标权重
            current_positions: 当前持仓 {stock_code: {'quantity': int, 'price': float}}
            total_capital: 总资金
            prices: 当前价格
            stock_names: 股票名称
            
        Returns:
            Tuple[买入仓位, 卖出仓位, 持仓不变]
        """
        stock_names = stock_names or {}
        
        target_positions = {}
        for code, weight in target_weights.items():
            price = prices.get(code, 0)
            if price <= 0:
                continue
            
            target_value = total_capital * weight
            quantity = int(target_value / price // self.config.round_lot) * self.config.round_lot
            
            target_positions[code] = PositionSize(
                stock_code=code,
                stock_name=stock_names.get(code, ""),
                weight=weight,
                target_value=target_value,
                price=price,
                quantity=quantity,
                actual_value=quantity * price
            )
        
        buy_positions = {}
        sell_positions = {}
        hold_stocks = []
        
        all_codes = set(target_positions.keys()) | set(current_positions.keys())
        
        for code in all_codes:
            target_qty = target_positions.get(code, PositionSize(stock_code=code)).quantity
            current_qty = current_positions.get(code, {}).get('quantity', 0)
            
            diff = target_qty - current_qty
            
            if diff > 0:
                price = prices.get(code, 0)
                buy_positions[code] = PositionSize(
                    stock_code=code,
                    stock_name=stock_names.get(code, ""),
                    quantity=diff,
                    price=price,
                    actual_value=diff * price
                )
            elif diff < 0:
                price = prices.get(code, 0)
                sell_positions[code] = PositionSize(
                    stock_code=code,
                    stock_name=stock_names.get(code, ""),
                    quantity=abs(diff),
                    price=price,
                    actual_value=abs(diff) * price
                )
            else:
                hold_stocks.append(code)
        
        logger.info(f"再平衡计算完成: 买入 {len(buy_positions)}, 卖出 {len(sell_positions)}, 持有 {len(hold_stocks)}")
        
        return buy_positions, sell_positions, hold_stocks


_default_sizer: Optional[PositionSizer] = None


def get_position_sizer() -> PositionSizer:
    """获取全局仓位计算器实例"""
    global _default_sizer
    if _default_sizer is None:
        _default_sizer = PositionSizer()
    return _default_sizer


def reset_position_sizer():
    """重置全局仓位计算器"""
    global _default_sizer
    _default_sizer = None


__all__ = [
    'SizingMethod',
    'SizingStatus',
    'PositionSize',
    'SizingResult',
    'SizingConfig',
    'PositionSizer',
    'PositionSizerError',
    'get_position_sizer',
    'reset_position_sizer',
]
