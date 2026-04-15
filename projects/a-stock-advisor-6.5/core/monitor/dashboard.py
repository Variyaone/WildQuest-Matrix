"""
监控仪表盘模块

提供实时监控仪表盘，展示策略运行状态、因子表现、信号质量等。
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import pandas as pd
import numpy as np

from core.infrastructure.logging import get_logger


class RefreshFrequency(Enum):
    """刷新频率"""
    REALTIME = "realtime"  # 5分钟
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class PanelType(Enum):
    """面板类型"""
    PORTFOLIO = "portfolio"
    FACTOR = "factor"
    SIGNAL = "signal"
    STRATEGY = "strategy"
    TRADING = "trading"
    SYSTEM = "system"


@dataclass
class DashboardPanel:
    """仪表盘面板"""
    panel_id: str
    panel_type: PanelType
    title: str
    data: Dict[str, Any] = field(default_factory=dict)
    last_update: Optional[datetime] = None
    refresh_frequency: RefreshFrequency = RefreshFrequency.REALTIME
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result["panel_type"] = self.panel_type.value
        result["refresh_frequency"] = self.refresh_frequency.value
        result["last_update"] = self.last_update.isoformat() if self.last_update else None
        return result


@dataclass
class PortfolioOverview:
    """组合概览"""
    total_value: float = 0.0
    daily_return: float = 0.0
    cumulative_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    positions: Dict[str, float] = field(default_factory=dict)
    industry_weights: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FactorOverview:
    """因子概览"""
    factor_id: str
    factor_name: str
    ic_5d: float = 0.0
    ic_20d: float = 0.0
    ic_60d: float = 0.0
    ic_trend: str = "stable"
    score: float = 0.0
    decay_warning: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SignalOverview:
    """信号概览"""
    signal_id: str
    signal_name: str
    win_rate: float = 0.0
    avg_return: float = 0.0
    strength: float = 0.0
    quality_score: float = 0.0
    trigger_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyOverview:
    """策略概览"""
    strategy_id: str
    strategy_name: str
    health_score: float = 0.0
    health_level: str = "good"
    daily_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TradingOverview:
    """交易概览"""
    date: str
    total_orders: int = 0
    filled_orders: int = 0
    fill_rate: float = 0.0
    turnover_rate: float = 0.0
    total_commission: float = 0.0
    total_slippage: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SystemOverview:
    """系统概览"""
    data_status: str = "normal"
    task_status: str = "normal"
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    last_data_update: Optional[str] = None
    alert_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Dashboard:
    """监控仪表盘"""
    
    def __init__(self, dashboard_id: str, name: str = "Main Dashboard"):
        self.dashboard_id = dashboard_id
        self.name = name
        self.panels: Dict[str, DashboardPanel] = {}
        self.logger = get_logger("monitor.dashboard")
        self._last_refresh: Optional[datetime] = None
        
        self._init_default_panels()
    
    def _init_default_panels(self):
        """初始化默认面板"""
        default_panels = [
            ("portfolio_overview", PanelType.PORTFOLIO, "组合概览", RefreshFrequency.REALTIME),
            ("factor_monitor", PanelType.FACTOR, "因子监控", RefreshFrequency.DAILY),
            ("signal_monitor", PanelType.SIGNAL, "信号监控", RefreshFrequency.DAILY),
            ("strategy_monitor", PanelType.STRATEGY, "策略监控", RefreshFrequency.DAILY),
            ("trading_monitor", PanelType.TRADING, "交易监控", RefreshFrequency.REALTIME),
            ("system_monitor", PanelType.SYSTEM, "系统监控", RefreshFrequency.REALTIME),
        ]
        
        for panel_id, panel_type, title, freq in default_panels:
            self.panels[panel_id] = DashboardPanel(
                panel_id=panel_id,
                panel_type=panel_type,
                title=title,
                refresh_frequency=freq
            )
    
    def update_panel(self, panel_id: str, data: Dict[str, Any]) -> bool:
        """更新面板数据"""
        if panel_id not in self.panels:
            self.logger.warning(f"面板不存在: {panel_id}")
            return False
        
        self.panels[panel_id].data = data
        self.panels[panel_id].last_update = datetime.now()
        self.logger.debug(f"更新面板: {panel_id}")
        return True
    
    def get_panel(self, panel_id: str) -> Optional[DashboardPanel]:
        """获取面板"""
        return self.panels.get(panel_id)
    
    def get_all_panels(self) -> List[DashboardPanel]:
        """获取所有面板"""
        return list(self.panels.values())
    
    def refresh(self, panel_types: Optional[List[PanelType]] = None):
        """刷新面板"""
        now = datetime.now()
        
        for panel in self.panels.values():
            if panel_types and panel.panel_type not in panel_types:
                continue
            
            should_refresh = self._should_refresh(panel, now)
            if should_refresh:
                self._refresh_panel(panel)
        
        self._last_refresh = now
    
    def _should_refresh(self, panel: DashboardPanel, now: datetime) -> bool:
        """判断是否需要刷新"""
        if panel.last_update is None:
            return True
        
        elapsed = now - panel.last_update
        
        if panel.refresh_frequency == RefreshFrequency.REALTIME:
            return elapsed > timedelta(minutes=5)
        elif panel.refresh_frequency == RefreshFrequency.DAILY:
            return elapsed > timedelta(days=1)
        elif panel.refresh_frequency == RefreshFrequency.WEEKLY:
            return elapsed > timedelta(weeks=1)
        elif panel.refresh_frequency == RefreshFrequency.MONTHLY:
            return elapsed > timedelta(days=30)
        
        return False
    
    def _refresh_panel(self, panel: DashboardPanel):
        """刷新单个面板"""
        if panel.panel_type == PanelType.PORTFOLIO:
            self._refresh_portfolio_panel(panel)
        elif panel.panel_type == PanelType.FACTOR:
            self._refresh_factor_panel(panel)
        elif panel.panel_type == PanelType.SIGNAL:
            self._refresh_signal_panel(panel)
        elif panel.panel_type == PanelType.STRATEGY:
            self._refresh_strategy_panel(panel)
        elif panel.panel_type == PanelType.TRADING:
            self._refresh_trading_panel(panel)
        elif panel.panel_type == PanelType.SYSTEM:
            self._refresh_system_panel(panel)
    
    def _refresh_portfolio_panel(self, panel: DashboardPanel):
        """刷新组合面板"""
        pass
    
    def _refresh_factor_panel(self, panel: DashboardPanel):
        """刷新因子面板"""
        pass
    
    def _refresh_signal_panel(self, panel: DashboardPanel):
        """刷新信号面板"""
        pass
    
    def _refresh_strategy_panel(self, panel: DashboardPanel):
        """刷新策略面板"""
        pass
    
    def _refresh_trading_panel(self, panel: DashboardPanel):
        """刷新交易面板"""
        pass
    
    def _refresh_system_panel(self, panel: DashboardPanel):
        """刷新系统面板"""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "dashboard_id": self.dashboard_id,
            "name": self.name,
            "panels": [p.to_dict() for p in self.panels.values()],
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None
        }
    
    def to_json(self) -> str:
        """转换为JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class DashboardManager:
    """仪表盘管理器"""
    
    def __init__(self, storage_path: str = "./data/dashboards"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.dashboards: Dict[str, Dashboard] = {}
        self.logger = get_logger("monitor.dashboard_manager")
    
    def create_dashboard(self, dashboard_id: str, name: str = "Main Dashboard") -> Dashboard:
        """创建仪表盘"""
        if dashboard_id in self.dashboards:
            self.logger.warning(f"仪表盘已存在: {dashboard_id}")
            return self.dashboards[dashboard_id]
        
        dashboard = Dashboard(dashboard_id, name)
        self.dashboards[dashboard_id] = dashboard
        self.logger.info(f"创建仪表盘: {dashboard_id}")
        return dashboard
    
    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """获取仪表盘"""
        return self.dashboards.get(dashboard_id)
    
    def delete_dashboard(self, dashboard_id: str) -> bool:
        """删除仪表盘"""
        if dashboard_id not in self.dashboards:
            return False
        
        del self.dashboards[dashboard_id]
        self.logger.info(f"删除仪表盘: {dashboard_id}")
        return True
    
    def save_dashboard(self, dashboard_id: str) -> bool:
        """保存仪表盘"""
        dashboard = self.get_dashboard(dashboard_id)
        if not dashboard:
            return False
        
        file_path = self.storage_path / f"{dashboard_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(dashboard.to_json())
        
        self.logger.info(f"保存仪表盘: {dashboard_id}")
        return True
    
    def load_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """加载仪表盘"""
        file_path = self.storage_path / f"{dashboard_id}.json"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            dashboard = Dashboard(data["dashboard_id"], data["name"])
            
            for panel_data in data["panels"]:
                panel = DashboardPanel(
                    panel_id=panel_data["panel_id"],
                    panel_type=PanelType(panel_data["panel_type"]),
                    title=panel_data["title"],
                    data=panel_data["data"],
                    refresh_frequency=RefreshFrequency(panel_data["refresh_frequency"])
                )
                if panel_data["last_update"]:
                    panel.last_update = datetime.fromisoformat(panel_data["last_update"])
                dashboard.panels[panel.panel_id] = panel
            
            self.dashboards[dashboard_id] = dashboard
            self.logger.info(f"加载仪表盘: {dashboard_id}")
            return dashboard
        
        except Exception as e:
            self.logger.error(f"加载仪表盘失败: {dashboard_id}, 错误: {e}")
            return None
    
    def refresh_all(self, panel_types: Optional[List[PanelType]] = None):
        """刷新所有仪表盘"""
        for dashboard in self.dashboards.values():
            dashboard.refresh(panel_types)
        
        self.logger.info("刷新所有仪表盘")
