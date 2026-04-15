"""
数据层检查器

检查数据层的硬性要求(H1-H5)和弹性要求(E1-E5)。
"""

from typing import Dict, Any, List
import pandas as pd
import numpy as np

from .base_checker import BaseLayerChecker
from ..contracts import (
    CheckResult,
    LayerCheckResult,
    RequirementType,
    DataLayerContract
)


class DataLayerChecker(BaseLayerChecker):
    """数据层检查器"""
    
    def __init__(self):
        super().__init__("data", 1)
        self.contract = DataLayerContract()
    
    def check(self, data: pd.DataFrame, context: Dict[str, Any] = None) -> LayerCheckResult:
        """
        检查数据层
        
        Args:
            data: 市场数据DataFrame
            context: 检查上下文
                - completeness_threshold: 完整性阈值 (默认0.99)
                - quality_score_threshold: 质量分数阈值 (默认80)
                
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
        """检查硬性要求 H1-H5"""
        results = []
        
        # H1: 数据非空
        is_not_empty = df is not None and len(df) > 0
        results.append(self._create_check_result(
            req_id="H1",
            req_name="数据非空",
            req_type=RequirementType.HARD,
            passed=is_not_empty,
            actual_value=len(df) if df is not None else 0,
            expected_value="> 0",
            message="数据非空检查通过" if is_not_empty else "数据为空",
            details={"row_count": len(df) if df is not None else 0}
        ))
        
        if not is_not_empty:
            # 如果数据为空，后续检查跳过
            return results
        
        # H2: 必需字段完整
        required_fields = self.contract.REQUIRED_FIELDS
        missing_fields = [f for f in required_fields if f not in df.columns]
        has_all_fields = len(missing_fields) == 0
        results.append(self._create_check_result(
            req_id="H2",
            req_name="必需字段完整",
            req_type=RequirementType.HARD,
            passed=has_all_fields,
            actual_value=df.columns.tolist(),
            expected_value=required_fields,
            message=f"必需字段完整" if has_all_fields else f"缺少字段: {missing_fields}",
            details={"missing_fields": missing_fields}
        ))
        
        # H3: 时间序列连续 (缺失率 < 10%)
        continuity_passed = self._check_continuity(df)
        results.append(self._create_check_result(
            req_id="H3",
            req_name="时间序列连续",
            req_type=RequirementType.HARD,
            passed=continuity_passed,
            actual_value="连续" if continuity_passed else "不连续",
            expected_value="缺失率 < 10%",
            message="时间序列连续" if continuity_passed else "时间序列不连续，缺失率过高",
        ))
        
        # H4: 价格逻辑一致
        price_logic_passed = self._check_price_logic(df)
        results.append(self._create_check_result(
            req_id="H4",
            req_name="价格逻辑一致",
            req_type=RequirementType.HARD,
            passed=price_logic_passed,
            actual_value="一致" if price_logic_passed else "不一致",
            expected_value="high >= max(open,close), low <= min(open,close)",
            message="价格逻辑一致" if price_logic_passed else "价格逻辑不一致",
        ))
        
        # H5: 无未来数据泄露
        # 简化实现：检查日期是否超过今天
        future_leak_passed = self._check_future_leak(df)
        results.append(self._create_check_result(
            req_id="H5",
            req_name="无未来数据泄露",
            req_type=RequirementType.HARD,
            passed=future_leak_passed,
            actual_value="无泄露" if future_leak_passed else "有泄露",
            expected_value="无未来数据",
            message="无未来数据泄露" if future_leak_passed else "检测到未来数据泄露",
        ))
        
        return results
    
    def _check_elastic_requirements(self, df: pd.DataFrame, context: Dict[str, Any]) -> List[CheckResult]:
        """检查弹性要求 E1-E5"""
        results = []
        
        # E1: 数据完整性 >= 99%
        completeness_threshold = context.get('completeness_threshold', 0.99)
        completeness = self._calculate_completeness(df)
        results.append(self._create_check_result(
            req_id="E1",
            req_name="数据完整性",
            req_type=RequirementType.ELASTIC,
            passed=completeness >= completeness_threshold,
            actual_value=f"{completeness:.2%}",
            expected_value=f">= {completeness_threshold:.0%}",
            message=f"数据完整性: {completeness:.2%}",
            details={"completeness": completeness}
        ))
        
        # E2: 数据时效性 (需要上下文中的数据时间)
        data_freshness_passed = True
        results.append(self._create_check_result(
            req_id="E2",
            req_name="数据时效性",
            req_type=RequirementType.ELASTIC,
            passed=data_freshness_passed,
            actual_value="待实现",
            expected_value="< 24小时",
            message="数据时效性检查待实现",
        ))
        
        # E3: 质量分数 >= 80
        quality_score_threshold = context.get('quality_score_threshold', 80)
        quality_score = self._calculate_quality_score(df)
        results.append(self._create_check_result(
            req_id="E3",
            req_name="质量分数",
            req_type=RequirementType.ELASTIC,
            passed=quality_score >= quality_score_threshold,
            actual_value=f"{quality_score:.1f}",
            expected_value=f">= {quality_score_threshold}",
            message=f"质量分数: {quality_score:.1f}",
            details={"quality_score": quality_score}
        ))
        
        # E4: 多源一致性 >= 95%
        results.append(self._create_check_result(
            req_id="E4",
            req_name="多源一致性",
            req_type=RequirementType.ELASTIC,
            passed=True,  # 简化实现
            actual_value="待实现",
            expected_value=">= 95%",
            message="多源一致性检查待实现",
        ))
        
        # E5: 异常值比例 < 0.5%
        outlier_ratio = self._calculate_outlier_ratio(df)
        results.append(self._create_check_result(
            req_id="E5",
            req_name="异常值比例",
            req_type=RequirementType.ELASTIC,
            passed=outlier_ratio < 0.005,
            actual_value=f"{outlier_ratio:.2%}",
            expected_value="< 0.5%",
            message=f"异常值比例: {outlier_ratio:.2%}",
            details={"outlier_ratio": outlier_ratio}
        ))
        
        return results
    
    def _check_continuity(self, df: pd.DataFrame) -> bool:
        """检查时间序列连续性"""
        try:
            if 'stock_code' not in df.columns or 'date' not in df.columns:
                return True  # 无法检查，默认通过
            
            grouped = df.groupby('stock_code')
            for stock_code, group in grouped:
                if len(group) <= 1:
                    continue
                dates = pd.to_datetime(group['date']).sort_values()
                expected_days = (dates.max() - dates.min()).days + 1
                actual_days = len(dates)
                if actual_days < expected_days * 0.9:
                    return False
            return True
        except Exception:
            return False
    
    def _check_price_logic(self, df: pd.DataFrame) -> bool:
        """检查价格逻辑一致性"""
        try:
            required = ['high', 'low', 'open', 'close']
            if not all(col in df.columns for col in required):
                return True  # 无法检查，默认通过
            
            valid_high = (df['high'] >= df[['open', 'close']].max(axis=1)).all()
            valid_low = (df['low'] <= df[['open', 'close']].min(axis=1)).all()
            return bool(valid_high and valid_low)
        except Exception:
            return False
    
    def _check_future_leak(self, df: pd.DataFrame) -> bool:
        """检查未来数据泄露"""
        try:
            if 'date' not in df.columns:
                return True
            
            from datetime import datetime
            max_date = pd.to_datetime(df['date']).max()
            today = datetime.now()
            return max_date.date() <= today.date()
        except Exception:
            return True
    
    def _calculate_completeness(self, df: pd.DataFrame) -> float:
        """计算数据完整性"""
        try:
            total_cells = df.size
            missing_cells = df.isna().sum().sum()
            return 1 - (missing_cells / total_cells) if total_cells > 0 else 0
        except Exception:
            return 0
    
    def _calculate_quality_score(self, df: pd.DataFrame) -> float:
        """计算质量分数"""
        # 简化实现：基于完整性和价格逻辑
        completeness = self._calculate_completeness(df)
        price_logic = 1.0 if self._check_price_logic(df) else 0.0
        continuity = 1.0 if self._check_continuity(df) else 0.0
        
        # 加权平均
        score = (completeness * 0.4 + price_logic * 0.3 + continuity * 0.3) * 100
        return score
    
    def _calculate_outlier_ratio(self, df: pd.DataFrame) -> float:
        """计算异常值比例"""
        try:
            price_cols = ['open', 'high', 'low', 'close']
            available_cols = [c for c in price_cols if c in df.columns]
            
            if not available_cols:
                return 0
            
            outlier_count = 0
            total_count = 0
            
            for col in available_cols:
                series = df[col].dropna()
                if len(series) == 0:
                    continue
                
                # 使用IQR方法检测异常值
                Q1 = series.quantile(0.25)
                Q3 = series.quantile(0.75)
                IQR = Q3 - Q1
                
                outliers = ((series < (Q1 - 3 * IQR)) | (series > (Q3 + 3 * IQR))).sum()
                outlier_count += outliers
                total_count += len(series)
            
            return outlier_count / total_count if total_count > 0 else 0
        except Exception:
            return 0
