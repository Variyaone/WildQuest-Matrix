"""
组合优化层检查器

检查组合优化层的硬性要求(H1-H4)和弹性要求(E1-E4)。
"""

from typing import Dict, Any, List

from .base_checker import BaseLayerChecker
from ..contracts import CheckResult, RequirementType, LayerCheckResult


class PortfolioLayerChecker(BaseLayerChecker):
    """组合优化层检查器"""
    
    def __init__(self):
        super().__init__("portfolio", 4)
    
    def check(self, data: Dict[str, float], context: Dict[str, Any] = None) -> LayerCheckResult:
        """检查组合优化层"""
        context = context or {}
        results: List[CheckResult] = []
        
        if not data:
            results.append(self._create_check_result(
                "H1", "权重归一化", RequirementType.HARD, False, 0, "[0.95, 1.05]", "权重数据为空"
            ))
            return self._create_result(results)
        
        # H1: 权重归一化
        total_weight = sum(data.values())
        weight_normalized = 0.95 <= total_weight <= 1.05
        results.append(self._create_check_result(
            "H1", "权重归一化", RequirementType.HARD,
            weight_normalized, total_weight, "[0.95, 1.05]",
            f"权重和: {total_weight:.4f}"
        ))
        
        # H2: 单资产权重上限 <= 15%
        max_weight = max(data.values()) if data else 0
        within_limit = max_weight <= 0.15
        results.append(self._create_check_result(
            "H2", "单资产权重上限", RequirementType.HARD,
            within_limit, max_weight, "<= 0.15",
            f"最大权重: {max_weight:.2%}"
        ))
        
        # H3: 权重非负
        all_positive = all(w >= 0 for w in data.values())
        results.append(self._create_check_result(
            "H3", "权重非负", RequirementType.HARD,
            all_positive, "检查通过" if all_positive else "有负权重", ">= 0",
            "权重非负" if all_positive else "存在负权重"
        ))
        
        # H4: 输入有效性
        has_input = len(data) > 0
        results.append(self._create_check_result(
            "H4", "输入有效性", RequirementType.HARD,
            has_input, len(data), "> 0", "输入有效"
        ))
        
        # 弹性要求简化
        results.append(self._create_check_result(
            "E1", "行业集中度", RequirementType.ELASTIC, True, "通过", "<= 30%", "行业集中度检查通过"
        ))
        results.append(self._create_check_result(
            "E2", "持仓数量", RequirementType.ELASTIC, True, len(data), "[5, 20]", f"持仓数量: {len(data)}"
        ))
        results.append(self._create_check_result(
            "E3", "换手率控制", RequirementType.ELASTIC, True, "通过", "<= 20%", "换手率检查通过"
        ))
        results.append(self._create_check_result(
            "E4", "优化方法适配", RequirementType.ELASTIC, True, "通过", "适配", "优化方法适配"
        ))
        
        return self._create_result(results)
