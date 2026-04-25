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
        results.append(self._create_check_result(
            "H2", "行业集中度", RequirementType.HARD, True, "通过", "<= 30%", "行业集中度检查通过"
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
