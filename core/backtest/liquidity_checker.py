"""
流动性约束检查器

强制检查交易流动性，防止回测买入流动性不足的股票。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import date, timedelta
from enum import Enum
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class LiquidityLevel(Enum):
    """流动性等级"""
    HIGH = "high"           # 高流动性
    MEDIUM = "medium"       # 中等流动性
    LOW = "low"             # 低流动性
    ILLIQUID = "illiquid"   # 流动性极差


@dataclass
class LiquidityMetrics:
    """流动性指标"""
    stock_code: str
    date: date
    avg_amount_20d: float
    avg_volume_20d: float
    avg_turnover_20d: float
    amount_std_20d: float
    volume_std_20d: float
    liquidity_score: float
    liquidity_level: LiquidityLevel
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'stock_code': self.stock_code,
            'date': self.date.isoformat(),
            'avg_amount_20d': self.avg_amount_20d,
            'avg_volume_20d': self.avg_volume_20d,
            'avg_turnover_20d': self.avg_turnover_20d,
            'amount_std_20d': self.amount_std_20d,
            'volume_std_20d': self.volume_std_20d,
            'liquidity_score': self.liquidity_score,
            'liquidity_level': self.liquidity_level.value
        }


@dataclass
class LiquidityCheckResult:
    """流动性检查结果"""
    passed: bool
    stock_code: str
    planned_amount: float
    avg_amount: float
    participation_rate: float
    max_participation_rate: float
    liquidity_level: LiquidityLevel
    message: str
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'passed': self.passed,
            'stock_code': self.stock_code,
            'planned_amount': self.planned_amount,
            'avg_amount': self.avg_amount,
            'participation_rate': self.participation_rate,
            'max_participation_rate': self.max_participation_rate,
            'liquidity_level': self.liquidity_level.value,
            'message': self.message,
            'warnings': self.warnings
        }


class LiquidityConstraintChecker:
    """
    流动性约束检查器
    
    检查交易流动性，防止买入流动性不足的股票。
    """
    
    def __init__(
        self,
        max_participation_rate: float = 0.05,
        min_avg_amount: float = 10000000.0,
        min_avg_volume: float = 100000.0,
        lookback_days: int = 20,
        liquidity_score_threshold: float = 0.3,
        strict_mode: bool = True
    ):
        """
        初始化流动性约束检查器
        
        Args:
            max_participation_rate: 最大参与率（默认5%）
            min_avg_amount: 最小日均成交额（默认1000万元）
            min_avg_volume: 最小日均成交量（默认10万股）
            lookback_days: 回看天数（默认20天）
            liquidity_score_threshold: 流动性分数阈值（默认0.3）
            strict_mode: 严格模式（默认True）
        """
        self.max_participation_rate = max_participation_rate
        self.min_avg_amount = min_avg_amount
        self.min_avg_volume = min_avg_volume
        self.lookback_days = lookback_days
        self.liquidity_score_threshold = liquidity_score_threshold
        self.strict_mode = strict_mode
        
        self._liquidity_cache: Dict[str, LiquidityMetrics] = {}
    
    def calculate_liquidity_metrics(
        self,
        stock_code: str,
        target_date: date,
        market_data: pd.DataFrame,
        amount_col: str = "amount",
        volume_col: str = "volume",
        turnover_col: str = "turnover",
        date_col: str = "date",
        stock_col: str = "stock_code"
    ) -> LiquidityMetrics:
        """
        计算流动性指标
        
        Args:
            stock_code: 股票代码
            target_date: 目标日期
            market_data: 市场数据
            amount_col: 成交额列名
            volume_col: 成交量列名
            turnover_col: 换手率列名
            date_col: 日期列名
            stock_col: 股票代码列名
            
        Returns:
            LiquidityMetrics: 流动性指标
        """
        cache_key = f"{stock_code}_{target_date.isoformat()}"
        if cache_key in self._liquidity_cache:
            return self._liquidity_cache[cache_key]
        
        stock_data = market_data[market_data[stock_col] == stock_code].copy()
        stock_data = stock_data.sort_values(date_col)
        
        lookback_start = target_date - timedelta(days=self.lookback_days * 2)
        lookback_start_ts = pd.Timestamp(lookback_start)
        target_date_ts = pd.Timestamp(target_date)
        
        historical_data = stock_data[
            (stock_data[date_col] >= lookback_start_ts) &
            (stock_data[date_col] < target_date_ts)
        ].tail(self.lookback_days)
        
        if len(historical_data) < self.lookback_days // 2:
            logger.warning(f"{stock_code} 历史数据不足: {len(historical_data)} < {self.lookback_days // 2}")
        
        avg_amount = historical_data[amount_col].mean() if amount_col in historical_data.columns else 0.0
        avg_volume = historical_data[volume_col].mean() if volume_col in historical_data.columns else 0.0
        avg_turnover = historical_data[turnover_col].mean() if turnover_col in historical_data.columns else 0.0
        
        amount_std = historical_data[amount_col].std() if amount_col in historical_data.columns else 0.0
        volume_std = historical_data[volume_col].std() if volume_col in historical_data.columns else 0.0
        
        liquidity_score = self._calculate_liquidity_score(
            avg_amount, avg_volume, avg_turnover, amount_std, volume_std
        )
        
        liquidity_level = self._classify_liquidity_level(liquidity_score)
        
        metrics = LiquidityMetrics(
            stock_code=stock_code,
            date=target_date,
            avg_amount_20d=avg_amount,
            avg_volume_20d=avg_volume,
            avg_turnover_20d=avg_turnover,
            amount_std_20d=amount_std,
            volume_std_20d=volume_std,
            liquidity_score=liquidity_score,
            liquidity_level=liquidity_level
        )
        
        self._liquidity_cache[cache_key] = metrics
        
        return metrics
    
    def _calculate_liquidity_score(
        self,
        avg_amount: float,
        avg_volume: float,
        avg_turnover: float,
        amount_std: float,
        volume_std: float
    ) -> float:
        """计算流动性分数"""
        amount_score = min(avg_amount / self.min_avg_amount, 1.0) if self.min_avg_amount > 0 else 0.0
        volume_score = min(avg_volume / self.min_avg_volume, 1.0) if self.min_avg_volume > 0 else 0.0
        
        amount_cv = amount_std / avg_amount if avg_amount > 0 else 1.0
        volume_cv = volume_std / avg_volume if avg_volume > 0 else 1.0
        stability_score = max(0, 1.0 - (amount_cv + volume_cv) / 2)
        
        turnover_score = min(avg_turnover / 0.05, 1.0) if avg_turnover > 0 else 0.0
        
        liquidity_score = (
            amount_score * 0.4 +
            volume_score * 0.2 +
            stability_score * 0.2 +
            turnover_score * 0.2
        )
        
        return liquidity_score
    
    def _classify_liquidity_level(self, liquidity_score: float) -> LiquidityLevel:
        """分类流动性等级"""
        if liquidity_score >= 0.7:
            return LiquidityLevel.HIGH
        elif liquidity_score >= 0.5:
            return LiquidityLevel.MEDIUM
        elif liquidity_score >= 0.3:
            return LiquidityLevel.LOW
        else:
            return LiquidityLevel.ILLIQUID
    
    def check_buy_feasibility(
        self,
        stock_code: str,
        planned_amount: float,
        target_date: date,
        market_data: pd.DataFrame,
        amount_col: str = "amount",
        volume_col: str = "volume",
        turnover_col: str = "turnover",
        date_col: str = "date",
        stock_col: str = "stock_code"
    ) -> LiquidityCheckResult:
        """
        检查买入可行性
        
        Args:
            stock_code: 股票代码
            planned_amount: 计划买入金额
            target_date: 目标日期
            market_data: 市场数据
            amount_col: 成交额列名
            volume_col: 成交量列名
            turnover_col: 换手率列名
            date_col: 日期列名
            stock_col: 股票代码列名
            
        Returns:
            LiquidityCheckResult: 检查结果
        """
        metrics = self.calculate_liquidity_metrics(
            stock_code, target_date, market_data,
            amount_col, volume_col, turnover_col, date_col, stock_col
        )
        
        warnings = []
        
        if metrics.avg_amount_20d < self.min_avg_amount:
            message = f"流动性不足：日均成交额 {metrics.avg_amount_20d:.0f} < {self.min_avg_amount:.0f}"
            return LiquidityCheckResult(
                passed=False,
                stock_code=stock_code,
                planned_amount=planned_amount,
                avg_amount=metrics.avg_amount_20d,
                participation_rate=0.0,
                max_participation_rate=self.max_participation_rate,
                liquidity_level=metrics.liquidity_level,
                message=message,
                warnings=[message]
            )
        
        if metrics.avg_volume_20d < self.min_avg_volume:
            message = f"成交量不足：日均成交量 {metrics.avg_volume_20d:.0f} < {self.min_avg_volume:.0f}"
            return LiquidityCheckResult(
                passed=False,
                stock_code=stock_code,
                planned_amount=planned_amount,
                avg_amount=metrics.avg_amount_20d,
                participation_rate=0.0,
                max_participation_rate=self.max_participation_rate,
                liquidity_level=metrics.liquidity_level,
                message=message,
                warnings=[message]
            )
        
        participation_rate = planned_amount / metrics.avg_amount_20d if metrics.avg_amount_20d > 0 else 1.0
        
        if participation_rate > self.max_participation_rate:
            message = f"参与率过高：{participation_rate:.1%} > {self.max_participation_rate:.1%}"
            warnings.append(message)
            
            if self.strict_mode:
                return LiquidityCheckResult(
                    passed=False,
                    stock_code=stock_code,
                    planned_amount=planned_amount,
                    avg_amount=metrics.avg_amount_20d,
                    participation_rate=participation_rate,
                    max_participation_rate=self.max_participation_rate,
                    liquidity_level=metrics.liquidity_level,
                    message=message,
                    warnings=warnings
                )
        
        if metrics.liquidity_score < self.liquidity_score_threshold:
            warning = f"流动性分数过低：{metrics.liquidity_score:.2f} < {self.liquidity_score_threshold:.2f}"
            warnings.append(warning)
            
            if self.strict_mode and metrics.liquidity_level == LiquidityLevel.ILLIQUID:
                return LiquidityCheckResult(
                    passed=False,
                    stock_code=stock_code,
                    planned_amount=planned_amount,
                    avg_amount=metrics.avg_amount_20d,
                    participation_rate=participation_rate,
                    max_participation_rate=self.max_participation_rate,
                    liquidity_level=metrics.liquidity_level,
                    message=f"流动性极差：{metrics.liquidity_level.value}",
                    warnings=warnings
                )
        
        message = "流动性检查通过"
        if warnings:
            message += f"（有{len(warnings)}个警告）"
        
        return LiquidityCheckResult(
            passed=True,
            stock_code=stock_code,
            planned_amount=planned_amount,
            avg_amount=metrics.avg_amount_20d,
            participation_rate=participation_rate,
            max_participation_rate=self.max_participation_rate,
            liquidity_level=metrics.liquidity_level,
            message=message,
            warnings=warnings
        )
    
    def check_sell_feasibility(
        self,
        stock_code: str,
        planned_amount: float,
        target_date: date,
        market_data: pd.DataFrame,
        amount_col: str = "amount",
        volume_col: str = "volume",
        turnover_col: str = "turnover",
        date_col: str = "date",
        stock_col: str = "stock_code"
    ) -> LiquidityCheckResult:
        """
        检查卖出可行性
        
        Args:
            stock_code: 股票代码
            planned_amount: 计划卖出金额
            target_date: 目标日期
            market_data: 市场数据
            amount_col: 成交额列名
            volume_col: 成交量列名
            turnover_col: 换手率列名
            date_col: 日期列名
            stock_col: 股票代码列名
            
        Returns:
            LiquidityCheckResult: 检查结果
        """
        return self.check_buy_feasibility(
            stock_code, planned_amount, target_date, market_data,
            amount_col, volume_col, turnover_col, date_col, stock_col
        )
    
    def batch_check_liquidity(
        self,
        trade_plans: List[Dict[str, Any]],
        target_date: date,
        market_data: pd.DataFrame,
        amount_col: str = "amount",
        volume_col: str = "volume",
        turnover_col: str = "turnover",
        date_col: str = "date",
        stock_col: str = "stock_code"
    ) -> Tuple[List[LiquidityCheckResult], Dict[str, Any]]:
        """
        批量检查流动性
        
        Args:
            trade_plans: 交易计划列表
            target_date: 目标日期
            market_data: 市场数据
            amount_col: 成交额列名
            volume_col: 成交量列名
            turnover_col: 换手率列名
            date_col: 日期列名
            stock_col: 股票代码列名
            
        Returns:
            Tuple[List[LiquidityCheckResult], Dict]: 检查结果列表和统计信息
        """
        results = []
        
        for plan in trade_plans:
            stock_code = plan.get('stock_code')
            planned_amount = plan.get('amount', 0)
            
            result = self.check_buy_feasibility(
                stock_code, planned_amount, target_date, market_data,
                amount_col, volume_col, turnover_col, date_col, stock_col
            )
            results.append(result)
        
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count
        
        high_liquidity_count = sum(1 for r in results if r.liquidity_level == LiquidityLevel.HIGH)
        medium_liquidity_count = sum(1 for r in results if r.liquidity_level == LiquidityLevel.MEDIUM)
        low_liquidity_count = sum(1 for r in results if r.liquidity_level == LiquidityLevel.LOW)
        illiquid_count = sum(1 for r in results if r.liquidity_level == LiquidityLevel.ILLIQUID)
        
        stats = {
            'total_count': len(results),
            'passed_count': passed_count,
            'failed_count': failed_count,
            'pass_rate': passed_count / len(results) if results else 0.0,
            'liquidity_distribution': {
                'high': high_liquidity_count,
                'medium': medium_liquidity_count,
                'low': low_liquidity_count,
                'illiquid': illiquid_count
            },
            'avg_participation_rate': np.mean([r.participation_rate for r in results]) if results else 0.0
        }
        
        logger.info(
            f"流动性批量检查: {passed_count}/{len(results)} 通过, "
            f"通过率 {stats['pass_rate']:.1%}"
        )
        
        return results, stats
    
    def clear_cache(self):
        """清除缓存"""
        self._liquidity_cache.clear()


def create_liquidity_checker(
    max_participation_rate: float = 0.05,
    min_avg_amount: float = 10000000.0,
    strict_mode: bool = True
) -> LiquidityConstraintChecker:
    """创建流动性约束检查器"""
    return LiquidityConstraintChecker(
        max_participation_rate=max_participation_rate,
        min_avg_amount=min_avg_amount,
        strict_mode=strict_mode
    )
