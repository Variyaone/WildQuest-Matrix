"""
事前风控模块

交易前检查，防止违规交易。包括：
- 单票权重上限检查
- 行业集中度检查
- 总仓位上限检查
- 止损线检查
- 黑名单检查
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum

from .limits import (
    RiskLimits, HardLimits, SoftLimits, BlacklistConfig,
    get_risk_limits, RiskLevel, LimitType
)


class CheckResult(Enum):
    """检查结果"""
    PASS = "pass"
    WARNING = "warning"
    REJECT = "reject"


@dataclass
class Violation:
    """违规记录"""
    rule_id: str
    rule_name: str
    limit_type: LimitType
    risk_level: RiskLevel
    actual_value: float
    limit_value: float
    message: str
    stock_codes: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "limit_type": self.limit_type.value,
            "risk_level": self.risk_level.value,
            "actual_value": self.actual_value,
            "limit_value": self.limit_value,
            "message": self.message,
            "stock_codes": self.stock_codes,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class PreTradeCheckResult:
    """事前检查结果"""
    passed: bool
    result: CheckResult
    violations: List[Violation] = field(default_factory=list)
    warnings: List[Violation] = field(default_factory=list)
    checked_at: datetime = field(default_factory=datetime.now)
    total_checks: int = 0
    passed_checks: int = 0
    
    def add_violation(self, violation: Violation):
        """添加违规记录"""
        if violation.limit_type == LimitType.HARD:
            self.violations.append(violation)
            self.passed = False
            self.result = CheckResult.REJECT
        else:
            self.warnings.append(violation)
            if self.result == CheckResult.PASS:
                self.result = CheckResult.WARNING
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "passed": self.passed,
            "result": self.result.value,
            "violations": [v.to_dict() for v in self.violations],
            "warnings": [v.to_dict() for v in self.warnings],
            "checked_at": self.checked_at.isoformat(),
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks
        }


@dataclass
class TradeInstruction:
    """交易指令"""
    stock_code: str
    direction: str
    quantity: int
    price: Optional[float] = None
    amount: Optional[float] = None
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "stock_code": self.stock_code,
            "direction": self.direction,
            "quantity": self.quantity,
            "price": self.price,
            "amount": self.amount,
            "reason": self.reason
        }


@dataclass
class PortfolioState:
    """组合状态"""
    total_capital: float
    positions: Dict[str, float]
    weights: Dict[str, float]
    industry_mapping: Dict[str, str]
    current_drawdown: float = 0.0
    cash: float = 0.0
    
    def get_industry_weights(self) -> Dict[str, float]:
        """计算行业权重"""
        industry_weights = {}
        for stock, weight in self.weights.items():
            industry = self.industry_mapping.get(stock, "Unknown")
            industry_weights[industry] = industry_weights.get(industry, 0) + weight
        return industry_weights
    
    def get_total_position(self) -> float:
        """获取总仓位"""
        return sum(self.positions.values())
    
    def get_position_ratio(self) -> float:
        """获取仓位比例"""
        return self.get_total_position() / self.total_capital if self.total_capital > 0 else 0.0


class PreTradeRiskChecker:
    """
    事前风控检查器
    
    执行交易前的风险检查，确保交易符合风控规则。
    """
    
    def __init__(self, risk_limits: Optional[RiskLimits] = None):
        self.risk_limits = risk_limits or get_risk_limits()
    
    def check(
        self,
        trade_instructions: List[TradeInstruction],
        portfolio_state: PortfolioState,
        check_soft_limits: bool = True
    ) -> PreTradeCheckResult:
        """
        执行事前风控检查
        
        Args:
            trade_instructions: 交易指令列表
            portfolio_state: 当前组合状态
            check_soft_limits: 是否检查弹性限制
            
        Returns:
            PreTradeCheckResult: 检查结果
        """
        result = PreTradeCheckResult(passed=True, result=CheckResult.PASS)
        
        result.total_checks = 5 if check_soft_limits else 3
        
        hard_result = self._check_hard_limits(trade_instructions, portfolio_state)
        for violation in hard_result:
            result.add_violation(violation)
        
        if not result.violations:
            result.passed_checks += 3
        
        if check_soft_limits:
            soft_result = self._check_soft_limits(trade_instructions, portfolio_state)
            for warning in soft_result:
                result.add_violation(warning)
            
            if len(soft_result) == 0:
                result.passed_checks += 2
        
        return result
    
    def _check_hard_limits(
        self,
        trade_instructions: List[TradeInstruction],
        portfolio_state: PortfolioState
    ) -> List[Violation]:
        """检查硬性限制"""
        violations = []
        
        violations.extend(self._check_single_stock_weight(trade_instructions, portfolio_state))
        violations.extend(self._check_industry_concentration(trade_instructions, portfolio_state))
        violations.extend(self._check_total_position(trade_instructions, portfolio_state))
        violations.extend(self._check_drawdown_limit(trade_instructions, portfolio_state))
        violations.extend(self._check_blacklist(trade_instructions, portfolio_state))
        
        return violations
    
    def _check_soft_limits(
        self,
        trade_instructions: List[TradeInstruction],
        portfolio_state: PortfolioState
    ) -> List[Violation]:
        """检查弹性限制"""
        warnings = []
        
        warnings.extend(self._check_stock_count(trade_instructions, portfolio_state))
        warnings.extend(self._check_turnover_rate(trade_instructions, portfolio_state))
        warnings.extend(self._check_liquidity(trade_instructions, portfolio_state))
        
        return warnings
    
    def _check_single_stock_weight(
        self,
        trade_instructions: List[TradeInstruction],
        portfolio_state: PortfolioState
    ) -> List[Violation]:
        """检查单票权重上限"""
        violations = []
        hard_limits = self.risk_limits.hard_limits
        
        new_weights = portfolio_state.weights.copy()
        for instruction in trade_instructions:
            if instruction.direction == "buy":
                amount = instruction.amount or (instruction.quantity * instruction.price if instruction.price and instruction.quantity else 0)
                weight_change = amount / portfolio_state.total_capital if portfolio_state.total_capital > 0 else 0
                new_weights[instruction.stock_code] = new_weights.get(instruction.stock_code, 0) + weight_change
            elif instruction.direction == "sell":
                if instruction.stock_code in new_weights:
                    amount = instruction.amount or (instruction.quantity * instruction.price if instruction.price and instruction.quantity else 0)
                    weight_change = amount / portfolio_state.total_capital if portfolio_state.total_capital > 0 else 0
                    new_weights[instruction.stock_code] = max(0, new_weights[instruction.stock_code] - weight_change)
        
        for stock, weight in new_weights.items():
            if weight > hard_limits.max_single_stock_weight:
                violations.append(Violation(
                    rule_id="H1",
                    rule_name="单票权重上限",
                    limit_type=LimitType.HARD,
                    risk_level=RiskLevel.HIGH,
                    actual_value=weight,
                    limit_value=hard_limits.max_single_stock_weight,
                    message=f"股票 {stock} 权重 {weight:.2%} 超过上限 {hard_limits.max_single_stock_weight:.2%}",
                    stock_codes=[stock]
                ))
        
        return violations
    
    def _check_industry_concentration(
        self,
        trade_instructions: List[TradeInstruction],
        portfolio_state: PortfolioState
    ) -> List[Violation]:
        """检查行业集中度"""
        violations = []
        hard_limits = self.risk_limits.hard_limits
        
        new_weights = portfolio_state.weights.copy()
        for instruction in trade_instructions:
            if instruction.direction == "buy":
                amount = instruction.amount or (instruction.quantity * instruction.price if instruction.price and instruction.quantity else 0)
                weight_change = amount / portfolio_state.total_capital if portfolio_state.total_capital > 0 else 0
                new_weights[instruction.stock_code] = new_weights.get(instruction.stock_code, 0) + weight_change
            elif instruction.direction == "sell":
                if instruction.stock_code in new_weights:
                    amount = instruction.amount or (instruction.quantity * instruction.price if instruction.price and instruction.quantity else 0)
                    weight_change = amount / portfolio_state.total_capital if portfolio_state.total_capital > 0 else 0
                    new_weights[instruction.stock_code] = max(0, new_weights[instruction.stock_code] - weight_change)
        
        industry_weights = {}
        for stock, weight in new_weights.items():
            industry = portfolio_state.industry_mapping.get(stock, "Unknown")
            industry_weights[industry] = industry_weights.get(industry, 0) + weight
        
        for industry, weight in industry_weights.items():
            if weight > hard_limits.max_industry_concentration:
                violations.append(Violation(
                    rule_id="H2",
                    rule_name="行业集中度上限",
                    limit_type=LimitType.HARD,
                    risk_level=RiskLevel.HIGH,
                    actual_value=weight,
                    limit_value=hard_limits.max_industry_concentration,
                    message=f"行业 {industry} 集中度 {weight:.2%} 超过上限 {hard_limits.max_industry_concentration:.2%}",
                    details={"industry": industry}
                ))
        
        return violations
    
    def _check_total_position(
        self,
        trade_instructions: List[TradeInstruction],
        portfolio_state: PortfolioState
    ) -> List[Violation]:
        """检查总仓位上限"""
        violations = []
        hard_limits = self.risk_limits.hard_limits
        
        new_position = portfolio_state.get_total_position()
        for instruction in trade_instructions:
            if instruction.direction == "buy":
                amount = instruction.amount or (instruction.quantity * instruction.price if instruction.price and instruction.quantity else 0)
                new_position += amount
            elif instruction.direction == "sell":
                amount = instruction.amount or (instruction.quantity * instruction.price if instruction.price and instruction.quantity else 0)
                new_position -= amount
        
        new_position_ratio = new_position / portfolio_state.total_capital if portfolio_state.total_capital > 0 else 0
        
        if new_position_ratio > hard_limits.max_total_position:
            violations.append(Violation(
                rule_id="H3",
                rule_name="总仓位上限",
                limit_type=LimitType.HARD,
                risk_level=RiskLevel.HIGH,
                actual_value=new_position_ratio,
                limit_value=hard_limits.max_total_position,
                message=f"总仓位 {new_position_ratio:.2%} 超过上限 {hard_limits.max_total_position:.2%}"
            ))
        
        return violations
    
    def _check_drawdown_limit(
        self,
        trade_instructions: List[TradeInstruction],
        portfolio_state: PortfolioState
    ) -> List[Violation]:
        """检查止损线"""
        violations = []
        hard_limits = self.risk_limits.hard_limits
        
        if portfolio_state.current_drawdown > hard_limits.max_drawdown:
            violations.append(Violation(
                rule_id="H4",
                rule_name="止损线检查",
                limit_type=LimitType.HARD,
                risk_level=RiskLevel.CRITICAL,
                actual_value=portfolio_state.current_drawdown,
                limit_value=hard_limits.max_drawdown,
                message=f"当前回撤 {portfolio_state.current_drawdown:.2%} 超过止损线 {hard_limits.max_drawdown:.2%}，应停止买入"
            ))
        
        return violations
    
    def _check_blacklist(
        self,
        trade_instructions: List[TradeInstruction],
        portfolio_state: PortfolioState
    ) -> List[Violation]:
        """检查黑名单"""
        violations = []
        blacklist_config = self.risk_limits.blacklist
        
        if not blacklist_config.enabled:
            return violations
        
        for instruction in trade_instructions:
            if instruction.direction == "buy":
                if blacklist_config.is_stock_blocked(instruction.stock_code):
                    violations.append(Violation(
                        rule_id="H5",
                        rule_name="黑名单检查",
                        limit_type=LimitType.HARD,
                        risk_level=RiskLevel.CRITICAL,
                        actual_value=1,
                        limit_value=0,
                        message=f"股票 {instruction.stock_code} 在黑名单中，禁止买入",
                        stock_codes=[instruction.stock_code]
                    ))
                
                industry = portfolio_state.industry_mapping.get(instruction.stock_code, "")
                if blacklist_config.is_industry_blocked(industry):
                    violations.append(Violation(
                        rule_id="H5",
                        rule_name="行业黑名单检查",
                        limit_type=LimitType.HARD,
                        risk_level=RiskLevel.HIGH,
                        actual_value=1,
                        limit_value=0,
                        message=f"股票 {instruction.stock_code} 所属行业 {industry} 在黑名单中，禁止买入",
                        stock_codes=[instruction.stock_code],
                        details={"industry": industry}
                    ))
        
        return violations
    
    def _check_stock_count(
        self,
        trade_instructions: List[TradeInstruction],
        portfolio_state: PortfolioState
    ) -> List[Violation]:
        """检查持仓数量"""
        warnings = []
        soft_limits = self.risk_limits.soft_limits
        
        new_stocks = set(portfolio_state.weights.keys())
        for instruction in trade_instructions:
            if instruction.direction == "buy":
                new_stocks.add(instruction.stock_code)
            elif instruction.direction == "sell":
                if instruction.stock_code in new_stocks:
                    sell_amount = instruction.amount or (instruction.quantity * instruction.price if instruction.price and instruction.quantity else 0)
                    current_amount = portfolio_state.positions.get(instruction.stock_code, 0)
                    if sell_amount >= current_amount:
                        new_stocks.discard(instruction.stock_code)
        
        stock_count = len(new_stocks)
        min_count, max_count = soft_limits.ideal_stock_count_range
        
        if stock_count < min_count:
            warnings.append(Violation(
                rule_id="E1",
                rule_name="持仓数量下限",
                limit_type=LimitType.SOFT,
                risk_level=RiskLevel.MEDIUM,
                actual_value=stock_count,
                limit_value=min_count,
                message=f"持仓数量 {stock_count} 低于建议下限 {min_count}，组合分散度可能不足"
            ))
        elif stock_count > max_count:
            warnings.append(Violation(
                rule_id="E1",
                rule_name="持仓数量上限",
                limit_type=LimitType.SOFT,
                risk_level=RiskLevel.MEDIUM,
                actual_value=stock_count,
                limit_value=max_count,
                message=f"持仓数量 {stock_count} 超过建议上限 {max_count}，可能增加管理复杂度"
            ))
        
        return warnings
    
    def _check_turnover_rate(
        self,
        trade_instructions: List[TradeInstruction],
        portfolio_state: PortfolioState
    ) -> List[Violation]:
        """检查换手率"""
        warnings = []
        soft_limits = self.risk_limits.soft_limits
        
        total_trade_amount = 0
        for instruction in trade_instructions:
            amount = instruction.amount or (instruction.quantity * instruction.price if instruction.price and instruction.quantity else 0)
            total_trade_amount += amount
        
        turnover_rate = total_trade_amount / portfolio_state.total_capital if portfolio_state.total_capital > 0 else 0
        
        if turnover_rate > soft_limits.max_turnover_rate:
            warnings.append(Violation(
                rule_id="E2",
                rule_name="换手率检查",
                limit_type=LimitType.SOFT,
                risk_level=RiskLevel.MEDIUM,
                actual_value=turnover_rate,
                limit_value=soft_limits.max_turnover_rate,
                message=f"换手率 {turnover_rate:.2%} 超过建议上限 {soft_limits.max_turnover_rate:.2%}"
            ))
        
        return warnings
    
    def _check_liquidity(
        self,
        trade_instructions: List[TradeInstruction],
        portfolio_state: PortfolioState
    ) -> List[Violation]:
        """检查流动性"""
        warnings = []
        liquidity_config = self.risk_limits.liquidity
        
        for instruction in trade_instructions:
            if instruction.direction == "buy":
                amount = instruction.amount or (instruction.quantity * instruction.price if instruction.price and instruction.quantity else 0)
                if amount > liquidity_config.min_daily_turnover:
                    warnings.append(Violation(
                        rule_id="E3",
                        rule_name="流动性检查",
                        limit_type=LimitType.SOFT,
                        risk_level=RiskLevel.LOW,
                        actual_value=amount,
                        limit_value=liquidity_config.min_daily_turnover,
                        message=f"股票 {instruction.stock_code} 单笔交易金额 {amount:.0f} 较大，注意流动性风险",
                        stock_codes=[instruction.stock_code]
                    ))
        
        return warnings
    
    def check_single_trade(
        self,
        instruction: TradeInstruction,
        portfolio_state: PortfolioState
    ) -> PreTradeCheckResult:
        """
        检查单个交易指令
        
        Args:
            instruction: 交易指令
            portfolio_state: 组合状态
            
        Returns:
            PreTradeCheckResult: 检查结果
        """
        return self.check([instruction], portfolio_state)
    
    def quick_check(
        self,
        stock_code: str,
        direction: str,
        amount: float,
        portfolio_state: PortfolioState
    ) -> Tuple[bool, str]:
        """
        快速检查（简化版）
        
        Args:
            stock_code: 股票代码
            direction: 方向 (buy/sell)
            amount: 交易金额
            portfolio_state: 组合状态
            
        Returns:
            (是否通过, 消息)
        """
        instruction = TradeInstruction(
            stock_code=stock_code,
            direction=direction,
            quantity=0,
            amount=amount
        )
        
        result = self.check([instruction], portfolio_state, check_soft_limits=False)
        
        if result.passed:
            return True, "风控检查通过"
        else:
            messages = [v.message for v in result.violations]
            return False, "; ".join(messages)


def create_portfolio_state(
    total_capital: float,
    positions: Dict[str, float],
    industry_mapping: Dict[str, str],
    current_drawdown: float = 0.0
) -> PortfolioState:
    """
    创建组合状态
    
    Args:
        total_capital: 总资金
        positions: 持仓市值 {stock_code: market_value}
        industry_mapping: 行业映射 {stock_code: industry}
        current_drawdown: 当前回撤
        
    Returns:
        PortfolioState: 组合状态
    """
    total_position = sum(positions.values())
    weights = {stock: value / total_capital for stock, value in positions.items()} if total_capital > 0 else {}
    cash = total_capital - total_position
    
    return PortfolioState(
        total_capital=total_capital,
        positions=positions,
        weights=weights,
        industry_mapping=industry_mapping,
        current_drawdown=current_drawdown,
        cash=cash
    )
