"""
因子验证器模块

验证因子预测能力和稳定性，包括IC/IR/单调性/相关性等指标计算。
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import numpy as np
from scipy import stats

from .registry import FactorMetadata, FactorQualityMetrics, get_factor_registry
from ..infrastructure.exceptions import FactorException


@dataclass
class ValidationResult:
    """验证结果"""
    success: bool
    factor_id: str
    metrics: Optional[FactorQualityMetrics] = None
    details: Dict[str, Any] = None
    error_message: Optional[str] = None


@dataclass
class ICAnalysisResult:
    """IC分析结果"""
    ic_series: pd.Series
    ic_mean: float
    ic_std: float
    ic_ir: float
    ic_positive_ratio: float
    ic_t_stat: float
    ic_p_value: float


class ICAnalyzer:
    """
    IC分析器
    
    计算因子的信息系数（Information Coefficient）及其相关统计量。
    """
    
    @staticmethod
    def calculate_ic(
        factor_values: pd.Series,
        forward_returns: pd.Series,
        method: str = "spearman"
    ) -> float:
        """
        计算单期IC
        
        Args:
            factor_values: 因子值序列
            forward_returns: 未来收益序列
            method: 相关系数方法 ('spearman' 或 'pearson')
            
        Returns:
            float: IC值
        """
        valid_mask = ~(factor_values.isna() | forward_returns.isna())
        factor_clean = factor_values[valid_mask]
        returns_clean = forward_returns[valid_mask]
        
        if len(factor_clean) < 10:
            return np.nan
        
        if method == "spearman":
            ic, _ = stats.spearmanr(factor_clean, returns_clean)
        else:
            ic, _ = stats.pearsonr(factor_clean, returns_clean)
        
        return ic
    
    @staticmethod
    def calculate_ic_series(
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        factor_col: str = "factor_value",
        return_col: str = "forward_return",
        date_col: str = "date",
        stock_col: str = "stock_code",
        method: str = "spearman"
    ) -> pd.Series:
        """
        计算IC时间序列
        
        Args:
            factor_df: 因子数据
            return_df: 收益数据
            factor_col: 因子值列名
            return_col: 收益列名
            date_col: 日期列名
            stock_col: 股票代码列名
            method: 相关系数方法
            
        Returns:
            pd.Series: IC时间序列
        """
        merged = pd.merge(
            factor_df[[date_col, stock_col, factor_col]],
            return_df[[date_col, stock_col, return_col]],
            on=[date_col, stock_col],
            how="inner"
        )
        
        ic_series = merged.groupby(date_col).apply(
            lambda g: ICAnalyzer.calculate_ic(
                g[factor_col], 
                g[return_col], 
                method
            )
        )
        
        return ic_series
    
    @staticmethod
    def analyze_ic(ic_series: pd.Series) -> ICAnalysisResult:
        """
        分析IC序列
        
        Args:
            ic_series: IC时间序列
            
        Returns:
            ICAnalysisResult: IC分析结果
        """
        ic_clean = ic_series.dropna()
        
        if len(ic_clean) == 0:
            return ICAnalysisResult(
                ic_series=ic_series,
                ic_mean=0.0,
                ic_std=0.0,
                ic_ir=0.0,
                ic_positive_ratio=0.0,
                ic_t_stat=0.0,
                ic_p_value=1.0
            )
        
        ic_mean = ic_clean.mean()
        ic_std = ic_clean.std()
        ic_ir = ic_mean / ic_std if ic_std > 0 else 0.0
        
        ic_positive_ratio = (ic_clean > 0).sum() / len(ic_clean)
        
        t_stat, p_value = stats.ttest_1samp(ic_clean, 0)
        
        return ICAnalysisResult(
            ic_series=ic_series,
            ic_mean=ic_mean,
            ic_std=ic_std,
            ic_ir=ic_ir,
            ic_positive_ratio=ic_positive_ratio,
            ic_t_stat=t_stat,
            ic_p_value=p_value
        )


class MonotonicityAnalyzer:
    """
    单调性分析器
    
    分析因子值与收益之间的单调关系。
    """
    
    @staticmethod
    def calculate_monotonicity(
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        n_groups: int = 5,
        factor_col: str = "factor_value",
        return_col: str = "forward_return",
        date_col: str = "date",
        stock_col: str = "stock_code"
    ) -> Tuple[float, pd.DataFrame]:
        """
        计算因子单调性
        
        Args:
            factor_df: 因子数据
            return_df: 收益数据
            n_groups: 分组数量
            factor_col: 因子值列名
            return_col: 收益列名
            date_col: 日期列名
            stock_col: 股票代码列名
            
        Returns:
            Tuple[float, pd.DataFrame]: 单调性得分和分组收益
        """
        merged = pd.merge(
            factor_df[[date_col, stock_col, factor_col]],
            return_df[[date_col, stock_col, return_col]],
            on=[date_col, stock_col],
            how="inner"
        )
        
        def calc_group_returns(group):
            group[factor_col] = pd.to_numeric(group[factor_col], errors='coerce')
            group = group.dropna(subset=[factor_col, return_col])
            
            if len(group) < n_groups:
                return pd.Series()
            
            group['factor_group'] = pd.qcut(
                group[factor_col], 
                n_groups, 
                labels=False, 
                duplicates='drop'
            )
            
            return group.groupby('factor_group')[return_col].mean()
        
        group_returns = merged.groupby(date_col).apply(calc_group_returns)
        
        if group_returns.empty:
            return 0.0, pd.DataFrame()
        
        avg_group_returns = group_returns.groupby(level=1).mean()
        
        x = np.arange(len(avg_group_returns))
        y = avg_group_returns.values
        
        if len(x) < 2:
            return 0.0, avg_group_returns.to_frame('avg_return')
        
        correlation = np.corrcoef(x, y)[0, 1]
        monotonicity = abs(correlation)
        
        return monotonicity, avg_group_returns.to_frame('avg_return')


class CorrelationAnalyzer:
    """
    相关性分析器
    
    分析因子之间的相关性。
    """
    
    @staticmethod
    def calculate_factor_correlation(
        factor_df1: pd.DataFrame,
        factor_df2: pd.DataFrame,
        factor_col: str = "factor_value",
        date_col: str = "date",
        stock_col: str = "stock_code",
        method: str = "spearman"
    ) -> float:
        """
        计算两个因子之间的相关性
        
        Args:
            factor_df1: 第一个因子数据
            factor_df2: 第二个因子数据
            factor_col: 因子值列名
            date_col: 日期列名
            stock_col: 股票代码列名
            method: 相关系数方法
            
        Returns:
            float: 相关系数
        """
        merged = pd.merge(
            factor_df1[[date_col, stock_col, factor_col]].rename(columns={factor_col: 'factor1'}),
            factor_df2[[date_col, stock_col, factor_col]].rename(columns={factor_col: 'factor2'}),
            on=[date_col, stock_col],
            how="inner"
        )
        
        if len(merged) < 10:
            return np.nan
        
        if method == "spearman":
            corr, _ = stats.spearmanr(merged['factor1'], merged['factor2'])
        else:
            corr, _ = stats.pearsonr(merged['factor1'], merged['factor2'])
        
        return corr
    
    @staticmethod
    def calculate_correlation_matrix(
        factor_dfs: Dict[str, pd.DataFrame],
        factor_col: str = "factor_value",
        date_col: str = "date",
        stock_col: str = "stock_code",
        method: str = "spearman"
    ) -> pd.DataFrame:
        """
        计算多个因子之间的相关性矩阵
        
        Args:
            factor_dfs: 因子数据字典，键为因子ID
            factor_col: 因子值列名
            date_col: 日期列名
            stock_col: 股票代码列名
            method: 相关系数方法
            
        Returns:
            pd.DataFrame: 相关性矩阵
        """
        factor_ids = list(factor_dfs.keys())
        n_factors = len(factor_ids)
        
        corr_matrix = pd.DataFrame(
            np.eye(n_factors),
            index=factor_ids,
            columns=factor_ids
        )
        
        for i in range(n_factors):
            for j in range(i + 1, n_factors):
                fid1, fid2 = factor_ids[i], factor_ids[j]
                corr = CorrelationAnalyzer.calculate_factor_correlation(
                    factor_dfs[fid1],
                    factor_dfs[fid2],
                    factor_col,
                    date_col,
                    stock_col,
                    method
                )
                corr_matrix.loc[fid1, fid2] = corr
                corr_matrix.loc[fid2, fid1] = corr
        
        return corr_matrix


class FactorValidator:
    """
    因子验证器
    
    综合验证因子的预测能力和稳定性。
    """
    
    IC_THRESHOLD = 0.02
    IR_THRESHOLD = 0.3
    MONOTONICITY_THRESHOLD = 0.6
    CORRELATION_THRESHOLD = 0.7
    NAN_RATIO_THRESHOLD = 0.5
    
    def __init__(self):
        """初始化因子验证器"""
        self._registry = get_factor_registry()
    
    def validate(
        self,
        factor_id: str,
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        other_factor_dfs: Optional[Dict[str, pd.DataFrame]] = None,
        n_groups: int = 5
    ) -> ValidationResult:
        """
        验证因子
        
        Args:
            factor_id: 因子ID
            factor_df: 因子数据
            return_df: 收益数据
            other_factor_dfs: 其他因子数据（用于相关性分析）
            n_groups: 分组数量
            
        Returns:
            ValidationResult: 验证结果
        """
        try:
            factor_col = "factor_value"
            return_col = "forward_return"
            date_col = "date"
            stock_col = "stock_code"
            
            ic_series = ICAnalyzer.calculate_ic_series(
                factor_df, return_df,
                factor_col, return_col,
                date_col, stock_col
            )
            
            ic_result = ICAnalyzer.analyze_ic(ic_series)
            
            monotonicity, group_returns = MonotonicityAnalyzer.calculate_monotonicity(
                factor_df, return_df,
                n_groups, factor_col, return_col,
                date_col, stock_col
            )
            
            nan_ratio = factor_df[factor_col].isna().sum() / len(factor_df)
            
            coverage = factor_df[stock_col].nunique()
            
            avg_correlation = 0.0
            if other_factor_dfs:
                correlations = []
                for other_id, other_df in other_factor_dfs.items():
                    corr = CorrelationAnalyzer.calculate_factor_correlation(
                        factor_df, other_df,
                        factor_col, date_col, stock_col
                    )
                    if not np.isnan(corr):
                        correlations.append(abs(corr))
                
                if correlations:
                    avg_correlation = np.mean(correlations)
            
            metrics = FactorQualityMetrics(
                ic_mean=ic_result.ic_mean,
                ic_std=ic_result.ic_std,
                ir=ic_result.ic_ir,
                monotonicity=monotonicity,
                correlation_with_others=avg_correlation,
                nan_ratio=nan_ratio,
                coverage=coverage
            )
            
            details = {
                "ic_positive_ratio": ic_result.ic_positive_ratio,
                "ic_t_stat": ic_result.ic_t_stat,
                "ic_p_value": ic_result.ic_p_value,
                "group_returns": group_returns.to_dict() if not group_returns.empty else {},
                "validation_passed": self._check_thresholds(metrics)
            }
            
            self._registry.update_quality_metrics(factor_id, metrics)
            
            return ValidationResult(
                success=True,
                factor_id=factor_id,
                metrics=metrics,
                details=details
            )
            
        except Exception as e:
            return ValidationResult(
                success=False,
                factor_id=factor_id,
                error_message=str(e)
            )
    
    def _check_thresholds(self, metrics: FactorQualityMetrics) -> Dict[str, bool]:
        """检查指标是否满足阈值"""
        return {
            "ic_mean": abs(metrics.ic_mean) >= self.IC_THRESHOLD,
            "ir": abs(metrics.ir) >= self.IR_THRESHOLD,
            "monotonicity": metrics.monotonicity >= self.MONOTONICITY_THRESHOLD,
            "correlation": metrics.correlation_with_others < self.CORRELATION_THRESHOLD,
            "nan_ratio": metrics.nan_ratio < self.NAN_RATIO_THRESHOLD
        }
    
    def quick_validate(
        self,
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame
    ) -> Dict[str, float]:
        """
        快速验证因子（仅计算IC和IR）
        
        Args:
            factor_df: 因子数据
            return_df: 收益数据
            
        Returns:
            Dict[str, float]: 验证指标
        """
        ic_series = ICAnalyzer.calculate_ic_series(factor_df, return_df)
        ic_result = ICAnalyzer.analyze_ic(ic_series)
        
        return {
            "ic_mean": ic_result.ic_mean,
            "ic_std": ic_result.ic_std,
            "ir": ic_result.ic_ir,
            "ic_positive_ratio": ic_result.ic_positive_ratio
        }
    
    def compare_factors(
        self,
        factor_results: Dict[str, ValidationResult]
    ) -> pd.DataFrame:
        """
        比较多个因子的验证结果
        
        Args:
            factor_results: 因子验证结果字典
            
        Returns:
            pd.DataFrame: 比较表格
        """
        comparison_data = []
        
        for factor_id, result in factor_results.items():
            if result.success and result.metrics:
                comparison_data.append({
                    "factor_id": factor_id,
                    "ic_mean": result.metrics.ic_mean,
                    "ic_std": result.metrics.ic_std,
                    "ir": result.metrics.ir,
                    "monotonicity": result.metrics.monotonicity,
                    "correlation": result.metrics.correlation_with_others,
                    "nan_ratio": result.metrics.nan_ratio,
                    "coverage": result.metrics.coverage
                })
        
        return pd.DataFrame(comparison_data)


_default_validator: Optional[FactorValidator] = None


def get_factor_validator() -> FactorValidator:
    """获取全局因子验证器实例"""
    global _default_validator
    if _default_validator is None:
        _default_validator = FactorValidator()
    return _default_validator


def reset_factor_validator():
    """重置全局因子验证器"""
    global _default_validator
    _default_validator = None
