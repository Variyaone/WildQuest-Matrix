"""
风控限制配置模块

定义所有风控相关的限制参数和配置。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LimitType(Enum):
    """限制类型"""
    HARD = "hard"
    SOFT = "soft"


@dataclass
class HardLimits:
    """
    硬性限制（不可突破）
    
    这些限制是必须遵守的，违反将直接拒绝交易。
    """
    max_single_stock_weight: float = 0.12
    max_industry_concentration: float = 0.30
    max_total_position: float = 0.95
    max_drawdown: float = 0.15
    min_stock_count: int = 5
    max_stock_count: int = 20
    
    def validate(self) -> List[str]:
        """验证配置合理性"""
        errors = []
        if self.max_single_stock_weight <= 0 or self.max_single_stock_weight > 1:
            errors.append("单票权重上限必须在(0, 1]范围内")
        if self.max_industry_concentration <= 0 or self.max_industry_concentration > 1:
            errors.append("行业集中度上限必须在(0, 1]范围内")
        if self.max_total_position <= 0 or self.max_total_position > 1:
            errors.append("总仓位上限必须在(0, 1]范围内")
        if self.max_drawdown <= 0 or self.max_drawdown > 1:
            errors.append("最大回撤必须在(0, 1]范围内")
        if self.min_stock_count < 1:
            errors.append("最小持股数必须大于0")
        if self.max_stock_count < self.min_stock_count:
            errors.append("最大持股数不能小于最小持股数")
        return errors


@dataclass
class SoftLimits:
    """
    弹性限制（可适度突破）
    
    这些限制是建议性的，违反时会产生警告但不会阻止交易。
    """
    ideal_stock_count_range: tuple = (5, 20)
    max_turnover_rate: float = 0.20
    min_turnover_amount: float = 10_000_000.0
    max_correlation: float = 0.70
    max_beta_exposure: float = 0.30
    
    def validate(self) -> List[str]:
        """验证配置合理性"""
        errors = []
        if self.max_turnover_rate < 0 or self.max_turnover_rate > 1:
            errors.append("换手率上限必须在[0, 1]范围内")
        if self.min_turnover_amount < 0:
            errors.append("最小成交额不能为负")
        if self.max_correlation < 0 or self.max_correlation > 1:
            errors.append("最大相关性必须在[0, 1]范围内")
        if self.max_beta_exposure < 0:
            errors.append("Beta暴露上限不能为负")
        return errors


@dataclass
class AlertThresholds:
    """
    预警阈值配置
    
    当风险指标超过这些阈值时，系统会发送预警通知。
    """
    drawdown_warning: float = 0.10
    drawdown_critical: float = 0.12
    industry_concentration_warning: float = 0.25
    industry_concentration_critical: float = 0.28
    single_stock_weight_warning: float = 0.10
    single_stock_weight_critical: float = 0.11
    volatility_warning: float = 0.03
    volatility_critical: float = 0.05
    position_usage_warning: float = 0.85
    position_usage_critical: float = 0.90
    
    def validate(self) -> List[str]:
        """验证配置合理性"""
        errors = []
        if self.drawdown_warning >= self.drawdown_critical:
            errors.append("回撤预警阈值应小于临界阈值")
        if self.industry_concentration_warning >= self.industry_concentration_critical:
            errors.append("行业集中度预警阈值应小于临界阈值")
        if self.single_stock_weight_warning >= self.single_stock_weight_critical:
            errors.append("单票权重预警阈值应小于临界阈值")
        return errors


@dataclass
class StopLossConfig:
    """
    止损配置
    """
    enabled: bool = True
    individual_stop_loss: float = 0.08
    portfolio_stop_loss: float = 0.15
    trailing_stop_enabled: bool = False
    trailing_stop_ratio: float = 0.10
    time_based_stop_days: int = 0
    
    def validate(self) -> List[str]:
        """验证配置合理性"""
        errors = []
        if self.individual_stop_loss <= 0 or self.individual_stop_loss > 1:
            errors.append("个股止损线必须在(0, 1]范围内")
        if self.portfolio_stop_loss <= 0 or self.portfolio_stop_loss > 1:
            errors.append("组合止损线必须在(0, 1]范围内")
        return errors


@dataclass
class BlacklistConfig:
    """
    黑名单配置
    """
    enabled: bool = True
    stock_blacklist: List[str] = field(default_factory=list)
    industry_blacklist: List[str] = field(default_factory=list)
    auto_update: bool = True
    st_stocks_blocked: bool = True
    suspended_stocks_blocked: bool = True
    new_stock_days: int = 60
    
    def is_stock_blocked(self, stock_code: str) -> bool:
        """检查股票是否在黑名单中"""
        return stock_code in self.stock_blacklist
    
    def is_industry_blocked(self, industry: str) -> bool:
        """检查行业是否在黑名单中"""
        return industry in self.industry_blacklist
    
    def add_to_blacklist(self, stock_code: str, reason: str = ""):
        """添加股票到黑名单"""
        if stock_code not in self.stock_blacklist:
            self.stock_blacklist.append(stock_code)
    
    def remove_from_blacklist(self, stock_code: str):
        """从黑名单移除股票"""
        if stock_code in self.stock_blacklist:
            self.stock_blacklist.remove(stock_code)


@dataclass
class LiquidityConfig:
    """
    流动性配置
    """
    min_daily_turnover: float = 10_000_000.0
    min_turnover_days: int = 20
    max_price_impact: float = 0.02
    min_free_float_ratio: float = 0.05
    
    def validate(self) -> List[str]:
        """验证配置合理性"""
        errors = []
        if self.min_daily_turnover < 0:
            errors.append("最小日成交额不能为负")
        if self.max_price_impact < 0 or self.max_price_impact > 1:
            errors.append("最大价格冲击必须在[0, 1]范围内")
        return errors


@dataclass
class RiskLimits:
    """
    风控限制配置汇总
    
    整合所有风控限制配置，提供统一的配置管理接口。
    """
    hard_limits: HardLimits = field(default_factory=HardLimits)
    soft_limits: SoftLimits = field(default_factory=SoftLimits)
    alert_thresholds: AlertThresholds = field(default_factory=AlertThresholds)
    stop_loss: StopLossConfig = field(default_factory=StopLossConfig)
    blacklist: BlacklistConfig = field(default_factory=BlacklistConfig)
    liquidity: LiquidityConfig = field(default_factory=LiquidityConfig)
    
    def validate_all(self) -> Dict[str, List[str]]:
        """验证所有配置"""
        errors = {
            "hard_limits": self.hard_limits.validate(),
            "soft_limits": self.soft_limits.validate(),
            "alert_thresholds": self.alert_thresholds.validate(),
            "stop_loss": self.stop_loss.validate(),
            "liquidity": self.liquidity.validate()
        }
        return {k: v for k, v in errors.items() if v}
    
    def is_valid(self) -> bool:
        """检查配置是否有效"""
        return len(self.validate_all()) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "hard_limits": {
                "max_single_stock_weight": self.hard_limits.max_single_stock_weight,
                "max_industry_concentration": self.hard_limits.max_industry_concentration,
                "max_total_position": self.hard_limits.max_total_position,
                "max_drawdown": self.hard_limits.max_drawdown,
                "min_stock_count": self.hard_limits.min_stock_count,
                "max_stock_count": self.hard_limits.max_stock_count
            },
            "soft_limits": {
                "ideal_stock_count_range": self.soft_limits.ideal_stock_count_range,
                "max_turnover_rate": self.soft_limits.max_turnover_rate,
                "min_turnover_amount": self.soft_limits.min_turnover_amount,
                "max_correlation": self.soft_limits.max_correlation,
                "max_beta_exposure": self.soft_limits.max_beta_exposure
            },
            "alert_thresholds": {
                "drawdown_warning": self.alert_thresholds.drawdown_warning,
                "drawdown_critical": self.alert_thresholds.drawdown_critical,
                "industry_concentration_warning": self.alert_thresholds.industry_concentration_warning,
                "industry_concentration_critical": self.alert_thresholds.industry_concentration_critical
            },
            "stop_loss": {
                "enabled": self.stop_loss.enabled,
                "individual_stop_loss": self.stop_loss.individual_stop_loss,
                "portfolio_stop_loss": self.stop_loss.portfolio_stop_loss
            },
            "blacklist": {
                "enabled": self.blacklist.enabled,
                "stock_blacklist": self.blacklist.stock_blacklist,
                "industry_blacklist": self.blacklist.industry_blacklist
            },
            "liquidity": {
                "min_daily_turnover": self.liquidity.min_daily_turnover,
                "min_turnover_days": self.liquidity.min_turnover_days,
                "max_price_impact": self.liquidity.max_price_impact
            }
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "RiskLimits":
        """从字典创建配置"""
        hard_dict = config_dict.get("hard_limits", {})
        soft_dict = config_dict.get("soft_limits", {})
        alert_dict = config_dict.get("alert_thresholds", {})
        stop_dict = config_dict.get("stop_loss", {})
        blacklist_dict = config_dict.get("blacklist", {})
        liquidity_dict = config_dict.get("liquidity", {})
        
        return cls(
            hard_limits=HardLimits(
                max_single_stock_weight=hard_dict.get("max_single_stock_weight", 0.12),
                max_industry_concentration=hard_dict.get("max_industry_concentration", 0.30),
                max_total_position=hard_dict.get("max_total_position", 0.95),
                max_drawdown=hard_dict.get("max_drawdown", 0.15),
                min_stock_count=hard_dict.get("min_stock_count", 5),
                max_stock_count=hard_dict.get("max_stock_count", 20)
            ),
            soft_limits=SoftLimits(
                ideal_stock_count_range=tuple(soft_dict.get("ideal_stock_count_range", (5, 20))),
                max_turnover_rate=soft_dict.get("max_turnover_rate", 0.20),
                min_turnover_amount=soft_dict.get("min_turnover_amount", 10_000_000.0),
                max_correlation=soft_dict.get("max_correlation", 0.70),
                max_beta_exposure=soft_dict.get("max_beta_exposure", 0.30)
            ),
            alert_thresholds=AlertThresholds(
                drawdown_warning=alert_dict.get("drawdown_warning", 0.10),
                drawdown_critical=alert_dict.get("drawdown_critical", 0.12),
                industry_concentration_warning=alert_dict.get("industry_concentration_warning", 0.25),
                industry_concentration_critical=alert_dict.get("industry_concentration_critical", 0.28),
                single_stock_weight_warning=alert_dict.get("single_stock_weight_warning", 0.10),
                single_stock_weight_critical=alert_dict.get("single_stock_weight_critical", 0.11),
                volatility_warning=alert_dict.get("volatility_warning", 0.03),
                volatility_critical=alert_dict.get("volatility_critical", 0.05),
                position_usage_warning=alert_dict.get("position_usage_warning", 0.85),
                position_usage_critical=alert_dict.get("position_usage_critical", 0.90)
            ),
            stop_loss=StopLossConfig(
                enabled=stop_dict.get("enabled", True),
                individual_stop_loss=stop_dict.get("individual_stop_loss", 0.08),
                portfolio_stop_loss=stop_dict.get("portfolio_stop_loss", 0.15),
                trailing_stop_enabled=stop_dict.get("trailing_stop_enabled", False),
                trailing_stop_ratio=stop_dict.get("trailing_stop_ratio", 0.10),
                time_based_stop_days=stop_dict.get("time_based_stop_days", 0)
            ),
            blacklist=BlacklistConfig(
                enabled=blacklist_dict.get("enabled", True),
                stock_blacklist=blacklist_dict.get("stock_blacklist", []),
                industry_blacklist=blacklist_dict.get("industry_blacklist", []),
                auto_update=blacklist_dict.get("auto_update", True),
                st_stocks_blocked=blacklist_dict.get("st_stocks_blocked", True),
                suspended_stocks_blocked=blacklist_dict.get("suspended_stocks_blocked", True),
                new_stock_days=blacklist_dict.get("new_stock_days", 60)
            ),
            liquidity=LiquidityConfig(
                min_daily_turnover=liquidity_dict.get("min_daily_turnover", 10_000_000.0),
                min_turnover_days=liquidity_dict.get("min_turnover_days", 20),
                max_price_impact=liquidity_dict.get("max_price_impact", 0.02),
                min_free_float_ratio=liquidity_dict.get("min_free_float_ratio", 0.05)
            )
        )


_default_risk_limits: Optional[RiskLimits] = None


def get_risk_limits() -> RiskLimits:
    """获取全局风控限制配置"""
    global _default_risk_limits
    if _default_risk_limits is None:
        _default_risk_limits = RiskLimits()
    return _default_risk_limits


def set_risk_limits(limits: RiskLimits):
    """设置全局风控限制配置"""
    global _default_risk_limits
    _default_risk_limits = limits


def reset_risk_limits():
    """重置全局风控限制配置"""
    global _default_risk_limits
    _default_risk_limits = None
