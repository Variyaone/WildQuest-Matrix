"""
因子看板模块

借鉴聚宽因子看板设计，提供统一的因子分析入口。
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

from .classification import FactorCategory, FactorSubCategory
from .registry import ValidationStatus


class StockPool(Enum):
    """股票池选项"""
    ALL_A = "全A股"
    CSI300 = "沪深300"
    CSI500 = "中证500"
    CSI800 = "中证800"
    CSI1000 = "中证1000"
    GEM = "创业板"
    STAR = "科创板"


class BacktestPeriod(Enum):
    """回测周期选项"""
    RECENT_3M = "近3个月"
    RECENT_1Y = "近1年"
    RECENT_3Y = "近3年"
    RECENT_5Y = "近5年"
    RECENT_10Y = "近10年"
    YTD = "年初至今"
    CUSTOM = "自定义"


class PortfolioType(Enum):
    """组合构建类型"""
    LONG_ONLY = "纯多头组合"
    LONG_SHORT = "多空组合"


class CommissionPreset(Enum):
    """手续费预设方案"""
    NONE = "无"
    STANDARD = "3‰佣金+1‰印花税+无滑点"
    WITH_SLIPPAGE = "3‰佣金+1‰印花税+1‰滑点"
    CUSTOM = "自定义"


COMMISSION_PRESETS = {
    CommissionPreset.NONE: {
        "buy_commission": 0.0,
        "sell_commission": 0.0,
        "stamp_duty": 0.0,
        "slippage": 0.0,
    },
    CommissionPreset.STANDARD: {
        "buy_commission": 0.003,
        "sell_commission": 0.003,
        "stamp_duty": 0.001,
        "slippage": 0.0,
    },
    CommissionPreset.WITH_SLIPPAGE: {
        "buy_commission": 0.003,
        "sell_commission": 0.003,
        "stamp_duty": 0.001,
        "slippage": 0.001,
    },
}


TOOLTIPS = {
    "filter_limit_up": "排除涨停股票，避免无法买入的情况",
    "filter_limit_down": "排除跌停股票，避免无法卖出的情况",
    "filter_suspended": "排除停牌股票，避免无法交易的情况",
    "filter_st_less_1y": "排除上市不足1年的新股，避免流动性风险",
    "n_groups": "将股票按因子值分成N组，用于计算分位数收益",
    "holding_period": "持仓周期（交易日），用于计算换手率",
    "portfolio_type": "纯多头：仅做多因子值最高的股票\n多空：做多高因子值、做空低因子值",
    "min_quantile": "因子值最小的分位数组（第1组）",
    "max_quantile": "因子值最大的分位数组（第N组）",
}


@dataclass
class FactorFilterConfig:
    """
    因子筛选配置
    
    集中管理所有筛选参数，支持持久化存储。
    """
    categories: List[str] = field(default_factory=lambda: ["动量类", "价值类"])
    stock_pools: List[str] = field(default_factory=lambda: ["中证500", "中证800"])
    backtest_periods: List[str] = field(default_factory=lambda: ["近1年", "近3年"])
    
    n_groups: int = 5
    holding_period: int = 5
    
    portfolio_type: str = "纯多头组合"
    commission_preset: str = "3‰佣金+1‰印花税+1‰滑点"
    
    filter_limit_up: bool = True
    filter_limit_down: bool = True
    filter_suspended: bool = True
    filter_st_less_1y: bool = True
    
    buy_commission: float = 0.0003
    sell_commission: float = 0.0013
    stamp_duty: float = 0.001
    slippage: float = 0.001
    
    custom_start_date: Optional[str] = None
    custom_end_date: Optional[str] = None
    
    sort_by: str = "ic_mean"
    sort_order: str = "desc"
    
    min_ic: Optional[float] = None
    min_ir: Optional[float] = None
    max_correlation: Optional[float] = None
    
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FactorFilterConfig":
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k) or k in cls.__dataclass_fields__})
    
    def get_total_cost(self) -> float:
        """计算总交易成本"""
        return self.buy_commission + self.sell_commission + self.stamp_duty + self.slippage
    
    def apply_commission_preset(self, preset: str):
        """应用手续费预设"""
        for p in CommissionPreset:
            if p.value == preset:
                preset_data = COMMISSION_PRESETS.get(p, {})
                self.buy_commission = preset_data.get("buy_commission", 0.0)
                self.sell_commission = preset_data.get("sell_commission", 0.0)
                self.stamp_duty = preset_data.get("stamp_duty", 0.0)
                self.slippage = preset_data.get("slippage", 0.0)
                self.commission_preset = preset
                break
    
    def get_effective_period(self) -> tuple:
        """获取有效回测周期"""
        today = datetime.now()
        
        if "近3个月" in self.backtest_periods:
            end_date = today.strftime("%Y-%m-%d")
            start_date = (today.replace(year=today.year - 1)).strftime("%Y-%m-%d")
            from dateutil.relativedelta import relativedelta
            start_date = (today - relativedelta(months=3)).strftime("%Y-%m-%d")
            return start_date, end_date
        elif "近1年" in self.backtest_periods:
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
        elif "近10年" in self.backtest_periods:
            end_date = today.strftime("%Y-%m-%d")
            start_date = (today.replace(year=today.year - 10)).strftime("%Y-%m-%d")
            return start_date, end_date
        elif "年初至今" in self.backtest_periods:
            end_date = today.strftime("%Y-%m-%d")
            start_date = today.replace(month=1, day=1).strftime("%Y-%m-%d")
            return start_date, end_date
        elif self.custom_start_date and self.custom_end_date:
            return self.custom_start_date, self.custom_end_date
        
        end_date = today.strftime("%Y-%m-%d")
        start_date = (today.replace(year=today.year - 1)).strftime("%Y-%m-%d")
        return start_date, end_date


DEFAULT_FILTER_CONFIG = FactorFilterConfig(
    categories=["动量类", "价值类", "质量类"],
    stock_pools=["中证500", "中证800"],
    backtest_periods=["近1年", "近3年"],
    n_groups=5,
    holding_period=5,
    filter_limit_up=True,
    filter_suspended=True,
    buy_commission=0.0003,
    sell_commission=0.0013,
    slippage=0.001,
)


class FactorDashboardConfigManager:
    """
    因子看板配置管理器
    
    负责配置的持久化存储和加载。
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path.home() / ".openclaw" / "factor_dashboard"
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "filter_config.json"
    
    def save(self, config: FactorFilterConfig, name: str = "default") -> bool:
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
    
    def load(self, name: str = "default") -> FactorFilterConfig:
        """加载配置"""
        try:
            configs = self.load_all()
            if name in configs:
                return FactorFilterConfig.from_dict(configs[name])
        except Exception:
            pass
        
        return DEFAULT_FILTER_CONFIG
    
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
class FactorDashboardRow:
    """因子看板表格行"""
    factor_id: str
    factor_name: str
    category: str
    
    min_quantile_excess_return: float = 0.0
    max_quantile_excess_return: float = 0.0
    min_quantile_turnover: float = 0.0
    max_quantile_turnover: float = 0.0
    
    excess_return: float = 0.0
    turnover: float = 0.0
    ic_mean: float = 0.0
    ic_std: float = 0.0
    ir: float = 0.0
    t_stat: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    monotonicity: float = 0.0
    score: int = 0
    rank: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def get_return_class(self) -> str:
        """获取收益的颜色类"""
        return "positive" if self.excess_return > 0 else "negative"
    
    def get_ic_class(self) -> str:
        """获取IC的颜色类"""
        return "positive" if self.ic_mean > 0 else "negative"
    
    def get_min_quantile_return_class(self) -> str:
        """获取最小分位数收益的颜色类"""
        return "positive" if self.min_quantile_excess_return > 0 else "negative"
    
    def get_max_quantile_return_class(self) -> str:
        """获取最大分位数收益的颜色类"""
        return "positive" if self.max_quantile_excess_return > 0 else "negative"


