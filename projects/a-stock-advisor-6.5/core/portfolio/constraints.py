"""
组合约束管理模块

管理组合层面的各类约束:
- 单票权重上限
- 行业权重上限
- 换手率限制
- 持仓数量限制
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from core.infrastructure.exceptions import AppException, ErrorCode

logger = logging.getLogger(__name__)


class ConstraintType(Enum):
    """约束类型"""
    HARD = "hard"
    SOFT = "soft"


class ConstraintStatus(Enum):
    """约束状态"""
    SATISFIED = "satisfied"
    VIOLATED = "violated"
    WARNING = "warning"


@dataclass
class ConstraintResult:
    """约束检查结果"""
    constraint_name: str
    status: ConstraintStatus
    passed: bool
    actual_value: Any
    limit_value: Any
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'constraint_name': self.constraint_name,
            'status': self.status.value,
            'passed': self.passed,
            'actual_value': self.actual_value,
            'limit_value': self.limit_value,
            'message': self.message,
            'details': self.details
        }


@dataclass
class ConstraintsCheckResult:
    """约束检查总结果"""
    passed: bool
    results: List[ConstraintResult]
    violations: List[ConstraintResult]
    warnings: List[ConstraintResult]
    summary: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'passed': self.passed,
            'results': [r.to_dict() for r in self.results],
            'violations': [v.to_dict() for v in self.violations],
            'warnings': [w.to_dict() for w in self.warnings],
            'summary': self.summary
        }


class ConstraintError(AppException):
    """约束错误异常"""
    
    def __init__(self, message: str, details: Optional[Dict] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.RISK_LIMIT_EXCEEDED,
            details=details or {},
            cause=cause
        )


@dataclass
class ConstraintConfig:
    """约束配置"""
    max_single_weight: float = 0.15
    max_industry_weight: float = 0.30
    min_positions: int = 5
    max_positions: int = 20
    max_turnover: float = 0.20
    min_weight: float = 0.0
    max_total_weight: float = 1.05
    min_total_weight: float = 0.95


class ConstraintsManager:
    """
    组合约束管理器
    
    管理组合层面的各类约束:
    - 单票权重上限（默认≤15%）
    - 行业权重上限（默认≤30%）
    - 换手率限制（默认≤20%）
    - 最小持仓数量（默认≥5只）
    - 最大持仓数量（默认≤20只）
    """
    
    def __init__(self, config: ConstraintConfig = None):
        self.config = config or ConstraintConfig()
    
    def check_all(
        self,
        weights: Dict[str, float],
        industry_exposures: Dict[str, str] = None,
        current_weights: Dict[str, float] = None,
        context: Dict[str, Any] = None
    ) -> ConstraintsCheckResult:
        """
        检查所有约束
        
        Args:
            weights: 组合权重字典 {stock_code: weight}
            industry_exposures: 行业暴露 {stock_code: industry}
            current_weights: 当前权重（用于计算换手率）
            context: 额外上下文信息
            
        Returns:
            ConstraintsCheckResult: 约束检查结果
        """
        context = context or {}
        results: List[ConstraintResult] = []
        violations: List[ConstraintResult] = []
        warnings: List[ConstraintResult] = []
        
        if not weights:
            result = ConstraintResult(
                constraint_name="权重非空",
                status=ConstraintStatus.VIOLATED,
                passed=False,
                actual_value=0,
                limit_value="> 0",
                message="权重字典为空"
            )
            results.append(result)
            violations.append(result)
            return ConstraintsCheckResult(
                passed=False,
                results=results,
                violations=violations,
                warnings=warnings,
                summary={'error': 'empty_weights'}
            )
        
        results.append(self._check_weight_normalization(weights))
        results.append(self._check_single_weight_limit(weights))
        results.append(self._check_non_negative_weights(weights))
        
        if industry_exposures:
            results.append(self._check_industry_concentration(weights, industry_exposures))
        
        results.append(self._check_position_count(weights))
        
        if current_weights:
            results.append(self._check_turnover(weights, current_weights))
        
        for result in results:
            if result.status == ConstraintStatus.VIOLATED:
                violations.append(result)
            elif result.status == ConstraintStatus.WARNING:
                warnings.append(result)
        
        all_passed = len(violations) == 0
        
        summary = {
            'total_constraints': len(results),
            'passed_count': sum(1 for r in results if r.passed),
            'violations_count': len(violations),
            'warnings_count': len(warnings),
            'total_weight': sum(weights.values()),
            'position_count': len(weights)
        }
        
        return ConstraintsCheckResult(
            passed=all_passed,
            results=results,
            violations=violations,
            warnings=warnings,
            summary=summary
        )
    
    def _check_weight_normalization(self, weights: Dict[str, float]) -> ConstraintResult:
        """检查权重归一化"""
        total_weight = sum(weights.values())
        normalized = self.config.min_total_weight <= total_weight <= self.config.max_total_weight
        
        if normalized:
            status = ConstraintStatus.SATISFIED
            message = f"权重归一化检查通过: {total_weight:.4f}"
        else:
            status = ConstraintStatus.VIOLATED
            message = f"权重归一化检查失败: {total_weight:.4f} 不在 [{self.config.min_total_weight}, {self.config.max_total_weight}] 范围内"
        
        return ConstraintResult(
            constraint_name="权重归一化",
            status=status,
            passed=normalized,
            actual_value=total_weight,
            limit_value=f"[{self.config.min_total_weight}, {self.config.max_total_weight}]",
            message=message,
            details={'total_weight': total_weight}
        )
    
    def _check_single_weight_limit(self, weights: Dict[str, float]) -> ConstraintResult:
        """检查单票权重上限"""
        max_weight = max(weights.values()) if weights else 0
        max_stock = max(weights.keys(), key=lambda k: weights[k]) if weights else ""
        
        within_limit = max_weight <= self.config.max_single_weight
        
        if within_limit:
            status = ConstraintStatus.SATISFIED
            message = f"单票权重上限检查通过: 最大权重 {max_weight:.2%}"
        else:
            status = ConstraintStatus.VIOLATED
            message = f"单票权重上限检查失败: {max_stock} 权重 {max_weight:.2%} 超过上限 {self.config.max_single_weight:.2%}"
        
        return ConstraintResult(
            constraint_name="单票权重上限",
            status=status,
            passed=within_limit,
            actual_value=max_weight,
            limit_value=self.config.max_single_weight,
            message=message,
            details={'max_weight_stock': max_stock, 'max_weight': max_weight}
        )
    
    def _check_non_negative_weights(self, weights: Dict[str, float]) -> ConstraintResult:
        """检查权重非负"""
        negative_weights = {k: v for k, v in weights.items() if v < 0}
        all_positive = len(negative_weights) == 0
        
        if all_positive:
            status = ConstraintStatus.SATISFIED
            message = "权重非负检查通过"
        else:
            status = ConstraintStatus.VIOLATED
            message = f"权重非负检查失败: {len(negative_weights)} 只股票权重为负"
        
        return ConstraintResult(
            constraint_name="权重非负",
            status=status,
            passed=all_positive,
            actual_value=len(negative_weights),
            limit_value=0,
            message=message,
            details={'negative_weights': negative_weights}
        )
    
    def _check_industry_concentration(
        self,
        weights: Dict[str, float],
        industry_exposures: Dict[str, str]
    ) -> ConstraintResult:
        """检查行业集中度"""
        industry_weights = {}
        for stock, weight in weights.items():
            industry = industry_exposures.get(stock, "其他")
            industry_weights[industry] = industry_weights.get(industry, 0) + weight
        
        max_industry = max(industry_weights.keys(), key=lambda k: industry_weights[k]) if industry_weights else ""
        max_industry_weight = industry_weights.get(max_industry, 0)
        
        within_limit = max_industry_weight <= self.config.max_industry_weight
        
        if within_limit:
            status = ConstraintStatus.SATISFIED
            message = f"行业集中度检查通过: 最大行业权重 {max_industry_weight:.2%}"
        else:
            status = ConstraintStatus.WARNING
            message = f"行业集中度警告: 行业 {max_industry} 权重 {max_industry_weight:.2%} 超过上限 {self.config.max_industry_weight:.2%}"
        
        return ConstraintResult(
            constraint_name="行业集中度",
            status=status,
            passed=within_limit,
            actual_value=max_industry_weight,
            limit_value=self.config.max_industry_weight,
            message=message,
            details={'industry_weights': industry_weights, 'max_industry': max_industry}
        )
    
    def _check_position_count(self, weights: Dict[str, float]) -> ConstraintResult:
        """检查持仓数量"""
        position_count = len(weights)
        
        min_ok = position_count >= self.config.min_positions
        max_ok = position_count <= self.config.max_positions
        
        if min_ok and max_ok:
            status = ConstraintStatus.SATISFIED
            message = f"持仓数量检查通过: {position_count} 只"
        elif not min_ok:
            status = ConstraintStatus.WARNING
            message = f"持仓数量警告: {position_count} 只少于最小要求 {self.config.min_positions} 只"
        else:
            status = ConstraintStatus.WARNING
            message = f"持仓数量警告: {position_count} 只超过最大限制 {self.config.max_positions} 只"
        
        return ConstraintResult(
            constraint_name="持仓数量",
            status=status,
            passed=min_ok and max_ok,
            actual_value=position_count,
            limit_value=f"[{self.config.min_positions}, {self.config.max_positions}]",
            message=message,
            details={'position_count': position_count}
        )
    
    def _check_turnover(
        self,
        weights: Dict[str, float],
        current_weights: Dict[str, float]
    ) -> ConstraintResult:
        """检查换手率"""
        all_stocks = set(weights.keys()) | set(current_weights.keys())
        
        total_turnover = 0
        for stock in all_stocks:
            target_weight = weights.get(stock, 0)
            current_weight = current_weights.get(stock, 0)
            total_turnover += abs(target_weight - current_weight)
        
        turnover = total_turnover / 2
        
        within_limit = turnover <= self.config.max_turnover
        
        if within_limit:
            status = ConstraintStatus.SATISFIED
            message = f"换手率检查通过: {turnover:.2%}"
        else:
            status = ConstraintStatus.WARNING
            message = f"换手率警告: {turnover:.2%} 超过上限 {self.config.max_turnover:.2%}"
        
        return ConstraintResult(
            constraint_name="换手率",
            status=status,
            passed=within_limit,
            actual_value=turnover,
            limit_value=self.config.max_turnover,
            message=message,
            details={'turnover': turnover}
        )
    
    def apply_constraints(
        self,
        weights: Dict[str, float],
        industry_exposures: Dict[str, str] = None
    ) -> Dict[str, float]:
        """
        应用约束调整权重
        
        Args:
            weights: 原始权重
            industry_exposures: 行业暴露
            
        Returns:
            调整后的权重
        """
        adjusted_weights = weights.copy()
        
        for stock in adjusted_weights:
            if adjusted_weights[stock] > self.config.max_single_weight:
                adjusted_weights[stock] = self.config.max_single_weight
        
        for stock in adjusted_weights:
            if adjusted_weights[stock] < self.config.min_weight:
                adjusted_weights[stock] = self.config.min_weight
        
        if industry_exposures:
            adjusted_weights = self._apply_industry_constraint(adjusted_weights, industry_exposures)
        
        total_weight = sum(adjusted_weights.values())
        if total_weight > 0:
            adjusted_weights = {k: v / total_weight for k, v in adjusted_weights.items()}
        
        return adjusted_weights
    
    def _apply_industry_constraint(
        self,
        weights: Dict[str, float],
        industry_exposures: Dict[str, str]
    ) -> Dict[str, float]:
        """应用行业约束"""
        industry_weights = {}
        for stock, weight in weights.items():
            industry = industry_exposures.get(stock, "其他")
            industry_weights[industry] = industry_weights.get(industry, 0) + weight
        
        for industry, weight in industry_weights.items():
            if weight > self.config.max_industry_weight:
                scale_factor = self.config.max_industry_weight / weight
                for stock in weights:
                    if industry_exposures.get(stock, "其他") == industry:
                        weights[stock] *= scale_factor
        
        return weights


__all__ = [
    'ConstraintType',
    'ConstraintStatus',
    'ConstraintResult',
    'ConstraintsCheckResult',
    'ConstraintConfig',
    'ConstraintError',
    'ConstraintsManager',
]
