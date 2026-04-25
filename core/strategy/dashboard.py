"""
策略看板模块

借鉴聚宽因子看板设计，提供统一的策略分析入口。
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


class StrategyTypeFilter(Enum):
    """策略类型筛选选项"""
    STOCK_SELECTION = "选股策略"
    TIMING = "择时策略"
    ARBITRAGE = "套利策略"
    TREND_FOLLOWING = "趋势跟踪"
    MEAN_REVERSION = "均值回归"
    MULTI_FACTOR = "多因子策略"
    CUSTOM = "自定义策略"


class RebalanceFreqFilter(Enum):
    """调仓频率筛选选项"""
    DAILY = "每日"
    WEEKLY = "每周"
    BIWEEKLY = "每两周"
    MONTHLY = "每月"
    QUARTERLY = "每季度"


@dataclass
class StrategyFilterConfig:
    """
    策略筛选配置
    
    集中管理所有筛选参数，支持持久化存储。
    """
    strategy_types: List[str] = field(default_factory=lambda: ["多因子策略", "选股策略"])
    rebalance_freqs: List[str] = field(default_factory=lambda: ["每日", "每周"])
    statuses: List[str] = field(default_factory=lambda: ["active"])
    
    backtest_periods: List[str] = field(default_factory=lambda: ["近1年", "近3年"])
    stock_pool: str = "中证500"
    benchmark: str = "000300.SH"
    
    min_sharpe: Optional[float] = None
    min_return: Optional[float] = None
    max_drawdown: Optional[float] = None
    min_win_rate: Optional[float] = None
    
    sort_by: str = "sharpe_ratio"
    sort_order: str = "desc"
    
    max_positions_range: tuple = (5, 50)
    
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyFilterConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def get_effective_period(self) -> tuple:
        """获取有效回测周期"""
        today = datetime.now()
        
        if "近1年" in self.backtest_periods:
            end_date = today.strftime("%Y-%m-%d")
            start_date = (today.replace(year=today.year - 1)).strftime("%Y-%m-%d")
            return start_date, end_date
        elif "近3年" in self.backtest_periods:
            end_date = today.strftime("%Y-%m-%d")
            start_date = (today.replace(year=today.year - 3)).strftime("%Y-%m-%d")
            return start_date, end_date
        elif "近5年" in self.backtest_periods:
            end_date = today.strftime("%Y-%m-%d")
            start_date = (today.replace(year=today.year - 5)).strftime("%Y-%m-%d")
            return start_date, end_date
        
        end_date = today.strftime("%Y-%m-%d")
        start_date = (today.replace(year=today.year - 1)).strftime("%Y-%m-%d")
        return start_date, end_date


DEFAULT_STRATEGY_FILTER_CONFIG = StrategyFilterConfig(
    strategy_types=["多因子策略", "选股策略"],
    rebalance_freqs=["每日", "每周"],
    statuses=["active"],
    backtest_periods=["近1年", "近3年"],
    stock_pool="中证500",
    benchmark="000300.SH",
    sort_by="sharpe_ratio",
)


class StrategyDashboardConfigManager:
    """
    策略看板配置管理器
    
    负责配置的持久化存储和加载。
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path.home() / ".openclaw" / "strategy_dashboard"
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "filter_config.json"
    
    def save(self, config: StrategyFilterConfig, name: str = "default") -> bool:
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
    
    def load(self, name: str = "default") -> StrategyFilterConfig:
        """加载配置"""
        try:
            configs = self.load_all()
            if name in configs:
                return StrategyFilterConfig.from_dict(configs[name])
        except Exception:
            pass
        
        return DEFAULT_STRATEGY_FILTER_CONFIG
    
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
class StrategyDashboardRow:
    """策略看板表格行"""
    strategy_id: str
    strategy_name: str
    strategy_type: str
    rebalance_freq: str
    status: str
    
    annual_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    excess_return: float = 0.0
    volatility: float = 0.0
    calmar_ratio: float = 0.0
    
    max_positions: int = 10
    signal_count: int = 0
    
    score: float = 0.0
    rank: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def get_return_class(self) -> str:
        """获取收益的颜色类"""
        return "positive" if self.annual_return > 0 else "negative"
    
    def get_sharpe_class(self) -> str:
        """获取夏普的颜色类"""
        return "positive" if self.sharpe_ratio > 1.0 else "negative" if self.sharpe_ratio < 0 else "neutral"