@dataclass
class FactorDashboardResult:
    """因子看板分析结果"""
    config: FactorFilterConfig
    rows: List[FactorDashboardRow] = field(default_factory=list)
    total_factors: int = 0
    filtered_factors: int = 0
    analysis_time: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    duration_seconds: float = 0.0
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "rows": [r.to_dict() for r in self.rows],
            "total_factors": self.total_factors,
            "filtered_factors": self.filtered_factors,
            "analysis_time": self.analysis_time,
            "duration_seconds": self.duration_seconds,
            "warnings": self.warnings,
        }
    
    def sort_rows(self, by: str = "ic_mean", order: str = "desc"):
        """排序结果行"""
        reverse = (order == "desc")
        
        if by == "ic_mean":
            self.rows.sort(key=lambda x: x.ic_mean, reverse=reverse)
        elif by == "ir":
            self.rows.sort(key=lambda x: x.ir, reverse=reverse)
        elif by == "excess_return":
            self.rows.sort(key=lambda x: x.excess_return, reverse=reverse)
        elif by == "min_quantile_excess_return":
            self.rows.sort(key=lambda x: x.min_quantile_excess_return, reverse=reverse)
        elif by == "max_quantile_excess_return":
            self.rows.sort(key=lambda x: x.max_quantile_excess_return, reverse=reverse)
        elif by == "score":
            self.rows.sort(key=lambda x: x.score, reverse=reverse)
        elif by == "turnover":
            self.rows.sort(key=lambda x: x.turnover, reverse=reverse)
        
        for i, row in enumerate(self.rows):
            row.rank = i + 1


