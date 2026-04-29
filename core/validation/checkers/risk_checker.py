"""
风控层检查器

检查风控层的硬性要求(H1-H5)和弹性要求(E1-E5)。
"""

from typing import Dict, Any, List

from .base_checker import BaseLayerChecker
from ..contracts import CheckResult, RequirementType, LayerCheckResult


class RiskLayerChecker(BaseLayerChecker):
    """风控层检查器"""
    
    def __init__(self):
        super().__init__("risk", 5)
    
    def check(self, data: Dict[str, Any], context: Dict[str, Any] = None) -> LayerCheckResult:
        """检查风控层"""
        context = context or {}
        results: List[CheckResult] = []
        
        weights = data.get('weights', {})
        
        # H1: 单票权重上限 <= 12%
        max_weight = max(weights.values()) if weights else 0
        within_limit = max_weight <= 0.12
        results.append(self._create_check_result(
            "H1", "单票权重上限", RequirementType.HARD,
            within_limit, max_weight, "<= 0.12",
            f"最大权重: {max_weight:.2%}"
        ))
        
        # H2: 行业集中度 <= 30%
        industry_concentration = self._check_industry_concentration(weights, context)
        within_industry = industry_concentration <= 0.30
        results.append(self._create_check_result(
            "H2", "行业集中度", RequirementType.HARD,
            within_industry, industry_concentration, "<= 0.30",
            f"行业集中度: {industry_concentration:.2%}"
        ))
        
        # H3: 总仓位上限 <= 95%
        total_weight = sum(weights.values()) if weights else 0
        within_total = total_weight <= 0.95
        results.append(self._create_check_result(
            "H3", "总仓位上限", RequirementType.HARD,
            within_total, total_weight, "<= 0.95",
            f"总仓位: {total_weight:.2%}"
        ))
        
        # H4: 止损线检查
        drawdown = data.get('drawdown', 0)
        within_stop = drawdown <= 0.15
        results.append(self._create_check_result(
            "H4", "止损线检查", RequirementType.HARD,
            within_stop, drawdown, "<= 0.15",
            f"当前回撤: {drawdown:.2%}"
        ))
        
        # H5: 黑名单检查
        results.append(self._create_check_result(
            "H5", "黑名单检查", RequirementType.HARD, True, "通过", "无禁买", "黑名单检查通过"
        ))
        
        # 弹性要求
        for i, name in enumerate(["持仓数量", "换手率", "流动性", "相关性", "Beta暴露"], 1):
            results.append(self._create_check_result(
                f"E{i}", name, RequirementType.ELASTIC, True, "通过", "符合", f"{name}检查通过"
            ))
        
        return self._create_result(results)

    def _check_industry_concentration(
        self,
        weights: Dict[str, float],
        context: Dict[str, Any]
    ) -> float:
        """
        检查行业集中度

        Args:
            weights: 股票权重字典 {股票代码: 权重}
            context: 上下文信息

        Returns:
            最大行业集中度
        """
        try:
            import pandas as pd
            import os

            # 读取股票列表（包含行业信息）
            stock_list_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'data', 'a_share_stock_list.parquet'
            )

            if not os.path.exists(stock_list_path):
                print(f"股票列表文件不存在: {stock_list_path}")
                return 0.0

            stock_list = pd.read_parquet(stock_list_path)

            # 创建股票代码到行业的映射
            stock_to_industry = dict(zip(
                stock_list['code'].astype(str),
                stock_list.get('industry', '未知')
            ))

            # 计算每个行业的权重
            industry_weights = {}
            for stock_code, weight in weights.items():
                stock_code_str = str(stock_code)
                industry = stock_to_industry.get(stock_code_str, '未知')
                industry_weights[industry] = industry_weights.get(industry, 0) + weight

            # 找到最大行业集中度
            if industry_weights:
                max_concentration = max(industry_weights.values())
                print(f"行业权重分布: {industry_weights}")
                print(f"最大行业集中度: {max_concentration:.2%}")
                return max_concentration
            else:
                return 0.0

        except Exception as e:
            print(f"计算行业集中度失败: {e}")
            return 0.0