@dataclass
class StrategyDashboardResult:
    """策略看板分析结果"""
    config: StrategyFilterConfig
    rows: List[StrategyDashboardRow] = field(default_factory=list)
    total_strategies: int = 0
    filtered_strategies: int = 0
    analysis_time: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    duration_seconds: float = 0.0
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "rows": [r.to_dict() for r in self.rows],
            "total_strategies": self.total_strategies,
            "filtered_strategies": self.filtered_strategies,
            "analysis_time": self.analysis_time,
            "duration_seconds": self.duration_seconds,
            "warnings": self.warnings,
        }
    
    def sort_rows(self, by: str = "sharpe_ratio", order: str = "desc"):
        """排序结果行"""
        reverse = (order == "desc")
        
        if by == "sharpe_ratio":
            self.rows.sort(key=lambda x: x.sharpe_ratio, reverse=reverse)
        elif by == "annual_return":
            self.rows.sort(key=lambda x: x.annual_return, reverse=reverse)
        elif by == "excess_return":
            self.rows.sort(key=lambda x: x.excess_return, reverse=reverse)
        elif by == "max_drawdown":
            self.rows.sort(key=lambda x: x.max_drawdown, reverse=not reverse)
        elif by == "win_rate":
            self.rows.sort(key=lambda x: x.win_rate, reverse=reverse)
        elif by == "score":
            self.rows.sort(key=lambda x: x.score, reverse=reverse)
        
        for i, row in enumerate(self.rows):
            row.rank = i + 1