class FactorDashboard:
    """
    因子看板
    
    统一的因子分析入口，借鉴聚宽设计。
    """
    
    STOCK_POOL_OPTIONS = [
        ("沪深300", "大盘蓝筹"),
        ("中证500", "中盘成长"),
        ("中证800", "沪深300+中证500"),
        ("中证1000", "小盘股"),
        ("中证全指", "全市场股票"),
    ]
    
    BACKTEST_PERIOD_OPTIONS = [
        ("近3个月", "最近63个交易日"),
        ("近1年", "最近252个交易日"),
        ("近3年", "最近756个交易日"),
        ("近10年", "最近2520个交易日"),
        ("自定义", "自定义起止日期"),
    ]
    
    CATEGORY_OPTIONS = [
        ("基础科目及衍生类因子", "财务基础科目"),
        ("情绪类因子", "市场情绪因子"),
        ("成长类因子", "盈利增长因子"),
        ("风险因子-新风格因子", "新风格风险因子"),
        ("每股指标因子", "每股财务指标"),
        ("风险因子-风格因子", "风格风险因子"),
        ("技术指标因子", "技术分析因子"),
        ("动量类", "价格动量因子"),
        ("价值类", "估值因子"),
        ("质量类", "盈利质量因子"),
        ("波动率类", "波动率因子"),
        ("流动性类", "流动性因子"),
        ("规模类", "市值规模因子"),
        ("另类数据类", "另类数据因子"),
    ]
    
    PORTFOLIO_TYPE_OPTIONS = [
        ("纯多头组合", "仅做多因子值最高的股票"),
        ("多空组合", "做多高因子值、做空低因子值"),
    ]
    
    COMMISSION_PRESET_OPTIONS = [
        ("无", "无手续费无滑点"),
        ("3‰佣金+1‰印花税+无滑点", "标准佣金"),
        ("3‰佣金+1‰印花税+1‰滑点", "含滑点"),
        ("自定义", "自定义手续费"),
    ]
    
    FILTER_STOCK_OPTIONS = [
        ("是", "过滤涨停、跌停、停牌股票"),
        ("否", "不过滤"),
    ]
    
    SORT_OPTIONS = [
        ("ic_mean", "IC均值"),
        ("ir", "信息比率"),
        ("excess_return", "超额收益"),
        ("min_quantile_excess_return", "最小分位数收益"),
        ("max_quantile_excess_return", "最大分位数收益"),
        ("score", "综合得分"),
        ("turnover", "换手率"),
    ]
    
    def __init__(self):
        self.config_manager = FactorDashboardConfigManager()
        self.current_config: FactorFilterConfig = self.config_manager.load()
    
    def get_config(self) -> FactorFilterConfig:
        """获取当前配置"""
        return self.current_config
    
    def update_config(self, **kwargs) -> FactorFilterConfig:
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.current_config, key):
                setattr(self.current_config, key, value)
        
        self.current_config.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self.current_config
    
    def save_config(self, name: str = "default") -> bool:
        """保存当前配置"""
        return self.config_manager.save(self.current_config, name)
    
    def load_config(self, name: str = "default") -> FactorFilterConfig:
        """加载配置"""
        self.current_config = self.config_manager.load(name)
        return self.current_config
    
    def reset_config(self) -> FactorFilterConfig:
        """重置为默认配置"""
        self.current_config = DEFAULT_FILTER_CONFIG
        return self.current_config
    
    def run_analysis(self) -> FactorDashboardResult:
        """
        运行因子分析
        
        根据当前配置筛选因子并计算绩效指标。
        """
        import time
        start_time = time.time()
        
        from .registry import get_factor_registry
        from .validator import get_factor_validator
        from .backtester import get_factor_backtester
        
        result = FactorDashboardResult(config=self.current_config)
        
        registry = get_factor_registry()
        all_factors = registry.list_all()
        result.total_factors = len(all_factors)
        
        filtered_factors = []
        for f in all_factors:
            category_name = f.category.value if hasattr(f.category, 'value') else str(f.category)
            
            if self.current_config.categories and category_name not in self.current_config.categories:
                continue
            
            if self.current_config.min_ic is not None:
                if f.quality_metrics and f.quality_metrics.ic_mean < self.current_config.min_ic:
                    continue
            
            if self.current_config.min_ir is not None:
                if f.quality_metrics and f.quality_metrics.ir < self.current_config.min_ir:
                    continue
            
            filtered_factors.append(f)
        
        result.filtered_factors = len(filtered_factors)
        
        for f in filtered_factors:
            row = FactorDashboardRow(
                factor_id=f.id,
                factor_name=f.name,
                category=f.category.value if hasattr(f.category, 'value') else str(f.category),
            )
            
            if f.quality_metrics:
                row.ic_mean = f.quality_metrics.ic_mean
                row.ic_std = f.quality_metrics.ic_std
                row.ir = f.quality_metrics.ir
                row.monotonicity = f.quality_metrics.monotonicity
            
            if f.backtest_results:
                latest_backtest = list(f.backtest_results.values())[-1] if f.backtest_results else None
                if latest_backtest:
                    row.excess_return = latest_backtest.annual_return
                    row.turnover = 0.0
                    row.max_drawdown = latest_backtest.max_drawdown
                    row.win_rate = latest_backtest.win_rate
                    row.t_stat = latest_backtest.ic / (f.quality_metrics.ic_std if f.quality_metrics else 1)
            
            validation_status = getattr(f, 'validation_status', ValidationStatus.NOT_VALIDATED)
            if validation_status in (ValidationStatus.NOT_VALIDATED, ValidationStatus.FAILED):
                row.score = 0.0
            else:
                row.score = f.score if f.score > 0 else 0.0
            result.rows.append(row)
        
        result.sort_rows(self.current_config.sort_by, self.current_config.sort_order)
        
        result.duration_seconds = time.time() - start_time
        
        return result


def get_factor_dashboard() -> FactorDashboard:
    """获取因子看板实例"""
    return FactorDashboard()
