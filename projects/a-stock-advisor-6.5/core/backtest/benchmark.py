"""
基准管理模块

管理基准指数数据，用于策略对比。
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


@dataclass
class Benchmark:
    """基准数据"""
    code: str
    name: str
    data: pd.DataFrame
    start_date: str
    end_date: str
    currency: str = "CNY"
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_returns(self) -> pd.Series:
        """获取收益率序列"""
        if 'close' not in self.data.columns:
            return pd.Series(dtype=float)
        return self.data['close'].pct_change().dropna()
    
    def get_cumulative_returns(self) -> pd.Series:
        """获取累计收益率"""
        returns = self.get_returns()
        return (1 + returns).cumprod() - 1
    
    def get_statistics(self) -> Dict[str, float]:
        """获取统计信息"""
        returns = self.get_returns()
        
        if len(returns) == 0:
            return {}
        
        annual_return = (1 + returns.mean()) ** 252 - 1
        annual_volatility = returns.std() * np.sqrt(252)
        sharpe_ratio = annual_return / annual_volatility if annual_volatility > 0 else 0
        
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        return {
            'annual_return': annual_return,
            'annual_volatility': annual_volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'total_return': (1 + returns).prod() - 1,
            'trading_days': len(returns)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'code': self.code,
            'name': self.name,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'currency': self.currency,
            'description': self.description,
            'statistics': self.get_statistics(),
            'metadata': self.metadata
        }


class BenchmarkManager:
    """
    基准管理器
    
    管理多个基准数据。
    """
    
    DEFAULT_BENCHMARKS = {
        '000300.SH': '沪深300',
        '000905.SH': '中证500',
        '000852.SH': '中证1000',
        '000001.SH': '上证指数',
        '399001.SZ': '深证成指',
        '399006.SZ': '创业板指',
        '000016.SH': '上证50',
        '000688.SH': '科创50'
    }
    
    def __init__(self):
        """初始化基准管理器"""
        self._benchmarks: Dict[str, Benchmark] = {}
        self._default_benchmark: Optional[str] = None
    
    def register(self, benchmark: Benchmark):
        """注册基准"""
        self._benchmarks[benchmark.code] = benchmark
    
    def get(self, code: str) -> Optional[Benchmark]:
        """获取基准"""
        return self._benchmarks.get(code)
    
    def remove(self, code: str) -> bool:
        """移除基准"""
        if code in self._benchmarks:
            del self._benchmarks[code]
            return True
        return False
    
    def list_benchmarks(self) -> List[str]:
        """列出所有基准代码"""
        return list(self._benchmarks.keys())
    
    def set_default(self, code: str) -> bool:
        """设置默认基准"""
        if code in self._benchmarks:
            self._default_benchmark = code
            return True
        return False
    
    def get_default(self) -> Optional[Benchmark]:
        """获取默认基准"""
        if self._default_benchmark:
            return self._benchmarks.get(self._default_benchmark)
        return None
    
    def create_from_dataframe(
        self,
        df: pd.DataFrame,
        code: str,
        name: str,
        description: str = ""
    ) -> Benchmark:
        """
        从DataFrame创建基准
        
        Args:
            df: 包含日期和收盘价的DataFrame
            code: 基准代码
            name: 基准名称
            description: 描述
            
        Returns:
            Benchmark: 基准对象
        """
        if 'date' not in df.columns:
            df = df.reset_index()
            if 'index' in df.columns:
                df = df.rename(columns={'index': 'date'})
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        start_date = df['date'].min().strftime('%Y-%m-%d')
        end_date = df['date'].max().strftime('%Y-%m-%d')
        
        benchmark = Benchmark(
            code=code,
            name=name,
            data=df,
            start_date=start_date,
            end_date=end_date,
            description=description
        )
        
        self.register(benchmark)
        return benchmark
    
    def compare(
        self,
        strategy_returns: pd.Series,
        benchmark_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        对比策略与基准表现
        
        Args:
            strategy_returns: 策略收益率序列
            benchmark_code: 基准代码（默认使用默认基准）
            
        Returns:
            Dict: 对比结果
        """
        benchmark = self.get(benchmark_code) if benchmark_code else self.get_default()
        
        if not benchmark:
            return {'error': '基准不存在'}
        
        benchmark_returns = benchmark.get_returns()
        
        aligned_strategy, aligned_benchmark = strategy_returns.align(
            benchmark_returns, join='inner'
        )
        
        if len(aligned_strategy) == 0:
            return {'error': '无重叠数据'}
        
        excess_returns = aligned_strategy - aligned_benchmark
        
        tracking_error = excess_returns.std() * np.sqrt(252)
        information_ratio = (
            excess_returns.mean() * 252 / tracking_error
            if tracking_error > 0 else 0
        )
        
        strategy_cum = (1 + aligned_strategy).cumprod()
        benchmark_cum = (1 + aligned_benchmark).cumprod()
        
        win_rate = (aligned_strategy > aligned_benchmark).mean()
        
        return {
            'strategy_annual_return': (1 + aligned_strategy.mean()) ** 252 - 1,
            'benchmark_annual_return': (1 + aligned_benchmark.mean()) ** 252 - 1,
            'excess_return': excess_returns.mean() * 252,
            'tracking_error': tracking_error,
            'information_ratio': information_ratio,
            'win_rate': win_rate,
            'strategy_total_return': strategy_cum.iloc[-1] - 1 if len(strategy_cum) > 0 else 0,
            'benchmark_total_return': benchmark_cum.iloc[-1] - 1 if len(benchmark_cum) > 0 else 0,
            'correlation': aligned_strategy.corr(aligned_benchmark),
            'beta': aligned_strategy.cov(aligned_benchmark) / aligned_benchmark.var() if aligned_benchmark.var() > 0 else 0,
            'alpha': (aligned_strategy.mean() - aligned_benchmark.mean() * 
                     (aligned_strategy.cov(aligned_benchmark) / aligned_benchmark.var())) * 252
        }
    
    def get_all_statistics(self) -> pd.DataFrame:
        """获取所有基准的统计信息"""
        stats_list = []
        
        for code, benchmark in self._benchmarks.items():
            stats = benchmark.get_statistics()
            stats['code'] = code
            stats['name'] = benchmark.name
            stats_list.append(stats)
        
        if not stats_list:
            return pd.DataFrame()
        
        df = pd.DataFrame(stats_list)
        df = df.set_index('code')
        return df
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'benchmarks': {code: bm.to_dict() for code, bm in self._benchmarks.items()},
            'default_benchmark': self._default_benchmark
        }
