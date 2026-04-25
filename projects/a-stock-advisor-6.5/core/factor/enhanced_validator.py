"""
增强版因子验证器

实现严格的因子验证标准，包括：
- 多维度验证（IC/IR/单调性/稳定性/样本外）
- 无效分数检测与处理
- 回测参数记录与复测
- 验证报告生成
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

import pandas as pd
import numpy as np
from scipy import stats

from .registry import (
    FactorMetadata, 
    FactorQualityMetrics, 
    BacktestResult,
    ValidationStatus,
    get_factor_registry
)
from .validator import ICAnalyzer, ValidationResult
from .backtester import (
    FactorBacktester,
    FactorBacktestResult,
    MarketType,
    HoldingPeriod,
    BacktestCredibility
)

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """验证等级"""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"
    COMPREHENSIVE = "comprehensive"


@dataclass
class ValidationThreshold:
    """验证阈值配置"""
    ic_min: float = 0.02
    ic_excellent: float = 0.05
    ir_min: float = 0.25
    ir_excellent: float = 0.5
    t_stat_min: float = 1.65
    t_stat_strong: float = 2.58
    monotonicity_min: float = 0.5
    monotonicity_strong: float = 0.8
    win_rate_min: float = 0.52
    coverage_min: int = 100
    trading_days_min: int = 100
    oos_decay_max: float = 0.3


@dataclass
class InvalidScoreIssue:
    """无效分数问题"""
    issue_type: str
    description: str
    severity: str
    detected_value: Any
    expected_range: Tuple[float, float]
    recommendation: str


@dataclass
class EnhancedValidationResult:
    """增强版验证结果"""
    factor_id: str
    factor_name: str
    validation_level: ValidationLevel
    passed: bool
    overall_score: float
    grade: str
    
    ic_metrics: Dict[str, float]
    stability_metrics: Dict[str, float]
    monotonicity_metrics: Dict[str, float]
    coverage_metrics: Dict[str, float]
    oos_metrics: Dict[str, float]
    
    issues: List[InvalidScoreIssue]
    warnings: List[str]
    recommendations: List[str]
    
    backtest_params: Dict[str, Any]
    validation_timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "factor_name": self.factor_name,
            "validation_level": self.validation_level.value,
            "passed": self.passed,
            "overall_score": self.overall_score,
            "grade": self.grade,
            "ic_metrics": self.ic_metrics,
            "stability_metrics": self.stability_metrics,
            "monotonicity_metrics": self.monotonicity_metrics,
            "coverage_metrics": self.coverage_metrics,
            "oos_metrics": self.oos_metrics,
            "issues": [
                {
                    "type": i.issue_type,
                    "description": i.description,
                    "severity": i.severity,
                    "detected_value": i.detected_value,
                    "expected_range": i.expected_range,
                    "recommendation": i.recommendation
                } for i in self.issues
            ],
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "backtest_params": self.backtest_params,
            "validation_timestamp": self.validation_timestamp
        }


class EnhancedFactorValidator:
    """
    增强版因子验证器
    
    实现严格的因子验证流程：
    1. 基础验证：数据质量、覆盖率
    2. IC验证：均值、标准差、显著性
    3. 稳定性验证：IR、时间一致性
    4. 单调性验证：分组收益单调性
    5. 样本外验证：训练/测试分割
    6. 无效分数检测：异常值、偏差
    """
    
    THRESHOLDS = {
        ValidationLevel.BASIC: ValidationThreshold(
            ic_min=0.01, ir_min=0.15, t_stat_min=1.0,
            monotonicity_min=0.4, coverage_min=50, trading_days_min=50
        ),
        ValidationLevel.STANDARD: ValidationThreshold(
            ic_min=0.02, ir_min=0.25, t_stat_min=1.65,
            monotonicity_min=0.5, coverage_min=100, trading_days_min=100
        ),
        ValidationLevel.STRICT: ValidationThreshold(
            ic_min=0.03, ir_min=0.35, t_stat_min=1.96,
            monotonicity_min=0.6, coverage_min=200, trading_days_min=200
        ),
        ValidationLevel.COMPREHENSIVE: ValidationThreshold(
            ic_min=0.04, ir_min=0.5, t_stat_min=2.58,
            monotonicity_min=0.7, coverage_min=300, trading_days_min=250,
            oos_decay_max=0.2
        )
    }
    
    def __init__(
        self,
        validation_level: ValidationLevel = ValidationLevel.STANDARD,
        registry=None
    ):
        self.validation_level = validation_level
        self.threshold = self.THRESHOLDS[validation_level]
        self._registry = registry or get_factor_registry()
        self._backtester = FactorBacktester()
    
    def validate_factor(
        self,
        factor_id: str,
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        price_df: Optional[pd.DataFrame] = None,
        stock_pool: str = "全市场",
        enable_oos: bool = True,
        train_ratio: float = 0.7
    ) -> EnhancedValidationResult:
        """
        执行增强版因子验证
        
        Args:
            factor_id: 因子ID
            factor_df: 因子数据
            return_df: 收益数据
            price_df: 价格数据（用于交易约束）
            stock_pool: 股票池名称
            enable_oos: 是否启用样本外验证
            train_ratio: 训练集比例
            
        Returns:
            EnhancedValidationResult: 验证结果
        """
        factor = self._registry.get(factor_id)
        factor_name = factor.name if factor else factor_id
        
        issues: List[InvalidScoreIssue] = []
        warnings: List[str] = []
        recommendations: List[str] = []
        
        ic_metrics = {}
        stability_metrics = {}
        monotonicity_metrics = {}
        coverage_metrics = {}
        oos_metrics = {}
        
        backtest_params = {
            "stock_pool": stock_pool,
            "enable_oos": enable_oos,
            "train_ratio": train_ratio,
            "validation_level": self.validation_level.value,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            factor_col = "factor_value"
            return_col = "forward_return"
            date_col = "date"
            stock_col = "stock_code"
            
            coverage_metrics = self._validate_coverage(
                factor_df, factor_col, date_col, stock_col, issues
            )
            
            ic_series = ICAnalyzer.calculate_ic_series(
                factor_df, return_df, factor_col, return_col, date_col, stock_col
            )
            ic_result = ICAnalyzer.analyze_ic(ic_series)
            
            ic_metrics = self._validate_ic(ic_result, issues, warnings)
            
            stability_metrics = self._validate_stability(
                ic_series, ic_result, issues, warnings
            )
            
            monotonicity_metrics = self._validate_monotonicity(
                factor_df, return_df, factor_col, return_col, date_col, stock_col, issues
            )
            
            if enable_oos:
                oos_metrics = self._validate_oos(
                    factor_df, return_df, factor_col, return_col, date_col, stock_col,
                    train_ratio, issues, warnings
                )
            
            invalid_issues = self._detect_invalid_scores(
                factor_df, factor_col, ic_metrics, stability_metrics, issues
            )
            issues.extend(invalid_issues)
            
            overall_score, grade = self._calculate_overall_score(
                ic_metrics, stability_metrics, monotonicity_metrics, coverage_metrics, oos_metrics
            )
            
            passed = self._determine_pass(issues, overall_score)
            
            recommendations = self._generate_recommendations(issues, warnings)
            
        except Exception as e:
            logger.error(f"验证因子 {factor_id} 失败: {e}")
            issues.append(InvalidScoreIssue(
                issue_type="validation_error",
                description=f"验证过程出错: {str(e)}",
                severity="critical",
                detected_value=str(e),
                expected_range=(None, None),
                recommendation="检查数据格式和完整性"
            ))
            passed = False
            overall_score = 0.0
            grade = "F"
        
        return EnhancedValidationResult(
            factor_id=factor_id,
            factor_name=factor_name,
            validation_level=self.validation_level,
            passed=passed,
            overall_score=overall_score,
            grade=grade,
            ic_metrics=ic_metrics,
            stability_metrics=stability_metrics,
            monotonicity_metrics=monotonicity_metrics,
            coverage_metrics=coverage_metrics,
            oos_metrics=oos_metrics,
            issues=issues,
            warnings=warnings,
            recommendations=recommendations,
            backtest_params=backtest_params,
            validation_timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    
    def _validate_coverage(
        self,
        factor_df: pd.DataFrame,
        factor_col: str,
        date_col: str,
        stock_col: str,
        issues: List[InvalidScoreIssue]
    ) -> Dict[str, float]:
        """验证覆盖率"""
        coverage_metrics = {}
        
        total_rows = len(factor_df)
        unique_stocks = factor_df[stock_col].nunique()
        unique_dates = factor_df[date_col].nunique()
        nan_ratio = factor_df[factor_col].isna().sum() / total_rows if total_rows > 0 else 1.0
        
        coverage_metrics["total_rows"] = total_rows
        coverage_metrics["unique_stocks"] = unique_stocks
        coverage_metrics["unique_dates"] = unique_dates
        coverage_metrics["nan_ratio"] = nan_ratio
        
        if unique_stocks < self.threshold.coverage_min:
            issues.append(InvalidScoreIssue(
                issue_type="coverage_stocks",
                description=f"股票覆盖不足: {unique_stocks} < {self.threshold.coverage_min}",
                severity="high",
                detected_value=unique_stocks,
                expected_range=(self.threshold.coverage_min, float('inf')),
                recommendation="扩大股票池或延长回测周期"
            ))
        
        if unique_dates < self.threshold.trading_days_min:
            issues.append(InvalidScoreIssue(
                issue_type="coverage_dates",
                description=f"交易日覆盖不足: {unique_dates} < {self.threshold.trading_days_min}",
                severity="high",
                detected_value=unique_dates,
                expected_range=(self.threshold.trading_days_min, float('inf')),
                recommendation="延长回测时间周期"
            ))
        
        if nan_ratio > 0.3:
            issues.append(InvalidScoreIssue(
                issue_type="data_quality",
                description=f"缺失值比例过高: {nan_ratio:.1%}",
                severity="medium",
                detected_value=nan_ratio,
                expected_range=(0.0, 0.3),
                recommendation="检查数据源质量或因子计算逻辑"
            ))
        
        return coverage_metrics
    
    def _validate_ic(
        self,
        ic_result,
        issues: List[InvalidScoreIssue],
        warnings: List[str]
    ) -> Dict[str, float]:
        """验证IC指标"""
        ic_metrics = {
            "ic_mean": ic_result.ic_mean,
            "ic_std": ic_result.ic_std,
            "ic_ir": ic_result.ic_ir,
            "ic_positive_ratio": ic_result.ic_positive_ratio,
            "ic_t_stat": ic_result.ic_t_stat,
            "ic_p_value": ic_result.ic_p_value
        }
        
        if abs(ic_result.ic_mean) < self.threshold.ic_min:
            issues.append(InvalidScoreIssue(
                issue_type="ic_too_low",
                description=f"IC均值过低: {abs(ic_result.ic_mean):.4f} < {self.threshold.ic_min}",
                severity="critical",
                detected_value=ic_result.ic_mean,
                expected_range=(self.threshold.ic_min, 1.0),
                recommendation="因子预测能力不足，考虑改进或放弃"
            ))
        
        if abs(ic_result.ic_t_stat) < self.threshold.t_stat_min:
            issues.append(InvalidScoreIssue(
                issue_type="ic_not_significant",
                description=f"IC不显著: t={abs(ic_result.ic_t_stat):.2f} < {self.threshold.t_stat_min}",
                severity="high",
                detected_value=ic_result.ic_t_stat,
                expected_range=(self.threshold.t_stat_min, float('inf')),
                recommendation="增加样本量或检查因子有效性"
            ))
        
        if ic_result.ic_positive_ratio < 0.5:
            warnings.append(f"IC正比例偏低: {ic_result.ic_positive_ratio:.1%}")
        
        return ic_metrics
    
    def _validate_stability(
        self,
        ic_series: pd.Series,
        ic_result,
        issues: List[InvalidScoreIssue],
        warnings: List[str]
    ) -> Dict[str, float]:
        """验证稳定性"""
        stability_metrics = {
            "ir": ic_result.ic_ir,
            "ic_std": ic_result.ic_std
        }
        
        if abs(ic_result.ic_ir) < self.threshold.ir_min:
            issues.append(InvalidScoreIssue(
                issue_type="ir_too_low",
                description=f"IR过低: {abs(ic_result.ic_ir):.3f} < {self.threshold.ir_min}",
                severity="high",
                detected_value=ic_result.ic_ir,
                expected_range=(self.threshold.ir_min, float('inf')),
                recommendation="因子稳定性不足，检查时间一致性"
            ))
        
        ic_std = ic_result.ic_std
        ic_mean = abs(ic_result.ic_mean)
        if ic_std > ic_mean * 3:
            warnings.append(f"IC波动较大: std/mean = {ic_std/ic_mean:.1f}")
        
        return stability_metrics
    
    def _validate_monotonicity(
        self,
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        factor_col: str,
        return_col: str,
        date_col: str,
        stock_col: str,
        issues: List[InvalidScoreIssue]
    ) -> Dict[str, float]:
        """验证单调性"""
        from .validator import MonotonicityAnalyzer
        
        monotonicity, group_returns = MonotonicityAnalyzer.calculate_monotonicity(
            factor_df, return_df, 5, factor_col, return_col, date_col, stock_col
        )
        
        monotonicity_metrics = {
            "monotonicity": monotonicity,
            "group_returns": group_returns.to_dict() if not group_returns.empty else {}
        }
        
        if monotonicity < self.threshold.monotonicity_min:
            issues.append(InvalidScoreIssue(
                issue_type="monotonicity_weak",
                description=f"单调性不足: {monotonicity:.2f} < {self.threshold.monotonicity_min}",
                severity="medium",
                detected_value=monotonicity,
                expected_range=(self.threshold.monotonicity_min, 1.0),
                recommendation="检查因子方向或分组逻辑"
            ))
        
        return monotonicity_metrics
    
    def _validate_oos(
        self,
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        factor_col: str,
        return_col: str,
        date_col: str,
        stock_col: str,
        train_ratio: float,
        issues: List[InvalidScoreIssue],
        warnings: List[str]
    ) -> Dict[str, float]:
        """样本外验证"""
        oos_metrics = {}
        
        try:
            dates = sorted(factor_df[date_col].unique())
            split_idx = int(len(dates) * train_ratio)
            train_dates = dates[:split_idx]
            test_dates = dates[split_idx:]
            
            train_factor = factor_df[factor_df[date_col].isin(train_dates)]
            test_factor = factor_df[factor_df[date_col].isin(test_dates)]
            train_return = return_df[return_df[date_col].isin(train_dates)]
            test_return = return_df[return_df[date_col].isin(test_dates)]
            
            train_ic_series = ICAnalyzer.calculate_ic_series(
                train_factor, train_return, factor_col, return_col, date_col, stock_col
            )
            test_ic_series = ICAnalyzer.calculate_ic_series(
                test_factor, test_return, factor_col, return_col, date_col, stock_col
            )
            
            train_ic = train_ic_series.mean()
            test_ic = test_ic_series.mean()
            
            if abs(train_ic) > 0:
                ic_decay = abs(train_ic - test_ic) / abs(train_ic)
            else:
                ic_decay = 1.0
            
            oos_metrics = {
                "train_ic": train_ic,
                "test_ic": test_ic,
                "ic_decay_rate": ic_decay,
                "train_dates": len(train_dates),
                "test_dates": len(test_dates)
            }
            
            if ic_decay > self.threshold.oos_decay_max:
                issues.append(InvalidScoreIssue(
                    issue_type="oos_decay",
                    description=f"样本外IC衰减严重: {ic_decay:.1%} > {self.threshold.oos_decay_max:.1%}",
                    severity="high",
                    detected_value=ic_decay,
                    expected_range=(0.0, self.threshold.oos_decay_max),
                    recommendation="可能存在过拟合，需要简化因子或增加正则化"
                ))
            
            if abs(test_ic) < self.threshold.ic_min:
                warnings.append(f"样本外IC不达标: {abs(test_ic):.4f}")
            
        except Exception as e:
            warnings.append(f"样本外验证失败: {str(e)}")
        
        return oos_metrics
    
    def _detect_invalid_scores(
        self,
        factor_df: pd.DataFrame,
        factor_col: str,
        ic_metrics: Dict[str, float],
        stability_metrics: Dict[str, float],
        issues: List[InvalidScoreIssue]
    ) -> List[InvalidScoreIssue]:
        """检测无效分数"""
        invalid_issues = []
        
        factor_values = factor_df[factor_col].dropna()
        
        if len(factor_values) > 0:
            mean_val = factor_values.mean()
            std_val = factor_values.std()
            
            if std_val == 0:
                invalid_issues.append(InvalidScoreIssue(
                    issue_type="constant_factor",
                    description="因子值为常数，无区分度",
                    severity="critical",
                    detected_value=mean_val,
                    expected_range=(None, None),
                    recommendation="检查因子计算逻辑"
                ))
            
            skewness = factor_values.skew()
            if abs(skewness) > 3:
                invalid_issues.append(InvalidScoreIssue(
                    issue_type="extreme_skewness",
                    description=f"因子分布极度偏斜: skewness={skewness:.2f}",
                    severity="medium",
                    detected_value=skewness,
                    expected_range=(-3.0, 3.0),
                    recommendation="考虑对因子进行标准化或Winsorize处理"
                ))
            
            kurtosis = factor_values.kurtosis()
            if kurtosis > 10:
                invalid_issues.append(InvalidScoreIssue(
                    issue_type="extreme_kurtosis",
                    description=f"因子分布存在极端值: kurtosis={kurtosis:.2f}",
                    severity="medium",
                    detected_value=kurtosis,
                    expected_range=(-3.0, 10.0),
                    recommendation="检查异常值或进行截断处理"
                ))
        
        ic_mean = ic_metrics.get("ic_mean", 0)
        ic_std = stability_metrics.get("ic_std", 0)
        
        if abs(ic_mean) > 0.15:
            invalid_issues.append(InvalidScoreIssue(
                issue_type="suspicious_ic",
                description=f"IC值异常高: {abs(ic_mean):.4f}，可能存在数据泄露",
                severity="critical",
                detected_value=ic_mean,
                expected_range=(0.0, 0.15),
                recommendation="检查是否存在未来函数或数据泄露"
            ))
        
        return invalid_issues
    
    def _calculate_overall_score(
        self,
        ic_metrics: Dict[str, float],
        stability_metrics: Dict[str, float],
        monotonicity_metrics: Dict[str, float],
        coverage_metrics: Dict[str, float],
        oos_metrics: Dict[str, float]
    ) -> Tuple[float, str]:
        """计算综合评分"""
        score = 0.0
        
        ic_score = min(abs(ic_metrics.get("ic_mean", 0)) / 0.05 * 30, 30)
        ir_score = min(abs(stability_metrics.get("ir", 0)) / 0.5 * 20, 20)
        t_score = min(abs(ic_metrics.get("ic_t_stat", 0)) / 2.58 * 15, 15)
        mono_score = monotonicity_metrics.get("monotonicity", 0) * 15
        
        coverage_score = 0
        if coverage_metrics.get("unique_stocks", 0) >= self.threshold.coverage_min:
            coverage_score += 5
        if coverage_metrics.get("unique_dates", 0) >= self.threshold.trading_days_min:
            coverage_score += 5
        
        oos_score = 0
        if oos_metrics:
            decay = oos_metrics.get("ic_decay_rate", 1)
            if decay < 0.2:
                oos_score = 10
            elif decay < 0.3:
                oos_score = 5
        
        score = ic_score + ir_score + t_score + mono_score + coverage_score + oos_score
        
        if score >= 85:
            grade = "A"
        elif score >= 70:
            grade = "B+"
        elif score >= 55:
            grade = "B"
        elif score >= 40:
            grade = "C"
        else:
            grade = "D"
        
        return score, grade
    
    def _determine_pass(self, issues: List[InvalidScoreIssue], score: float) -> bool:
        """判定是否通过"""
        critical_issues = [i for i in issues if i.severity == "critical"]
        high_issues = [i for i in issues if i.severity == "high"]
        
        if len(critical_issues) > 0:
            return False
        
        if len(high_issues) > 2:
            return False
        
        if score < 40:
            return False
        
        return True
    
    def _generate_recommendations(
        self,
        issues: List[InvalidScoreIssue],
        warnings: List[str]
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        for issue in issues:
            if issue.recommendation not in recommendations:
                recommendations.append(issue.recommendation)
        
        if len(warnings) > 3:
            recommendations.append("存在多个警告，建议全面检查因子质量")
        
        return recommendations


class BacktestParameterRecorder:
    """
    回测参数记录器
    
    记录每次回测的完整参数，支持复测。
    """
    
    @staticmethod
    def record_backtest_params(
        factor_id: str,
        backtest_result: FactorBacktestResult,
        stock_pool: str = "全市场",
        n_stocks: int = 0,
        enable_oos: bool = False,
        train_ratio: float = 0.7
    ) -> BacktestResult:
        """
        记录回测参数到BacktestResult
        
        Args:
            factor_id: 因子ID
            backtest_result: 回测结果
            stock_pool: 股票池
            n_stocks: 股票数量
            enable_oos: 是否启用样本外验证
            train_ratio: 训练集比例
            
        Returns:
            BacktestResult: 包含参数的回测结果
        """
        credibility = backtest_result.credibility
        
        result = BacktestResult(
            annual_return=backtest_result.spread_return * 50,
            sharpe_ratio=backtest_result.ic_statistics.ic_ir if backtest_result.ic_statistics else 0,
            max_drawdown=0,
            win_rate=backtest_result.ic_statistics.ic_positive_ratio if backtest_result.ic_statistics else 0,
            ic=backtest_result.ic_mean,
            start_date=None,
            end_date=None,
            stock_pool=stock_pool,
            n_stocks=n_stocks,
            n_groups=backtest_result.n_groups,
            holding_period=backtest_result.holding_period.value if backtest_result.holding_period else 5,
            market_type=backtest_result.market_type.value if backtest_result.market_type else "all_market",
            enable_oos=enable_oos,
            train_ratio=train_ratio,
            transaction_costs=True,
            credibility_score=credibility.total_score if credibility else 0,
            oos_valid=backtest_result.oos_validation.is_valid if backtest_result.oos_validation else False,
            backtest_version="v2.0"
        )
        
        return result
    
    @staticmethod
    def get_retest_params(
        registry,
        factor_id: str,
        stock_pool: str = "全市场"
    ) -> Optional[Dict[str, Any]]:
        """
        获取复测参数
        
        Args:
            registry: 因子注册表
            factor_id: 因子ID
            stock_pool: 股票池
            
        Returns:
            Optional[Dict]: 复测参数
        """
        factor = registry.get(factor_id)
        if not factor:
            return None
        
        backtest_result = factor.backtest_results.get(stock_pool)
        if not backtest_result:
            return None
        
        return {
            "factor_id": factor_id,
            "stock_pool": backtest_result.stock_pool,
            "n_stocks": backtest_result.n_stocks,
            "n_groups": backtest_result.n_groups,
            "holding_period": backtest_result.holding_period,
            "market_type": backtest_result.market_type,
            "enable_oos": backtest_result.enable_oos,
            "train_ratio": backtest_result.train_ratio,
            "transaction_costs": backtest_result.transaction_costs,
            "backtest_version": backtest_result.backtest_version
        }


def get_enhanced_validator(
    validation_level: ValidationLevel = ValidationLevel.STANDARD
) -> EnhancedFactorValidator:
    """获取增强版验证器实例"""
    return EnhancedFactorValidator(validation_level=validation_level)
