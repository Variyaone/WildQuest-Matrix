"""
绩效追踪模块

持续追踪策略绩效，支持多维度、多周期的绩效分析。
"""

import json
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import pandas as pd
import numpy as np

from core.infrastructure.logging import get_logger


class TrackingPeriod(Enum):
    """追踪周期"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class BenchmarkType(Enum):
    """基准类型"""
    HS300 = "000300.SH"  # 沪深300
    ZZ500 = "000905.SH"  # 中证500
    ZZ1000 = "000852.SH"  # 中证1000
    FUND_INDEX = "885000.WI"  # 偏股混合型基金指数


@dataclass
class PerformanceMetrics:
    """绩效指标"""
    period: str
    start_date: str
    end_date: str
    
    total_return: float = 0.0
    annual_return: float = 0.0
    excess_return: float = 0.0
    
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    
    win_rate: float = 0.0
    profit_loss_ratio: float = 0.0
    
    turnover_rate: float = 0.0
    total_commission: float = 0.0
    total_slippage: float = 0.0
    
    trading_days: int = 0
    total_trades: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DailyPerformance:
    """日度绩效"""
    date: str
    daily_return: float = 0.0
    excess_return: float = 0.0
    benchmark_return: float = 0.0
    turnover_rate: float = 0.0
    commission: float = 0.0
    position_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BenchmarkData:
    """基准数据"""
    benchmark_type: BenchmarkType
    benchmark_name: str
    daily_returns: List[Tuple[str, float]] = field(default_factory=list)
    
    def get_return(self, target_date: str) -> float:
        """获取指定日期收益率"""
        for d, r in self.daily_returns:
            if d == target_date:
                return r
        return 0.0


class PerformanceTracker:
    """绩效追踪器"""
    
    def __init__(
        self,
        tracker_id: str,
        benchmark: BenchmarkType = BenchmarkType.HS300,
        storage_path: str = "./data/performance"
    ):
        self.tracker_id = tracker_id
        self.benchmark = benchmark
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger("monitor.tracker")
        
        self.daily_performances: List[DailyPerformance] = []
        self.benchmark_data: Optional[BenchmarkData] = None
        self._returns_series: Optional[pd.Series] = None
    
    def add_daily_performance(
        self,
        date: str,
        daily_return: float,
        turnover_rate: float = 0.0,
        commission: float = 0.0,
        position_count: int = 0
    ):
        """添加日度绩效"""
        benchmark_return = 0.0
        if self.benchmark_data:
            benchmark_return = self.benchmark_data.get_return(date)
        
        excess_return = daily_return - benchmark_return
        
        perf = DailyPerformance(
            date=date,
            daily_return=daily_return,
            excess_return=excess_return,
            benchmark_return=benchmark_return,
            turnover_rate=turnover_rate,
            commission=commission,
            position_count=position_count
        )
        
        self.daily_performances.append(perf)
        self._update_returns_series()
        self.logger.debug(f"添加日度绩效: {date}, 收益率: {daily_return:.4f}")
    
    def _update_returns_series(self):
        """更新收益率序列"""
        if not self.daily_performances:
            return
        
        data = {
            datetime.strptime(p.date, "%Y-%m-%d"): p.daily_return
            for p in self.daily_performances
        }
        self._returns_series = pd.Series(data)
        self._returns_series.sort_index(inplace=True)
    
    def calculate_metrics(self, period: TrackingPeriod = TrackingPeriod.DAILY) -> PerformanceMetrics:
        """计算绩效指标"""
        if not self.daily_performances:
            return PerformanceMetrics(
                period=period.value,
                start_date="",
                end_date=""
            )
        
        start_date = self.daily_performances[0].date
        end_date = self.daily_performances[-1].date
        
        returns = np.array([p.daily_return for p in self.daily_performances])
        excess_returns = np.array([p.excess_return for p in self.daily_performances])
        
        total_return = (1 + returns).prod() - 1
        
        trading_days = len(returns)
        annual_factor = 252 / trading_days if trading_days > 0 else 0
        annual_return = (1 + total_return) ** annual_factor - 1 if total_return > -1 else 0
        
        volatility = np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0
        
        mean_excess = np.mean(excess_returns) * 252 if len(excess_returns) > 0 else 0
        sharpe_ratio = mean_excess / volatility if volatility > 0 else 0
        
        negative_returns = returns[returns < 0]
        downside_volatility = np.std(negative_returns) * np.sqrt(252) if len(negative_returns) > 1 else 0
        sortino_ratio = mean_excess / downside_volatility if downside_volatility > 0 else 0
        
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (running_max - cumulative) / running_max
        max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0
        
        calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0
        
        win_count = np.sum(returns > 0)
        win_rate = win_count / len(returns) if len(returns) > 0 else 0
        
        profits = returns[returns > 0]
        losses = np.abs(returns[returns < 0])
        avg_profit = np.mean(profits) if len(profits) > 0 else 0
        avg_loss = np.mean(losses) if len(losses) > 0 else 0
        profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0
        
        turnover_rates = [p.turnover_rate for p in self.daily_performances]
        avg_turnover = np.mean(turnover_rates) * 252 if turnover_rates else 0
        
        total_commission = sum(p.commission for p in self.daily_performances)
        
        return PerformanceMetrics(
            period=period.value,
            start_date=start_date,
            end_date=end_date,
            total_return=total_return,
            annual_return=annual_return,
            excess_return=np.mean(excess_returns) * 252 if len(excess_returns) > 0 else 0,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_loss_ratio=profit_loss_ratio,
            turnover_rate=avg_turnover,
            total_commission=total_commission,
            trading_days=trading_days,
            total_trades=len([p for p in self.daily_performances if p.turnover_rate > 0])
        )
    
    def get_period_performance(self, period: TrackingPeriod) -> List[DailyPerformance]:
        """获取周期绩效"""
        if period == TrackingPeriod.DAILY:
            return self.daily_performances[-1:] if self.daily_performances else []
        
        elif period == TrackingPeriod.WEEKLY:
            if not self.daily_performances:
                return []
            
            end_date = datetime.strptime(self.daily_performances[-1].date, "%Y-%m-%d")
            start_date = end_date - timedelta(days=7)
            
            return [
                p for p in self.daily_performances
                if datetime.strptime(p.date, "%Y-%m-%d") >= start_date
            ]
        
        elif period == TrackingPeriod.MONTHLY:
            if not self.daily_performances:
                return []
            
            end_date = datetime.strptime(self.daily_performances[-1].date, "%Y-%m-%d")
            start_date = end_date - timedelta(days=30)
            
            return [
                p for p in self.daily_performances
                if datetime.strptime(p.date, "%Y-%m-%d") >= start_date
            ]
        
        elif period == TrackingPeriod.YEARLY:
            if not self.daily_performances:
                return []
            
            end_date = datetime.strptime(self.daily_performances[-1].date, "%Y-%m-%d")
            start_date = end_date - timedelta(days=365)
            
            return [
                p for p in self.daily_performances
                if datetime.strptime(p.date, "%Y-%m-%d") >= start_date
            ]
        
        return []
    
    def get_cumulative_returns(self) -> pd.Series:
        """获取累计收益率序列"""
        if self._returns_series is None:
            return pd.Series()
        
        return (1 + self._returns_series).cumprod() - 1
    
    def get_drawdown_series(self) -> pd.Series:
        """获取回撤序列"""
        if self._returns_series is None:
            return pd.Series()
        
        cumulative = (1 + self._returns_series).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        
        return drawdown
    
    def compare_with_benchmark(self) -> Dict[str, Any]:
        """与基准对比"""
        if not self.daily_performances or not self.benchmark_data:
            return {}
        
        strategy_returns = np.array([p.daily_return for p in self.daily_performances])
        benchmark_returns = np.array([p.benchmark_return for p in self.daily_performances])
        
        strategy_total = (1 + strategy_returns).prod() - 1
        benchmark_total = (1 + benchmark_returns).prod() - 1
        
        correlation = np.corrcoef(strategy_returns, benchmark_returns)[0, 1]
        
        active_returns = strategy_returns - benchmark_returns
        tracking_error = np.std(active_returns) * np.sqrt(252)
        
        information_ratio = np.mean(active_returns) * 252 / tracking_error if tracking_error > 0 else 0
        
        beta = np.cov(strategy_returns, benchmark_returns)[0, 1] / np.var(benchmark_returns) if np.var(benchmark_returns) > 0 else 0
        
        alpha = (np.mean(strategy_returns) - beta * np.mean(benchmark_returns)) * 252
        
        return {
            "strategy_total_return": strategy_total,
            "benchmark_total_return": benchmark_total,
            "excess_return": strategy_total - benchmark_total,
            "correlation": correlation,
            "tracking_error": tracking_error,
            "information_ratio": information_ratio,
            "beta": beta,
            "alpha": alpha
        }
    
    def save(self) -> bool:
        """保存绩效数据"""
        file_path = self.storage_path / f"{self.tracker_id}.json"
        
        data = {
            "tracker_id": self.tracker_id,
            "benchmark": self.benchmark.value,
            "daily_performances": [p.to_dict() for p in self.daily_performances]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"保存绩效数据: {self.tracker_id}")
        return True
    
    def load(self) -> bool:
        """加载绩效数据"""
        file_path = self.storage_path / f"{self.tracker_id}.json"
        
        if not file_path.exists():
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.benchmark = BenchmarkType(data["benchmark"])
            self.daily_performances = [
                DailyPerformance(**p) for p in data["daily_performances"]
            ]
            self._update_returns_series()
            
            self.logger.info(f"加载绩效数据: {self.tracker_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"加载绩效数据失败: {e}")
            return False
    
    def generate_report(self, period: TrackingPeriod = TrackingPeriod.MONTHLY) -> str:
        """生成绩效报告"""
        metrics = self.calculate_metrics(period)
        comparison = self.compare_with_benchmark()
        
        report_lines = [
            f"# 绩效报告 ({period.value})",
            "",
            f"**追踪器ID**: {self.tracker_id}",
            f"**基准**: {self.benchmark.value}",
            f"**统计周期**: {metrics.start_date} ~ {metrics.end_date}",
            "",
            "## 收益指标",
            f"- 总收益率: {metrics.total_return:.2%}",
            f"- 年化收益率: {metrics.annual_return:.2%}",
            f"- 超额收益: {metrics.excess_return:.2%}",
            "",
            "## 风险指标",
            f"- 年化波动率: {metrics.volatility:.2%}",
            f"- 最大回撤: {metrics.max_drawdown:.2%}",
            f"- 夏普比率: {metrics.sharpe_ratio:.2f}",
            f"- 索提诺比率: {metrics.sortino_ratio:.2f}",
            f"- 卡玛比率: {metrics.calmar_ratio:.2f}",
            "",
            "## 交易指标",
            f"- 胜率: {metrics.win_rate:.2%}",
            f"- 盈亏比: {metrics.profit_loss_ratio:.2f}",
            f"- 年化换手率: {metrics.turnover_rate:.2%}",
            f"- 总交易成本: {metrics.total_commission:.2f}",
            f"- 交易天数: {metrics.trading_days}",
            "",
        ]
        
        if comparison:
            report_lines.extend([
                "## 基准对比",
                f"- 策略总收益: {comparison['strategy_total_return']:.2%}",
                f"- 基准总收益: {comparison['benchmark_total_return']:.2%}",
                f"- 超额收益: {comparison['excess_return']:.2%}",
                f"- 相关系数: {comparison['correlation']:.2f}",
                f"- 跟踪误差: {comparison['tracking_error']:.2%}",
                f"- 信息比率: {comparison['information_ratio']:.2f}",
                f"- Beta: {comparison['beta']:.2f}",
                f"- Alpha: {comparison['alpha']:.2%}",
            ])
        
        return "\n".join(report_lines)
