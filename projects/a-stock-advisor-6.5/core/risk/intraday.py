"""
事中风控模块

实时监控交易和持仓风险，包括：
- 实时盈亏监控
- 持仓风险监控
- 异常交易检测
- 紧急止损触发
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, time
from enum import Enum
from collections import deque

from .limits import RiskLimits, get_risk_limits, RiskLevel
from .metrics import RiskMetricsCalculator, RiskMetricsResult


class MonitorStatus(Enum):
    """监控状态"""
    NORMAL = "normal"
    WARNING = "warning"
    ALERT = "alert"
    CRITICAL = "critical"
    STOPPED = "stopped"


class AlertAction(Enum):
    """预警动作"""
    NOTIFY = "notify"
    REDUCE_POSITION = "reduce_position"
    STOP_LOSS = "stop_loss"
    FORCE_SELL = "force_sell"
    HALT_TRADING = "halt_trading"


@dataclass
class PositionRisk:
    """持仓风险"""
    stock_code: str
    quantity: int
    cost_price: float
    current_price: float
    market_value: float
    weight: float
    pnl: float
    pnl_ratio: float
    day_pnl: float
    day_pnl_ratio: float
    industry: str = ""
    risk_level: RiskLevel = RiskLevel.LOW
    alerts: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "stock_code": self.stock_code,
            "quantity": self.quantity,
            "cost_price": self.cost_price,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "weight": self.weight,
            "pnl": self.pnl,
            "pnl_ratio": self.pnl_ratio,
            "day_pnl": self.day_pnl,
            "day_pnl_ratio": self.day_pnl_ratio,
            "industry": self.industry,
            "risk_level": self.risk_level.value,
            "alerts": self.alerts
        }


@dataclass
class PortfolioRiskSnapshot:
    """组合风险快照"""
    timestamp: datetime
    total_capital: float
    total_position: float
    cash: float
    position_ratio: float
    total_pnl: float
    total_pnl_ratio: float
    day_pnl: float
    day_pnl_ratio: float
    current_drawdown: float
    max_drawdown: float
    position_risks: Dict[str, PositionRisk] = field(default_factory=dict)
    industry_concentration: Dict[str, float] = field(default_factory=dict)
    risk_metrics: Optional[RiskMetricsResult] = None
    status: MonitorStatus = MonitorStatus.NORMAL
    alerts: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_capital": self.total_capital,
            "total_position": self.total_position,
            "cash": self.cash,
            "position_ratio": self.position_ratio,
            "total_pnl": self.total_pnl,
            "total_pnl_ratio": self.total_pnl_ratio,
            "day_pnl": self.day_pnl,
            "day_pnl_ratio": self.day_pnl_ratio,
            "current_drawdown": self.current_drawdown,
            "max_drawdown": self.max_drawdown,
            "position_risks": {k: v.to_dict() for k, v in self.position_risks.items()},
            "industry_concentration": self.industry_concentration,
            "risk_metrics": self.risk_metrics.to_dict() if self.risk_metrics else None,
            "status": self.status.value,
            "alerts": self.alerts
        }


@dataclass
class IntradayAlert:
    """盘中预警"""
    alert_id: str
    alert_type: str
    risk_level: RiskLevel
    message: str
    stock_codes: List[str] = field(default_factory=list)
    action: AlertAction = AlertAction.NOTIFY
    details: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type,
            "risk_level": self.risk_level.value,
            "message": self.message,
            "stock_codes": self.stock_codes,
            "action": self.action.value,
            "details": self.details,
            "created_at": self.created_at.isoformat(),
            "acknowledged": self.acknowledged,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None
        }


@dataclass
class StopLossTrigger:
    """止损触发记录"""
    stock_code: str
    trigger_type: str
    trigger_price: float
    trigger_time: datetime
    stop_loss_price: float
    pnl_ratio: float
    action_taken: str
    quantity: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "stock_code": self.stock_code,
            "trigger_type": self.trigger_type,
            "trigger_price": self.trigger_price,
            "trigger_time": self.trigger_time.isoformat(),
            "stop_loss_price": self.stop_loss_price,
            "pnl_ratio": self.pnl_ratio,
            "action_taken": self.action_taken,
            "quantity": self.quantity
        }


class IntradayRiskMonitor:
    """
    盘中风控监控器
    
    实时监控持仓风险，触发预警和止损。
    """
    
    def __init__(
        self,
        risk_limits: Optional[RiskLimits] = None,
        metrics_calculator: Optional[RiskMetricsCalculator] = None
    ):
        self.risk_limits = risk_limits or get_risk_limits()
        self.metrics_calculator = metrics_calculator or RiskMetricsCalculator()
        
        self._snapshots: deque = deque(maxlen=1000)
        self._alerts: List[IntradayAlert] = []
        self._stop_loss_triggers: List[StopLossTrigger] = []
        self._alert_handlers: List[Callable] = []
        self._status = MonitorStatus.NORMAL
        self._last_update: Optional[datetime] = None
        self._alert_counter = 0
    
    def add_alert_handler(self, handler: Callable[[IntradayAlert], None]):
        """添加预警处理器"""
        self._alert_handlers.append(handler)
    
    def update(
        self,
        positions: Dict[str, Dict[str, Any]],
        prices: Dict[str, float],
        total_capital: float,
        industry_mapping: Optional[Dict[str, str]] = None,
        historical_returns: Optional[np.ndarray] = None,
        historical_nav: Optional[np.ndarray] = None
    ) -> PortfolioRiskSnapshot:
        """
        更新监控状态
        
        Args:
            positions: 持仓信息 {stock_code: {quantity, cost_price, ...}}
            prices: 当前价格 {stock_code: price}
            total_capital: 总资金
            industry_mapping: 行业映射
            historical_returns: 历史收益率序列
            historical_nav: 历史净值序列
            
        Returns:
            PortfolioRiskSnapshot: 组合风险快照
        """
        now = datetime.now()
        
        position_risks = {}
        total_position = 0.0
        total_pnl = 0.0
        day_pnl = 0.0
        industry_weights = {}
        
        for stock_code, pos_info in positions.items():
            quantity = pos_info.get("quantity", 0)
            cost_price = pos_info.get("cost_price", 0)
            day_cost = pos_info.get("day_cost", cost_price)
            
            current_price = prices.get(stock_code, cost_price)
            market_value = quantity * current_price
            weight = market_value / total_capital if total_capital > 0 else 0
            
            pnl = (current_price - cost_price) * quantity
            pnl_ratio = (current_price - cost_price) / cost_price if cost_price > 0 else 0
            
            day_pnl_stock = (current_price - day_cost) * quantity
            day_pnl_ratio_stock = (current_price - day_cost) / day_cost if day_cost > 0 else 0
            
            industry = ""
            if industry_mapping:
                industry = industry_mapping.get(stock_code, "")
                industry_weights[industry] = industry_weights.get(industry, 0) + weight
            
            position_risk = PositionRisk(
                stock_code=stock_code,
                quantity=quantity,
                cost_price=cost_price,
                current_price=current_price,
                market_value=market_value,
                weight=weight,
                pnl=pnl,
                pnl_ratio=pnl_ratio,
                day_pnl=day_pnl_stock,
                day_pnl_ratio=day_pnl_ratio_stock,
                industry=industry
            )
            
            position_risks[stock_code] = position_risk
            total_position += market_value
            total_pnl += pnl
            day_pnl += day_pnl_stock
        
        cash = total_capital - total_position
        position_ratio = total_position / total_capital if total_capital > 0 else 0
        
        risk_metrics = None
        if historical_returns is not None and historical_nav is not None:
            risk_metrics = self.metrics_calculator.calculate_all_metrics(
                historical_returns, historical_nav
            )
        
        current_drawdown = 0.0
        max_drawdown = 0.0
        if risk_metrics:
            current_drawdown = risk_metrics.current_drawdown
            max_drawdown = risk_metrics.max_drawdown
        
        snapshot = PortfolioRiskSnapshot(
            timestamp=now,
            total_capital=total_capital,
            total_position=total_position,
            cash=cash,
            position_ratio=position_ratio,
            total_pnl=total_pnl,
            total_pnl_ratio=total_pnl / total_capital if total_capital > 0 else 0,
            day_pnl=day_pnl,
            day_pnl_ratio=day_pnl / total_capital if total_capital > 0 else 0,
            current_drawdown=current_drawdown,
            max_drawdown=max_drawdown,
            position_risks=position_risks,
            industry_concentration=industry_weights,
            risk_metrics=risk_metrics
        )
        
        self._check_risks(snapshot)
        self._snapshots.append(snapshot)
        self._last_update = now
        
        return snapshot
    
    def _check_risks(self, snapshot: PortfolioRiskSnapshot):
        """检查风险并生成预警"""
        alerts = []
        thresholds = self.risk_limits.alert_thresholds
        hard_limits = self.risk_limits.hard_limits
        
        if snapshot.current_drawdown >= thresholds.drawdown_critical:
            alert = self._create_alert(
                alert_type="drawdown_critical",
                risk_level=RiskLevel.CRITICAL,
                message=f"回撤达到临界水平: {snapshot.current_drawdown:.2%}",
                action=AlertAction.STOP_LOSS,
                details={"drawdown": snapshot.current_drawdown}
            )
            alerts.append(alert)
            snapshot.status = MonitorStatus.CRITICAL
        elif snapshot.current_drawdown >= thresholds.drawdown_warning:
            alert = self._create_alert(
                alert_type="drawdown_warning",
                risk_level=RiskLevel.HIGH,
                message=f"回撤达到预警水平: {snapshot.current_drawdown:.2%}",
                action=AlertAction.NOTIFY,
                details={"drawdown": snapshot.current_drawdown}
            )
            alerts.append(alert)
            if snapshot.status == MonitorStatus.NORMAL:
                snapshot.status = MonitorStatus.WARNING
        
        for industry, weight in snapshot.industry_concentration.items():
            if weight >= thresholds.industry_concentration_critical:
                alert = self._create_alert(
                    alert_type="industry_concentration_critical",
                    risk_level=RiskLevel.HIGH,
                    message=f"行业 {industry} 集中度达到临界水平: {weight:.2%}",
                    action=AlertAction.REDUCE_POSITION,
                    details={"industry": industry, "weight": weight}
                )
                alerts.append(alert)
            elif weight >= thresholds.industry_concentration_warning:
                alert = self._create_alert(
                    alert_type="industry_concentration_warning",
                    risk_level=RiskLevel.MEDIUM,
                    message=f"行业 {industry} 集中度达到预警水平: {weight:.2%}",
                    action=AlertAction.NOTIFY,
                    details={"industry": industry, "weight": weight}
                )
                alerts.append(alert)
        
        for stock_code, pos_risk in snapshot.position_risks.items():
            if pos_risk.weight >= thresholds.single_stock_weight_critical:
                alert = self._create_alert(
                    alert_type="single_stock_weight_critical",
                    risk_level=RiskLevel.HIGH,
                    message=f"股票 {stock_code} 权重达到临界水平: {pos_risk.weight:.2%}",
                    action=AlertAction.REDUCE_POSITION,
                    stock_codes=[stock_code],
                    details={"weight": pos_risk.weight}
                )
                alerts.append(alert)
            
            if self.risk_limits.stop_loss.enabled:
                if pos_risk.pnl_ratio <= -self.risk_limits.stop_loss.individual_stop_loss:
                    alert = self._create_alert(
                        alert_type="individual_stop_loss",
                        risk_level=RiskLevel.CRITICAL,
                        message=f"股票 {stock_code} 触发止损: 亏损 {pos_risk.pnl_ratio:.2%}",
                        action=AlertAction.STOP_LOSS,
                        stock_codes=[stock_code],
                        details={"pnl_ratio": pos_risk.pnl_ratio}
                    )
                    alerts.append(alert)
                    pos_risk.alerts.append("触发止损")
                    pos_risk.risk_level = RiskLevel.CRITICAL
        
        if snapshot.position_ratio >= thresholds.position_usage_critical:
            alert = self._create_alert(
                alert_type="position_usage_critical",
                risk_level=RiskLevel.HIGH,
                message=f"仓位使用率达到临界水平: {snapshot.position_ratio:.2%}",
                action=AlertAction.NOTIFY,
                details={"position_ratio": snapshot.position_ratio}
            )
            alerts.append(alert)
        
        for alert in alerts:
            snapshot.alerts.append(alert.message)
            self._alerts.append(alert)
            self._dispatch_alert(alert)
    
    def _create_alert(
        self,
        alert_type: str,
        risk_level: RiskLevel,
        message: str,
        action: AlertAction = AlertAction.NOTIFY,
        stock_codes: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> IntradayAlert:
        """创建预警"""
        self._alert_counter += 1
        alert_id = f"ALERT-{datetime.now().strftime('%Y%m%d')}-{self._alert_counter:04d}"
        
        return IntradayAlert(
            alert_id=alert_id,
            alert_type=alert_type,
            risk_level=risk_level,
            message=message,
            stock_codes=stock_codes or [],
            action=action,
            details=details or {}
        )
    
    def _dispatch_alert(self, alert: IntradayAlert):
        """分发预警"""
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                pass
    
    def check_stop_loss(
        self,
        positions: Dict[str, Dict[str, Any]],
        prices: Dict[str, float]
    ) -> List[StopLossTrigger]:
        """
        检查止损触发
        
        Args:
            positions: 持仓信息
            prices: 当前价格
            
        Returns:
            List[StopLossTrigger]: 止损触发列表
        """
        triggers = []
        stop_loss_config = self.risk_limits.stop_loss
        
        if not stop_loss_config.enabled:
            return triggers
        
        for stock_code, pos_info in positions.items():
            quantity = pos_info.get("quantity", 0)
            cost_price = pos_info.get("cost_price", 0)
            current_price = prices.get(stock_code, cost_price)
            
            if cost_price <= 0 or quantity <= 0:
                continue
            
            pnl_ratio = (current_price - cost_price) / cost_price
            
            if pnl_ratio <= -stop_loss_config.individual_stop_loss:
                trigger = StopLossTrigger(
                    stock_code=stock_code,
                    trigger_type="individual_stop_loss",
                    trigger_price=current_price,
                    trigger_time=datetime.now(),
                    stop_loss_price=cost_price * (1 - stop_loss_config.individual_stop_loss),
                    pnl_ratio=pnl_ratio,
                    action_taken="pending",
                    quantity=quantity
                )
                triggers.append(trigger)
                self._stop_loss_triggers.append(trigger)
        
        return triggers
    
    def get_current_snapshot(self) -> Optional[PortfolioRiskSnapshot]:
        """获取当前快照"""
        return self._snapshots[-1] if self._snapshots else None
    
    def get_recent_snapshots(self, count: int = 10) -> List[PortfolioRiskSnapshot]:
        """获取最近的快照"""
        return list(self._snapshots)[-count:]
    
    def get_active_alerts(self) -> List[IntradayAlert]:
        """获取未确认的预警"""
        return [a for a in self._alerts if not a.acknowledged]
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认预警"""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_at = datetime.now()
                return True
        return False
    
    def get_status(self) -> MonitorStatus:
        """获取当前状态"""
        snapshot = self.get_current_snapshot()
        return snapshot.status if snapshot else self._status
    
    def get_summary(self) -> Dict[str, Any]:
        """获取监控摘要"""
        snapshot = self.get_current_snapshot()
        
        return {
            "status": self.get_status().value,
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "total_alerts": len(self._alerts),
            "active_alerts": len(self.get_active_alerts()),
            "stop_loss_triggers": len(self._stop_loss_triggers),
            "current_snapshot": snapshot.to_dict() if snapshot else None
        }


