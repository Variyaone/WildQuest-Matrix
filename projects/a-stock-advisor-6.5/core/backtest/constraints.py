"""
换手率约束和过拟合检测

限制过度交易，检测参数过拟合。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import date
import pandas as pd
import numpy as np
from scipy import stats
import logging

logger = logging.getLogger(__name__)


@dataclass
class TurnoverMetrics:
    """换手率指标"""
    date: date
    portfolio_turnover: float
    buy_turnover: float
    sell_turnover: float
    trade_count: int
    traded_value: float
    portfolio_value: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'date': self.date.isoformat(),
            'portfolio_turnover': self.portfolio_turnover,
            'buy_turnover': self.buy_turnover,
            'sell_turnover': self.sell_turnover,
            'trade_count': self.trade_count,
            'traded_value': self.traded_value,
            'portfolio_value': self.portfolio_value
        }


@dataclass
class TurnoverCheckResult:
    """换手率检查结果"""
    passed: bool
    current_turnover: float
    max_turnover: float
    avg_turnover: float
    turnover_trend: str
    message: str
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'passed': self.passed,
            'current_turnover': self.current_turnover,
            'max_turnover': self.max_turnover,
            'avg_turnover': self.avg_turnover,
            'turnover_trend': self.turnover_trend,
            'message': self.message,
            'warnings': self.warnings
        }


class TurnoverConstraintChecker:
    """
    换手率约束检查器
    
    限制过度交易，防止高频换手策略。
    """
    
    def __init__(
        self,
        max_daily_turnover: float = 0.3,
        max_monthly_turnover: float = 2.0,
        max_annual_turnover: float = 10.0,
        min_holding_days: int = 5,
        warning_threshold: float = 0.8
    ):
        """
        初始化换手率约束检查器
        
        Args:
            max_daily_turnover: 最大日换手率
            max_monthly_turnover: 最大月换手率
            max_annual_turnover: 最大年换手率
            min_holding_days: 最小持仓天数
            warning_threshold: 警告阈值比例
        """
        self.max_daily_turnover = max_daily_turnover
        self.max_monthly_turnover = max_monthly_turnover
        self.max_annual_turnover = max_annual_turnover
        self.min_holding_days = min_holding_days
        self.warning_threshold = warning_threshold
        
        self._turnover_history: List[TurnoverMetrics] = []
    
    def record_turnover(
        self,
        date: date,
        buy_value: float,
        sell_value: float,
        trade_count: int,
        portfolio_value: float
    ):
        """
        记录换手率
        
        Args:
            date: 日期
            buy_value: 买入金额
            sell_value: 卖出金额
            trade_count: 交易次数
            portfolio_value: 组合价值
        """
        traded_value = buy_value + sell_value
        portfolio_turnover = traded_value / portfolio_value if portfolio_value > 0 else 0.0
        buy_turnover = buy_value / portfolio_value if portfolio_value > 0 else 0.0
        sell_turnover = sell_value / portfolio_value if portfolio_value > 0 else 0.0
        
        metrics = TurnoverMetrics(
            date=date,
            portfolio_turnover=portfolio_turnover,
            buy_turnover=buy_turnover,
            sell_turnover=sell_turnover,
            trade_count=trade_count,
            traded_value=traded_value,
            portfolio_value=portfolio_value
        )
        
        self._turnover_history.append(metrics)
    
    def check_turnover_constraints(
        self,
        current_date: Optional[date] = None
    ) -> TurnoverCheckResult:
        """
        检查换手率约束
        
        Args:
            current_date: 当前日期（可选）
            
        Returns:
            TurnoverCheckResult: 检查结果
        """
        if not self._turnover_history:
            return TurnoverCheckResult(
                passed=True,
                current_turnover=0.0,
                max_turnover=self.max_daily_turnover,
                avg_turnover=0.0,
                turnover_trend="unknown",
                message="无换手率数据"
            )
        
        latest = self._turnover_history[-1]
        current_turnover = latest.portfolio_turnover
        
        if current_turnover > self.max_daily_turnover:
            return TurnoverCheckResult(
                passed=False,
                current_turnover=current_turnover,
                max_turnover=self.max_daily_turnover,
                avg_turnover=np.mean([m.portfolio_turnover for m in self._turnover_history]),
                turnover_trend="excessive",
                message=f"日换手率超标: {current_turnover:.1%} > {self.max_daily_turnover:.1%}"
            )
        
        if len(self._turnover_history) >= 20:
            recent_20d = self._turnover_history[-20:]
            monthly_turnover = sum(m.portfolio_turnover for m in recent_20d)
            
            if monthly_turnover > self.max_monthly_turnover:
                return TurnoverCheckResult(
                    passed=False,
                    current_turnover=current_turnover,
                    max_turnover=self.max_monthly_turnover,
                    avg_turnover=np.mean([m.portfolio_turnover for m in recent_20d]),
                    turnover_trend="high",
                    message=f"月换手率超标: {monthly_turnover:.1%} > {self.max_monthly_turnover:.1%}"
                )
        
        if len(self._turnover_history) >= 252:
            annual_turnover = sum(m.portfolio_turnover for m in self._turnover_history[-252:])
            
            if annual_turnover > self.max_annual_turnover:
                return TurnoverCheckResult(
                    passed=False,
                    current_turnover=current_turnover,
                    max_turnover=self.max_annual_turnover,
                    avg_turnover=np.mean([m.portfolio_turnover for m in self._turnover_history[-252:]]),
                    turnover_trend="very_high",
                    message=f"年换手率超标: {annual_turnover:.1%} > {self.max_annual_turnover:.1%}"
                )
        
        warnings = []
        if current_turnover > self.max_daily_turnover * self.warning_threshold:
            warnings.append(f"日换手率接近上限: {current_turnover:.1%}")
        
        if len(self._turnover_history) >= 5:
            recent_5d = [m.portfolio_turnover for m in self._turnover_history[-5:]]
            if np.mean(recent_5d) > self.max_daily_turnover * self.warning_threshold:
                warnings.append("近期平均换手率偏高")
        
        turnover_trend = "normal"
        if len(self._turnover_history) >= 10:
            recent_10d = [m.portfolio_turnover for m in self._turnover_history[-10:]]
            earlier_10d = [m.portfolio_turnover for m in self._turnover_history[-20:-10]] if len(self._turnover_history) >= 20 else []
            
            if earlier_10d:
                recent_avg = np.mean(recent_10d)
                earlier_avg = np.mean(earlier_10d)
                
                if recent_avg > earlier_avg * 1.5:
                    turnover_trend = "increasing"
                    warnings.append("换手率呈上升趋势")
                elif recent_avg < earlier_avg * 0.67:
                    turnover_trend = "decreasing"
        
        return TurnoverCheckResult(
            passed=True,
            current_turnover=current_turnover,
            max_turnover=self.max_daily_turnover,
            avg_turnover=np.mean([m.portfolio_turnover for m in self._turnover_history]),
            turnover_trend=turnover_trend,
            message="换手率检查通过",
            warnings=warnings
        )
    
    def get_turnover_statistics(self) -> Dict[str, Any]:
        """获取换手率统计"""
        if not self._turnover_history:
            return {'message': '无换手率数据'}
        
        turnovers = [m.portfolio_turnover for m in self._turnover_history]
        
        return {
            'total_days': len(self._turnover_history),
            'avg_daily_turnover': np.mean(turnovers),
            'median_daily_turnover': np.median(turnovers),
            'max_daily_turnover': np.max(turnovers),
            'min_daily_turnover': np.min(turnovers),
            'std_daily_turnover': np.std(turnovers),
            'total_turnover': sum(turnovers),
            'avg_trade_count': np.mean([m.trade_count for m in self._turnover_history])
        }
    
    def clear_history(self):
        """清除历史记录"""
        self._turnover_history.clear()


@dataclass
class OverfittingCheckResult:
    """过拟合检查结果"""
    is_overfitted: bool
    train_test_gap: float
    parameter_sensitivity: float
    complexity_score: float
    cross_validation_score: float
    warnings: List[str]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'is_overfitted': self.is_overfitted,
            'train_test_gap': self.train_test_gap,
            'parameter_sensitivity': self.parameter_sensitivity,
            'complexity_score': self.complexity_score,
            'cross_validation_score': self.cross_validation_score,
            'warnings': self.warnings,
            'recommendations': self.recommendations
        }


class OverfittingDetector:
    """
    过拟合检测器
    
    检测策略/因子是否过拟合。
    """
    
    def __init__(
        self,
        train_test_gap_threshold: float = 0.3,
        sensitivity_threshold: float = 0.5,
        complexity_threshold: float = 0.7
    ):
        """
        初始化过拟合检测器
        
        Args:
            train_test_gap_threshold: 训练测试差距阈值
            sensitivity_threshold: 参数敏感性阈值
            complexity_threshold: 复杂度阈值
        """
        self.train_test_gap_threshold = train_test_gap_threshold
        self.sensitivity_threshold = sensitivity_threshold
        self.complexity_threshold = complexity_threshold
    
    def detect_overfitting(
        self,
        train_metrics: Dict[str, float],
        test_metrics: Dict[str, float],
        parameter_variations: Optional[List[Dict[str, float]]] = None,
        cross_val_scores: Optional[List[float]] = None
    ) -> OverfittingCheckResult:
        """
        检测过拟合
        
        Args:
            train_metrics: 训练集指标
            test_metrics: 测试集指标
            parameter_variations: 参数变化结果
            cross_val_scores: 交叉验证分数
            
        Returns:
            OverfittingCheckResult: 检测结果
        """
        warnings = []
        recommendations = []
        
        train_ic = train_metrics.get('ic_mean', 0.0)
        test_ic = test_metrics.get('ic_mean', 0.0)
        
        if abs(train_ic) > 1e-6:
            train_test_gap = abs(train_ic - test_ic) / abs(train_ic)
        else:
            train_test_gap = 0.0
        
        if train_test_gap > self.train_test_gap_threshold:
            warnings.append(f"训练测试差距过大: {train_test_gap:.1%}")
            recommendations.append("考虑简化模型或增加正则化")
        
        parameter_sensitivity = 0.0
        if parameter_variations and len(parameter_variations) > 1:
            ics = [v.get('ic_mean', 0.0) for v in parameter_variations]
            if len(ics) > 1:
                ic_std = np.std(ics)
                ic_mean = np.mean(np.abs(ics))
                parameter_sensitivity = ic_std / (ic_mean + 1e-6)
                
                if parameter_sensitivity > self.sensitivity_threshold:
                    warnings.append(f"参数敏感性过高: {parameter_sensitivity:.2f}")
                    recommendations.append("参数微调导致性能剧变，可能过拟合")
        
        complexity_score = 0.0
        factor_count = train_metrics.get('factor_count', 1)
        if factor_count > 10:
            complexity_score = min((factor_count - 10) / 20, 1.0)
            if complexity_score > self.complexity_threshold:
                warnings.append(f"模型复杂度过高: {factor_count} 个因子")
                recommendations.append("减少因子数量，避免过拟合")
        
        cross_validation_score = 0.0
        if cross_val_scores and len(cross_val_scores) > 1:
            cross_validation_score = 1 - (np.std(cross_val_scores) / (np.mean(np.abs(cross_val_scores)) + 1e-6))
            
            if cross_validation_score < 0.5:
                warnings.append(f"交叉验证不稳定: {cross_validation_score:.2f}")
                recommendations.append("不同数据子集表现差异大")
        
        is_overfitted = (
            train_test_gap > self.train_test_gap_threshold or
            parameter_sensitivity > self.sensitivity_threshold or
            complexity_score > self.complexity_threshold
        )
        
        if not warnings:
            recommendations.append("未检测到明显过拟合")
        
        return OverfittingCheckResult(
            is_overfitted=is_overfitted,
            train_test_gap=train_test_gap,
            parameter_sensitivity=parameter_sensitivity,
            complexity_score=complexity_score,
            cross_validation_score=cross_validation_score,
            warnings=warnings,
            recommendations=recommendations
        )
    
    def perform_sensitivity_analysis(
        self,
        base_params: Dict[str, Any],
        param_ranges: Dict[str, List[Any]],
        backtest_func: callable,
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        执行参数敏感性分析
        
        Args:
            base_params: 基准参数
            param_ranges: 参数范围
            backtest_func: 回测函数
            factor_df: 因子数据
            return_df: 收益数据
            
        Returns:
            Dict: 敏感性分析结果
        """
        results = []
        
        for param_name, param_values in param_ranges.items():
            for param_value in param_values:
                test_params = base_params.copy()
                test_params[param_name] = param_value
                
                try:
                    backtest_result = backtest_func(factor_df, return_df, test_params)
                    results.append({
                        'param_name': param_name,
                        'param_value': param_value,
                        'ic_mean': backtest_result.get('ic_mean', 0.0),
                        'sharpe_ratio': backtest_result.get('sharpe_ratio', 0.0)
                    })
                except Exception as e:
                    logger.warning(f"参数 {param_name}={param_value} 回测失败: {e}")
        
        sensitivity_report = {}
        for param_name in param_ranges.keys():
            param_results = [r for r in results if r['param_name'] == param_name]
            
            if param_results:
                ics = [r['ic_mean'] for r in param_results]
                sharpes = [r['sharpe_ratio'] for r in param_results]
                
                sensitivity_report[param_name] = {
                    'ic_range': (min(ics), max(ics)),
                    'ic_std': np.std(ics),
                    'sharpe_range': (min(sharpes), max(sharpes)),
                    'sharpe_std': np.std(sharpes),
                    'sensitivity': np.std(ics) / (np.mean(np.abs(ics)) + 1e-6)
                }
        
        return {
            'results': results,
            'sensitivity_report': sensitivity_report,
            'overall_sensitivity': np.mean([s['sensitivity'] for s in sensitivity_report.values()])
        }


def create_turnover_checker(
    max_daily_turnover: float = 0.3,
    max_annual_turnover: float = 10.0
) -> TurnoverConstraintChecker:
    """创建换手率约束检查器"""
    return TurnoverConstraintChecker(
        max_daily_turnover=max_daily_turnover,
        max_annual_turnover=max_annual_turnover
    )


def create_overfitting_detector(
    train_test_gap_threshold: float = 0.3
) -> OverfittingDetector:
    """创建过拟合检测器"""
    return OverfittingDetector(train_test_gap_threshold=train_test_gap_threshold)
