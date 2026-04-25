"""
信号看板模块

借鉴聚宽因子看板设计，提供统一的信号分析入口。
特点：
- 筛选条件集中管理
- 多维度灵活过滤
- 默认值优化
- 配置持久化
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from enum import Enum
import json


class SignalTypeFilter(Enum):
    """信号类型筛选选项"""
    STOCK_SELECTION = "选股信号"
    TIMING = "择时信号"
    RISK_ALERT = "风险预警"
    REBALANCE = "调仓信号"
    CUSTOM = "自定义信号"


class SignalDirectionFilter(Enum):
    """信号方向筛选选项"""
    BUY = "买入"
    SELL = "卖出"
    HOLD = "持有"
    REDUCE = "减仓"
    INCREASE = "加仓"


class SignalStrengthFilter(Enum):
    """信号强度筛选选项"""
    STRONG = "强"
    MEDIUM = "中"
    WEAK = "弱"


@dataclass
class SignalFilterConfig:
    """
    信号筛选配置
    
    集中管理所有筛选参数，支持持久化存储。
    """
    signal_types: List[str] = field(default_factory=lambda: ["选股信号", "择时信号"])
    directions: List[str] = field(default_factory=lambda: ["买入", "持有"])
    strengths: List[str] = field(default_factory=lambda: ["强", "中"])
    statuses: List[str] = field(default_factory=lambda: ["active"])
    
    min_win_rate: Optional[float] = None
    min_avg_return: Optional[float] = None
    max_drawdown: Optional[float] = None
    min_total_signals: Optional[int] = None
    
    sort_by: str = "win_rate"
    sort_order: str = "desc"
    
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignalFilterConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


DEFAULT_SIGNAL_FILTER_CONFIG = SignalFilterConfig(
    signal_types=["选股信号", "择时信号"],
    directions=["买入", "持有"],
    strengths=["强", "中"],
    statuses=["active"],
    sort_by="win_rate",
)


class SignalDashboardConfigManager:
    """
    信号看板配置管理器
    
    负责配置的持久化存储和加载。
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path.home() / ".openclaw" / "signal_dashboard"
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "filter_config.json"
    
    def save(self, config: SignalFilterConfig, name: str = "default") -> bool:
        """保存配置"""
        try:
            config.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            configs = self.load_all()
            configs[name] = config.to_dict()
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(configs, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception:
            return False
    
    def load(self, name: str = "default") -> SignalFilterConfig:
        """加载配置"""
        try:
            configs = self.load_all()
            if name in configs:
                return SignalFilterConfig.from_dict(configs[name])
        except Exception:
            pass
        
        return DEFAULT_SIGNAL_FILTER_CONFIG
    
    def load_all(self) -> Dict[str, Any]:
        """加载所有配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        
        return {}
    
    def delete(self, name: str) -> bool:
        """删除配置"""
        try:
            configs = self.load_all()
            if name in configs:
                del configs[name]
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(configs, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
    
    def list_configs(self) -> List[str]:
        """列出所有配置名称"""
        configs = self.load_all()
        return list(configs.keys())


@dataclass
class SignalDashboardRow:
    """信号看板表格行"""
    signal_id: str
    signal_name: str
    signal_type: str
    direction: str
    strength: str
    status: str
    
    win_rate: float = 0.0
    avg_return: float = 0.0
    max_drawdown: float = 0.0
    total_signals: int = 0
    winning_signals: int = 0
    avg_holding_days: float = 0.0
    
    factor_count: int = 0
    confidence: float = 0.0
    
    score: float = 0.0
    rank: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def get_return_class(self) -> str:
        """获取收益的颜色类"""
        return "positive" if self.avg_return > 0 else "negative"
    
    def get_win_rate_class(self) -> str:
        """获取胜率的颜色类"""
        return "positive" if self.win_rate > 0.5 else "negative"


@dataclass
class SignalDashboardResult:
    """信号看板分析结果"""
    config: SignalFilterConfig
    rows: List[SignalDashboardRow] = field(default_factory=list)
    total_signals: int = 0
    filtered_signals: int = 0
    analysis_time: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    duration_seconds: float = 0.0
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "rows": [r.to_dict() for r in self.rows],
            "total_signals": self.total_signals,
            "filtered_signals": self.filtered_signals,
            "analysis_time": self.analysis_time,
            "duration_seconds": self.duration_seconds,
            "warnings": self.warnings,
        }
    
    def sort_rows(self, by: str = "win_rate", order: str = "desc"):
        """排序结果行"""
        reverse = (order == "desc")
        
        if by == "win_rate":
            self.rows.sort(key=lambda x: x.win_rate, reverse=reverse)
        elif by == "avg_return":
            self.rows.sort(key=lambda x: x.avg_return, reverse=reverse)
        elif by == "total_signals":
            self.rows.sort(key=lambda x: x.total_signals, reverse=reverse)
        elif by == "max_drawdown":
            self.rows.sort(key=lambda x: x.max_drawdown, reverse=not reverse)
        elif by == "score":
            self.rows.sort(key=lambda x: x.score, reverse=reverse)
        
        for i, row in enumerate(self.rows):
            row.rank = i + 1


class SignalDashboard:
    """
    信号看板
    
    统一的信号分析入口，借鉴聚宽设计。
    """
    
    SIGNAL_TYPE_OPTIONS = [
        ("选股信号", "股票选择信号"),
        ("择时信号", "市场择时信号"),
        ("风险预警", "风险预警信号"),
        ("调仓信号", "调仓信号"),
        ("自定义信号", "用户自定义"),
    ]
    
    DIRECTION_OPTIONS = [
        ("买入", "买入信号"),
        ("卖出", "卖出信号"),
        ("持有", "持有信号"),
        ("减仓", "减仓信号"),
        ("加仓", "加仓信号"),
    ]
    
    STRENGTH_OPTIONS = [
        ("强", "强信号"),
        ("中", "中等信号"),
        ("弱", "弱信号"),
    ]
    
    STATUS_OPTIONS = [
        ("active", "活跃"),
        ("testing", "测试中"),
        ("inactive", "停用"),
        ("deprecated", "已废弃"),
    ]
    
    SORT_OPTIONS = [
        ("win_rate", "胜率"),
        ("avg_return", "平均收益"),
        ("total_signals", "信号数量"),
        ("max_drawdown", "最大回撤"),
        ("score", "综合得分"),
    ]
    
    def __init__(self):
        self.config_manager = SignalDashboardConfigManager()
        self.current_config: SignalFilterConfig = self.config_manager.load()
    
    def get_config(self) -> SignalFilterConfig:
        """获取当前配置"""
        return self.current_config
    
    def update_config(self, **kwargs) -> SignalFilterConfig:
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.current_config, key):
                setattr(self.current_config, key, value)
        
        self.current_config.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self.current_config
    
    def save_config(self, name: str = "default") -> bool:
        """保存当前配置"""
        return self.config_manager.save(self.current_config, name)
    
    def load_config(self, name: str = "default") -> SignalFilterConfig:
        """加载配置"""
        self.current_config = self.config_manager.load(name)
        return self.current_config
    
    def reset_config(self) -> SignalFilterConfig:
        """重置为默认配置"""
        self.current_config = DEFAULT_SIGNAL_FILTER_CONFIG
        return self.current_config
    
    def run_analysis(self) -> SignalDashboardResult:
        """
        运行信号分析
        
        根据当前配置筛选信号并计算绩效指标。
        """
        import time
        start_time = time.time()
        
        from .registry import get_signal_registry
        
        result = SignalDashboardResult(config=self.current_config)
        
        registry = get_signal_registry()
        all_signals = registry.list_all()
        result.total_signals = len(all_signals)
        
        filtered_signals = []
        for s in all_signals:
            type_name = s.signal_type.value if hasattr(s.signal_type, 'value') else str(s.signal_type)
            
            if self.current_config.signal_types and type_name not in self.current_config.signal_types:
                continue
            
            direction_name = s.direction.value if hasattr(s.direction, 'value') else str(s.direction)
            if self.current_config.directions and direction_name not in self.current_config.directions:
                continue
            
            # SignalMetadata没有strength字段，跳过强度筛选
            if hasattr(s, 'strength'):
                strength_name = s.strength.value if hasattr(s.strength, 'value') else str(s.strength)
                if self.current_config.strengths and strength_name not in self.current_config.strengths:
                    continue
            
            status_name = s.status.value if hasattr(s.status, 'value') else str(s.status)
            if self.current_config.statuses and status_name not in self.current_config.statuses:
                continue
            
            if self.current_config.min_win_rate is not None:
                if s.performance and s.performance.win_rate < self.current_config.min_win_rate:
                    continue
            
            if self.current_config.min_avg_return is not None:
                if s.performance and s.performance.avg_return < self.current_config.min_avg_return:
                    continue
            
            if self.current_config.max_drawdown is not None:
                if s.performance and abs(s.performance.max_drawdown) > abs(self.current_config.max_drawdown):
                    continue
            
            filtered_signals.append(s)
        
        result.filtered_signals = len(filtered_signals)
        
        for s in filtered_signals:
            row = SignalDashboardRow(
                signal_id=s.id,
                signal_name=s.name,
                signal_type=s.signal_type.value if hasattr(s.signal_type, 'value') else str(s.signal_type),
                direction=s.direction.value if hasattr(s.direction, 'value') else str(s.direction),
                strength=s.strength.value if hasattr(s, 'strength') and hasattr(s.strength, 'value') else "unknown",
                status=s.status.value if hasattr(s.status, 'value') else str(s.status),
            )
            
            if hasattr(s, 'performance') and s.performance:
                row.win_rate = s.performance.win_rate
                row.avg_return = s.performance.avg_return
                row.max_drawdown = s.performance.max_drawdown
                row.total_signals = s.performance.total_signals
                row.winning_signals = s.performance.winning_signals
                row.avg_holding_days = s.performance.avg_holding_days
            
            if s.rules:
                row.factor_count = len(s.rules.factors)
            
            row.score = s.score if hasattr(s, 'score') else 0.0
            
            result.rows.append(row)
        
        result.sort_rows(self.current_config.sort_by, self.current_config.sort_order)
        
        result.duration_seconds = time.time() - start_time
        
        return result


def get_signal_dashboard() -> SignalDashboard:
    """获取信号看板实例"""
    return SignalDashboard()
