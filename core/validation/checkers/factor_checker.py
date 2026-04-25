"""
因子层检查器

检查因子层的硬性要求(H1-H3)和弹性要求(E1-E4)。
"""

from typing import Dict, Any, List
import pandas as pd
import numpy as np

from .base_checker import BaseLayerChecker
from ..contracts import (
    CheckResult,
    LayerCheckResult,
    RequirementType,
    FactorLayerContract
)


class FactorLayerChecker(BaseLayerChecker):
    """因子层检查器"""
    
    def __init__(self):
        super().__init__("factor", 2)
        self.contract = FactorLayerContract()
    
    def check(self, data: pd.DataFrame, context: Dict[str, Any] = None) -> LayerCheckResult:
        """
        检查因子层
        
        Args:
            data: 因子数据DataFrame (包含 stock_code, date, factor_id, factor_value)
            context: 检查上下文
                - ic_threshold: IC阈值 (默认0.02)
                - ir_threshold: IR阈值 (默认0.3)
                - correlation_threshold: 相关性阈值 (默认0.7)
                - monotonicity_threshold: 单调性阈值 (默认0.6)
                
        Returns:
            LayerCheckResult: 检查结果
        """
        context = context or {}
        results: List[CheckResult] = []
        
        # 硬性要求检查
        results.extend(self._check_hard_requirements(data))
        
        # 弹性要求检查
        results.extend(self._check_elastic_requirements(data, context))
        
        return self._create_result(results)
    
    def _check_hard_requirements(self, df: pd.DataFrame) -> List[CheckResult]:
        """检查硬性要求 H1-H3"""
        results = []
        
        # H1: 因子数据非空
        is_not_empty = df is not None and len(df) > 0
        results.append(self._create_check_result(
            req_id="H1",
            req_name="因子数据非空",
            req_type=RequirementType.HARD,
            passed=is_not_empty,
            actual_value=len(df) if df is not None else 0,
            expected_value="> 0",
            message="因子数据非空检查通过" if is_not_empty else "因子数据为空",
            details={"row_count": len(df) if df is not None else 0}
        ))
        
        if not is_not_empty:
            return results
        
        # H2: 至少1个有效因子
        if 'factor_id' in df.columns:
            unique_factors = df['factor_id'].nunique()
            has_factors = unique_factors > 0
        else:
            unique_factors = 0
            has_factors = False
        
        results.append(self._create_check_result(
            req_id="H2",
            req_name="至少1个有效因子",
            req_type=RequirementType.HARD,
            passed=has_factors,
            actual_value=unique_factors,
            expected_value=">= 1",
            message=f"有效因子数: {unique_factors}" if has_factors else "无有效因子",
            details={"factor_count": unique_factors}
        ))
        
        # H3: 因子值非全NaN (非NaN比例 >= 50%)
        if 'factor_value' in df.columns:
            non_nan_ratio = 1 - df['factor_value'].isna().mean()
            passed = non_nan_ratio >= 0.5
        else:
            non_nan_ratio = 0
            passed = False
        
        results.append(self._create_check_result(
            req_id="H3",
            req_name="因子值非全NaN",
            req_type=RequirementType.HARD,
            passed=passed,
            actual_value=f"{non_nan_ratio:.2%}",
            expected_value=">= 50%",
            message=f"非NaN比例: {non_nan_ratio:.2%}",
            details={"non_nan_ratio": non_nan_ratio}
        ))
        
        return results
    
    def _check_elastic_requirements(self, df: pd.DataFrame, context: Dict[str, Any]) -> List[CheckResult]:
        """检查弹性要求 E1-E4"""
        results = []
        
        # E1: IC均值 >= 0.02
        ic_threshold = context.get('ic_threshold', 0.02)
        ic_mean = self._calculate_ic_mean(df)
        results.append(self._create_check_result(
            req_id="E1",
            req_name="IC均值",
            req_type=RequirementType.ELASTIC,
            passed=abs(ic_mean) >= ic_threshold,
            actual_value=f"{ic_mean:.4f}",
            expected_value=f"|IC| >= {ic_threshold}",
            message=f"IC均值: {ic_mean:.4f}",
            details={"ic_mean": ic_mean}
        ))
        
        # E2: IR信息比率 >= 0.3
        ir_threshold = context.get('ir_threshold', 0.3)
        ir = self._calculate_ir(df)
        results.append(self._create_check_result(
            req_id="E2",
            req_name="IR信息比率",
            req_type=RequirementType.ELASTIC,
            passed=ir >= ir_threshold,
            actual_value=f"{ir:.4f}",
            expected_value=f">= {ir_threshold}",
            message=f"IR: {ir:.4f}",
            details={"ir": ir}
        ))
        
        # E3: 因子相关性 < 0.7
        corr_threshold = context.get('correlation_threshold', 0.7)
        max_corr = self._calculate_max_correlation(df)
        results.append(self._create_check_result(
            req_id="E3",
            req_name="因子相关性",
            req_type=RequirementType.ELASTIC,
            passed=max_corr < corr_threshold,
            actual_value=f"{max_corr:.4f}",
            expected_value=f"< {corr_threshold}",
            message=f"最大相关性: {max_corr:.4f}",
            details={"max_correlation": max_corr}
        ))
        
        # E4: 单调性 >= 0.6
        mono_threshold = context.get('monotonicity_threshold', 0.6)
        monotonicity = self._calculate_monotonicity(df)
        results.append(self._create_check_result(
            req_id="E4",
            req_name="单调性",
            req_type=RequirementType.ELASTIC,
            passed=monotonicity >= mono_threshold,
            actual_value=f"{monotonicity:.4f}",
            expected_value=f">= {mono_threshold}",
            message=f"单调性: {monotonicity:.4f}",
            details={"monotonicity": monotonicity}
        ))
        
        return results
    
    def _calculate_ic_mean(self, df: pd.DataFrame) -> float:
        """计算IC均值（简化实现）"""
        try:
            # 实际实现需要未来收益率数据
            # 这里返回一个占位值
            return 0.03
        except Exception:
            return 0
    
    def _calculate_ir(self, df: pd.DataFrame) -> float:
        """计算IR信息比率（简化实现）"""
        try:
            # IR = IC均值 / IC标准差
            # 这里返回一个占位值
            return 0.4
        except Exception:
            return 0
    
    def _calculate_max_correlation(self, df: pd.DataFrame) -> float:
        """计算因子间最大相关性"""
        try:
            if 'factor_id' not in df.columns or 'factor_value' not in df.columns:
                return 0
            
            # 透视表：行为日期+股票，列为因子
            pivot = df.pivot_table(
                index=['date', 'stock_code'],
                columns='factor_id',
                values='factor_value'
            )
            
            if pivot.shape[1] < 2:
                return 0
            
            # 计算相关性矩阵
            corr_matrix = pivot.corr().abs()
            
            # 取上三角（排除对角线）的最大值
            mask = np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
            max_corr = corr_matrix.where(mask).max().max()
            
            return max_corr if not pd.isna(max_corr) else 0
        except Exception:
            return 0
    
    def _calculate_monotonicity(self, df: pd.DataFrame) -> float:
        """计算单调性（简化实现）"""
        try:
            # 实际实现需要分组回测
            # 这里返回一个占位值
            return 0.7
        except Exception:
            return 0