class StrategyDashboard:
    """
    策略看板
    
    统一的策略分析入口，借鉴聚宽设计。
    """
    
    STRATEGY_TYPE_OPTIONS = [
        ("选股策略", "基于因子选股"),
        ("择时策略", "市场择时"),
        ("套利策略", "统计套利"),
        ("趋势跟踪", "趋势跟踪策略"),
        ("均值回归", "均值回归策略"),
        ("多因子策略", "多因子组合"),
        ("自定义策略", "用户自定义"),
    ]
    
    REBALANCE_FREQ_OPTIONS = [
        ("每日", "每日调仓"),
        ("每周", "每周调仓"),
        ("每两周", "双周调仓"),
        ("每月", "每月调仓"),
        ("每季度", "季度调仓"),
    ]
    
    STATUS_OPTIONS = [
        ("active", "活跃"),
        ("testing", "测试中"),
        ("inactive", "停用"),
        ("deprecated", "已废弃"),
    ]
    
    SORT_OPTIONS = [
        ("sharpe_ratio", "夏普比率"),
        ("annual_return", "年化收益"),
        ("excess_return", "超额收益"),
        ("max_drawdown", "最大回撤"),
        ("win_rate", "胜率"),
        ("score", "综合得分"),
    ]
    
    STOCK_POOL_OPTIONS = [
        "全A股", "沪深300", "中证500", "中证800", "中证1000", "创业板", "科创板"
    ]
    
    BENCHMARK_OPTIONS = [
        ("000300.SH", "沪深300"),
        ("000905.SH", "中证500"),
        ("000852.SH", "中证1000"),
        ("000001.SH", "上证指数"),
        ("399001.SZ", "深证成指"),
        ("399006.SZ", "创业板指"),
    ]
    
    def __init__(self):
        self.config_manager = StrategyDashboardConfigManager()
        self.current_config: StrategyFilterConfig = self.config_manager.load()
    
    def get_config(self) -> StrategyFilterConfig:
        """获取当前配置"""
        return self.current_config
    
    def update_config(self, **kwargs) -> StrategyFilterConfig:
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.current_config, key):
                setattr(self.current_config, key, value)
        
        self.current_config.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self.current_config
    
    def save_config(self, name: str = "default") -> bool:
        """保存当前配置"""
        return self.config_manager.save(self.current_config, name)
    
    def load_config(self, name: str = "default") -> StrategyFilterConfig:
        """加载配置"""
        self.current_config = self.config_manager.load(name)
        return self.current_config
    
    def reset_config(self) -> StrategyFilterConfig:
        """重置为默认配置"""
        self.current_config = DEFAULT_STRATEGY_FILTER_CONFIG
        return self.current_config
    
    def run_analysis(self) -> StrategyDashboardResult:
        """
        运行策略分析
        
        根据当前配置筛选策略并计算绩效指标。
        """
        import time
        start_time = time.time()
        
        from .registry import get_strategy_registry
        
        result = StrategyDashboardResult(config=self.current_config)
        
        registry = get_strategy_registry()
        all_strategies = registry.list_all()
        result.total_strategies = len(all_strategies)
        
        filtered_strategies = []
        FREQ_EN_TO_CN = {
            "daily": "每日",
            "weekly": "每周",
            "biweekly": "每两周",
            "monthly": "每月",
            "quarterly": "每季度"
        }
        
        for s in all_strategies:
            type_name = s.strategy_type.value if hasattr(s.strategy_type, 'value') else str(s.strategy_type)
            
            if self.current_config.strategy_types and type_name not in self.current_config.strategy_types:
                continue
            
            freq_value = s.rebalance_freq.value if hasattr(s.rebalance_freq, 'value') else str(s.rebalance_freq)
            freq_name = FREQ_EN_TO_CN.get(freq_value, freq_value)
            if self.current_config.rebalance_freqs and freq_name not in self.current_config.rebalance_freqs:
                continue
            
            status_name = s.status.value if hasattr(s.status, 'value') else str(s.status)
            if self.current_config.statuses and status_name not in self.current_config.statuses:
                continue
            
            if self.current_config.min_sharpe is not None:
                if s.backtest_performance and s.backtest_performance.sharpe_ratio < self.current_config.min_sharpe:
                    continue
            
            if self.current_config.min_return is not None:
                if s.backtest_performance and s.backtest_performance.annual_return < self.current_config.min_return:
                    continue
            
            if self.current_config.max_drawdown is not None:
                if s.backtest_performance and abs(s.backtest_performance.max_drawdown) > abs(self.current_config.max_drawdown):
                    continue
            
            filtered_strategies.append(s)
        
        result.filtered_strategies = len(filtered_strategies)
        
        for s in filtered_strategies:
            freq_value = s.rebalance_freq.value if hasattr(s.rebalance_freq, 'value') else str(s.rebalance_freq)
            freq_name = FREQ_EN_TO_CN.get(freq_value, freq_value)
            row = StrategyDashboardRow(
                strategy_id=s.id,
                strategy_name=s.name,
                strategy_type=s.strategy_type.value if hasattr(s.strategy_type, 'value') else str(s.strategy_type),
                rebalance_freq=freq_name,
                status=s.status.value if hasattr(s.status, 'value') else str(s.status),
                max_positions=s.max_positions,
                score=s.score,
            )
            
            if s.backtest_performance:
                row.annual_return = s.backtest_performance.annual_return
                row.sharpe_ratio = s.backtest_performance.sharpe_ratio
                row.max_drawdown = s.backtest_performance.max_drawdown
                row.win_rate = s.backtest_performance.win_rate
                row.excess_return = s.backtest_performance.excess_return
                row.volatility = s.backtest_performance.volatility
                row.calmar_ratio = s.backtest_performance.calmar_ratio
            
            if s.signals:
                row.signal_count = len(s.signals.signal_ids)
            
            result.rows.append(row)
        
        result.sort_rows(self.current_config.sort_by, self.current_config.sort_order)
        
        result.duration_seconds = time.time() - start_time
        
        return result


def get_strategy_dashboard() -> StrategyDashboard:
    """获取策略看板实例"""
    return StrategyDashboard()
