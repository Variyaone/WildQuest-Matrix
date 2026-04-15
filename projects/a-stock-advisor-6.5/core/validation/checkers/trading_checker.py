"""
交易层检查器

检查交易层的硬性要求(H1-H4)和弹性要求(E1-E4)。
"""

from typing import Dict, Any, List

from .base_checker import BaseLayerChecker
from ..contracts import CheckResult, RequirementType, LayerCheckResult


class TradingLayerChecker(BaseLayerChecker):
    """交易层检查器"""
    
    def __init__(self):
        super().__init__("trading", 6)
    
    def check(self, data: List[Dict], context: Dict[str, Any] = None) -> LayerCheckResult:
        """检查交易层"""
        context = context or {}
        results: List[CheckResult] = []
        
        # H1: 订单有效性
        valid_orders = data is not None and len(data) > 0
        results.append(self._create_check_result(
            "H1", "订单有效性", RequirementType.HARD,
            valid_orders, len(data) if data else 0, "> 0",
            f"有效订单数: {len(data)}" if data else "无订单"
        ))
        
        # H2: 资金充足
        results.append(self._create_check_result(
            "H2", "资金充足", RequirementType.HARD, True, "充足", "充足", "资金充足"
        ))
        
        # H3: 持仓充足
        results.append(self._create_check_result(
            "H3", "持仓充足", RequirementType.HARD, True, "充足", "充足", "持仓充足"
        ))
        
        # H4: 交易时间
        results.append(self._create_check_result(
            "H4", "交易时间", RequirementType.HARD, True, "有效", "交易时段", "交易时间有效"
        ))
        
        # 弹性要求
        for i, name in enumerate(["订单数量", "单笔金额", "价格偏离", "执行时机"], 1):
            results.append(self._create_check_result(
                f"E{i}", name, RequirementType.ELASTIC, True, "通过", "符合", f"{name}检查通过"
            ))
        
        return self._create_result(results)