class TradingActivityMonitor:
    """
    交易活动监控器
    
    监控异常交易行为。
    """
    
    def __init__(
        self,
        max_trades_per_minute: int = 10,
        max_volume_ratio: float = 0.1,
        max_trade_amount: float = 1_000_000.0
    ):
        self.max_trades_per_minute = max_trades_per_minute
        self.max_volume_ratio = max_volume_ratio
        self.max_trade_amount = max_trade_amount
        
        self._trade_history: deque = deque(maxlen=10000)
        self._anomaly_alerts: List[Dict[str, Any]] = []
    
    def record_trade(
        self,
        stock_code: str,
        direction: str,
        quantity: int,
        price: float,
        amount: float,
        timestamp: Optional[datetime] = None
    ):
        """记录交易"""
        trade = {
            "stock_code": stock_code,
            "direction": direction,
            "quantity": quantity,
            "price": price,
            "amount": amount,
            "timestamp": timestamp or datetime.now()
        }
        self._trade_history.append(trade)
        
        self._check_anomaly(trade)
    
    def _check_anomaly(self, trade: Dict[str, Any]):
        """检查异常交易"""
        now = trade["timestamp"]
        one_minute_ago = now - timedelta(minutes=1)
        
        recent_trades = [
            t for t in self._trade_history
            if t["timestamp"] >= one_minute_ago
        ]
        
        if len(recent_trades) > self.max_trades_per_minute:
            self._anomaly_alerts.append({
                "type": "high_frequency",
                "message": f"交易频率异常: 1分钟内 {len(recent_trades)} 笔交易",
                "timestamp": now,
                "details": {"trade_count": len(recent_trades)}
            })
        
        if trade["amount"] > self.max_trade_amount:
            self._anomaly_alerts.append({
                "type": "large_trade",
                "message": f"大额交易: {trade['stock_code']} 金额 {trade['amount']:.0f}",
                "timestamp": now,
                "details": trade
            })
    
    def get_anomalies(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """获取异常记录"""
        if since:
            return [a for a in self._anomaly_alerts if a["timestamp"] >= since]
        return self._anomaly_alerts.copy()
    
    def get_trade_statistics(self, period_minutes: int = 60) -> Dict[str, Any]:
        """获取交易统计"""
        now = datetime.now()
        start_time = now - timedelta(minutes=period_minutes)
        
        recent_trades = [
            t for t in self._trade_history
            if t["timestamp"] >= start_time
        ]
        
        if not recent_trades:
            return {
                "period_minutes": period_minutes,
                "total_trades": 0,
                "total_amount": 0,
                "buy_count": 0,
                "sell_count": 0
            }
        
        total_amount = sum(t["amount"] for t in recent_trades)
        buy_count = sum(1 for t in recent_trades if t["direction"] == "buy")
        sell_count = sum(1 for t in recent_trades if t["direction"] == "sell")
        
        return {
            "period_minutes": period_minutes,
            "total_trades": len(recent_trades),
            "total_amount": total_amount,
            "buy_count": buy_count,
            "sell_count": sell_count,
            "avg_trade_amount": total_amount / len(recent_trades)
        }


from datetime import timedelta
