"""
回测引擎

执行历史数据模拟交易。
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from enum import Enum
import pandas as pd
import numpy as np

from .matcher import OrderMatcher, Order, OrderType, MatchResult
from .analyzer import PerformanceAnalyzer, PerformanceMetrics
from .reporter import BacktestReporter, ReportConfig
from .benchmark import BenchmarkManager, Benchmark
from .slippage import SlippageModel, SlippageType
from .cost import CostModel


class BacktestMode(Enum):
    """回测模式"""
    EVENT_DRIVEN = "event_driven"
    VECTOR = "vector"


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_capital: float = 1000000.0
    start_date: str = "2020-01-01"
    end_date: str = "2025-12-31"
    commission_rate: float = 0.0003
    slippage_rate: float = 0.001
    benchmark: str = "000300.SH"
    mode: BacktestMode = BacktestMode.EVENT_DRIVEN
    position_limit: float = 0.95
    max_position_per_stock: float = 0.15
    min_trade_amount: int = 100
    price_field: str = "close"


@dataclass
class BacktestResult:
    """回测结果"""
    success: bool
    config: BacktestConfig
    metrics: PerformanceMetrics
    daily_returns: pd.Series
    positions: pd.DataFrame
    trades: List[Dict[str, Any]]
    equity_curve: pd.Series
    benchmark_returns: Optional[pd.Series] = None
    report_path: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'success': self.success,
            'config': {
                'initial_capital': self.config.initial_capital,
                'start_date': self.config.start_date,
                'end_date': self.config.end_date,
                'benchmark': self.config.benchmark
            },
            'metrics': self.metrics.to_dict(),
            'daily_returns': self.daily_returns.to_dict() if len(self.daily_returns) > 0 else {},
            'positions': self.positions.to_dict() if len(self.positions) > 0 else {},
            'trades': self.trades,
            'equity_curve': self.equity_curve.to_dict() if len(self.equity_curve) > 0 else {},
            'error_message': self.error_message
        }


class Portfolio:
    """投资组合"""
    
    def __init__(self, initial_capital: float):
        """初始化投资组合"""
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.total_value = initial_capital
        self.daily_values: List[Dict[str, Any]] = []
        self.trades: List[Dict[str, Any]] = []
    
    def update_position(
        self,
        stock_code: str,
        quantity: int,
        price: float,
        direction: str,
        cost: float = 0.0
    ):
        """更新持仓"""
        trade_value = quantity * price
        
        if direction == 'buy':
            self.cash -= (trade_value + cost)
            
            if stock_code in self.positions:
                old_qty = self.positions[stock_code]['quantity']
                old_cost = self.positions[stock_code]['avg_cost']
                new_qty = old_qty + quantity
                new_avg_cost = (old_qty * old_cost + trade_value) / new_qty if new_qty > 0 else 0
                self.positions[stock_code]['quantity'] = new_qty
                self.positions[stock_code]['avg_cost'] = new_avg_cost
            else:
                self.positions[stock_code] = {
                    'quantity': quantity,
                    'avg_cost': price,
                    'current_price': price
                }
        else:
            self.cash += (trade_value - cost)
            
            if stock_code in self.positions:
                self.positions[stock_code]['quantity'] -= quantity
                if self.positions[stock_code]['quantity'] <= 0:
                    del self.positions[stock_code]
        
        self.trades.append({
            'stock_code': stock_code,
            'direction': direction,
            'quantity': quantity,
            'price': price,
            'value': trade_value,
            'cost': cost,
            'timestamp': datetime.now()
        })
    
    def update_prices(self, prices: Dict[str, float]):
        """更新持仓价格"""
        for stock_code, price in prices.items():
            if stock_code in self.positions:
                self.positions[stock_code]['current_price'] = price
    
    def calculate_total_value(self) -> float:
        """计算总资产"""
        position_value = sum(
            pos['quantity'] * pos['current_price']
            for pos in self.positions.values()
        )
        self.total_value = self.cash + position_value
        return self.total_value
    
    def record_daily_value(self, date: Any):
        """记录每日资产"""
        total_value = self.calculate_total_value()
        position_value = total_value - self.cash
        
        self.daily_values.append({
            'date': date,
            'cash': self.cash,
            'position_value': position_value,
            'total_value': total_value,
            'position_count': len(self.positions)
        })
    
    def get_position_weights(self) -> Dict[str, float]:
        """获取持仓权重"""
        total_value = self.calculate_total_value()
        if total_value == 0:
            return {}
        
        weights = {}
        for stock_code, pos in self.positions.items():
            value = pos['quantity'] * pos['current_price']
            weights[stock_code] = value / total_value
        
        return weights
    
    def get_returns(self) -> pd.Series:
        """获取收益率序列"""
        if len(self.daily_values) < 2:
            return pd.Series(dtype=float)
        
        df = pd.DataFrame(self.daily_values)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        
        returns = df['total_value'].pct_change().dropna()
        return returns


class BacktestEngine:
    """
    回测引擎
    
    执行历史数据模拟交易。
    """
    
    def __init__(
        self,
        config: Optional[BacktestConfig] = None,
        data_loader: Optional[Callable] = None
    ):
        """
        初始化回测引擎
        
        Args:
            config: 回测配置
            data_loader: 数据加载函数
        """
        self.config = config or BacktestConfig()
        self.data_loader = data_loader
        
        self.matcher = OrderMatcher(
            slippage_model="percentage",
            cost_model="ashare",
            slippage_params={'base_rate': self.config.slippage_rate},
            cost_params={'commission_rate': self.config.commission_rate}
        )
        
        self.analyzer = PerformanceAnalyzer()
        self.benchmark_manager = BenchmarkManager()
        self.reporter = BacktestReporter()
        
        self._portfolio: Optional[Portfolio] = None
        self._data: Optional[pd.DataFrame] = None
        self._strategy: Optional[Callable] = None
    
    def set_data(self, data: pd.DataFrame):
        """设置回测数据"""
        self._data = data.copy()
        
        if 'date' in self._data.columns:
            self._data['date'] = pd.to_datetime(self._data['date'])
            self._data = self._data.sort_values('date')
    
    def set_strategy(self, strategy: Callable):
        """设置策略函数"""
        self._strategy = strategy
    
    def set_benchmark(self, benchmark_data: pd.DataFrame, code: str, name: str):
        """设置基准"""
        self.benchmark_manager.create_from_dataframe(benchmark_data, code, name)
        self.benchmark_manager.set_default(code)
    
    def run(
        self,
        strategy: Optional[Callable] = None,
        data: Optional[pd.DataFrame] = None
    ) -> BacktestResult:
        """
        运行回测
        
        Args:
            strategy: 策略函数
            data: 回测数据
            
        Returns:
            BacktestResult: 回测结果
        """
        if strategy:
            self._strategy = strategy
        if data is not None:
            self.set_data(data)
        
        if self._data is None or self._strategy is None:
            return BacktestResult(
                success=False,
                config=self.config,
                metrics=PerformanceMetrics(),
                daily_returns=pd.Series(),
                positions=pd.DataFrame(),
                trades=[],
                equity_curve=pd.Series(),
                error_message="缺少数据或策略"
            )
        
        try:
            if self.config.mode == BacktestMode.EVENT_DRIVEN:
                return self._run_event_driven()
            else:
                return self._run_vectorized()
        except Exception as e:
            return BacktestResult(
                success=False,
                config=self.config,
                metrics=PerformanceMetrics(),
                daily_returns=pd.Series(),
                positions=pd.DataFrame(),
                trades=[],
                equity_curve=pd.Series(),
                error_message=str(e)
            )
    
    def _run_event_driven(self) -> BacktestResult:
        """事件驱动回测"""
        self._portfolio = Portfolio(self.config.initial_capital)
        
        dates = self._data['date'].unique() if 'date' in self._data.columns else self._data.index.unique()
        
        for date in dates:
            if isinstance(date, str):
                date = pd.to_datetime(date)
            
            if date < pd.to_datetime(self.config.start_date):
                continue
            if date > pd.to_datetime(self.config.end_date):
                break
            
            daily_data = self._data[self._data['date'] == date] if 'date' in self._data.columns else self._data.loc[date]
            
            if isinstance(daily_data, pd.Series):
                daily_data = pd.DataFrame([daily_data])
            
            prices = self._extract_prices(daily_data)
            self._portfolio.update_prices(prices)
            
            signals = self._strategy(
                date=date,
                data=daily_data,
                portfolio=self._portfolio,
                context={'config': self.config}
            )
            
            if signals:
                self._execute_signals(signals, daily_data, date)
            
            self._portfolio.record_daily_value(date)
        
        return self._generate_result()
    
    def _run_vectorized(self) -> BacktestResult:
        """向量化回测"""
        self._portfolio = Portfolio(self.config.initial_capital)
        
        signals = self._strategy(
            data=self._data,
            context={'config': self.config}
        )
        
        if signals is None or len(signals) == 0:
            return self._generate_result()
        
        for date, date_signals in signals.groupby(signals.index if hasattr(signals, 'index') else signals['date']):
            if isinstance(date, str):
                date = pd.to_datetime(date)
            
            daily_data = self._data[self._data['date'] == date] if 'date' in self._data.columns else self._data.loc[date]
            
            if isinstance(daily_data, pd.Series):
                daily_data = pd.DataFrame([daily_data])
            
            prices = self._extract_prices(daily_data)
            self._portfolio.update_prices(prices)
            
            self._execute_signals(date_signals.to_dict('records'), daily_data, date)
            
            self._portfolio.record_daily_value(date)
        
        return self._generate_result()
    
    def _extract_prices(self, daily_data: pd.DataFrame) -> Dict[str, float]:
        """提取价格"""
        prices = {}
        price_field = self.config.price_field
        
        for _, row in daily_data.iterrows():
            stock_code = row.get('stock_code', row.get('code', ''))
            if stock_code and price_field in row:
                prices[stock_code] = row[price_field]
        
        return prices
    
    def _execute_signals(
        self,
        signals: List[Dict[str, Any]],
        daily_data: pd.DataFrame,
        date: Any
    ):
        """执行交易信号"""
        for signal in signals:
            stock_code = signal.get('stock_code', signal.get('code', ''))
            direction = signal.get('direction', 'buy')
            quantity = signal.get('quantity', 0)
            target_weight = signal.get('weight', None)
            
            stock_data = daily_data[daily_data['stock_code'] == stock_code] if 'stock_code' in daily_data.columns else daily_data
            
            if len(stock_data) == 0:
                continue
            
            price = stock_data[self.config.price_field].iloc[0]
            
            if target_weight is not None:
                target_value = self._portfolio.total_value * target_weight
                current_value = 0
                if stock_code in self._portfolio.positions:
                    pos = self._portfolio.positions[stock_code]
                    current_value = pos['quantity'] * pos['current_price']
                
                trade_value = target_value - current_value
                quantity = int(trade_value / price / self.config.min_trade_amount) * self.config.min_trade_amount
                
                if trade_value > 0:
                    direction = 'buy'
                else:
                    direction = 'sell'
                    quantity = abs(quantity)
            
            if quantity <= 0:
                continue
            
            order = self.matcher.create_order(
                stock_code=stock_code,
                direction=direction,
                quantity=quantity,
                order_type=OrderType.MARKET
            )
            
            market_data = {
                'close': price,
                'volume': stock_data.get('volume', [1e8]).iloc[0] if 'volume' in stock_data.columns else 1e8
            }
            
            result = self.matcher.match(order, market_data, date)
            
            if result.success:
                self._portfolio.update_position(
                    stock_code=stock_code,
                    quantity=result.filled_quantity,
                    price=result.filled_price,
                    direction=direction,
                    cost=result.transaction_cost.total_cost if result.transaction_cost else 0
                )
    
    def _generate_result(self) -> BacktestResult:
        """生成回测结果"""
        returns = self._portfolio.get_returns()
        
        benchmark_returns = None
        benchmark = self.benchmark_manager.get_default()
        if benchmark:
            benchmark_returns = benchmark.get_returns()
        
        positions_df = pd.DataFrame(self._portfolio.daily_values)
        if len(positions_df) > 0:
            positions_df['date'] = pd.to_datetime(positions_df['date'])
            positions_df = positions_df.set_index('date')
        
        trades = []
        for trade in self._portfolio.trades:
            trade_copy = trade.copy()
            if 'timestamp' in trade_copy:
                trade_copy['timestamp'] = trade_copy['timestamp'].isoformat()
            trades.append(trade_copy)
        
        metrics = self.analyzer.analyze(
            returns=returns,
            benchmark_returns=benchmark_returns,
            positions=positions_df,
            trades=trades
        )
        
        equity_curve = pd.Series(
            [v['total_value'] for v in self._portfolio.daily_values],
            index=[v['date'] for v in self._portfolio.daily_values]
        )
        
        return BacktestResult(
            success=True,
            config=self.config,
            metrics=metrics,
            daily_returns=returns,
            positions=positions_df,
            trades=trades,
            equity_curve=equity_curve,
            benchmark_returns=benchmark_returns
        )
    
    def generate_report(
        self,
        result: BacktestResult,
        filename: Optional[str] = None
    ) -> str:
        """
        生成回测报告
        
        Args:
            result: 回测结果
            filename: 文件名
            
        Returns:
            str: 报告路径
        """
        return self.reporter.generate(result.to_dict(), filename)
    
    def run_multiple(
        self,
        strategies: Dict[str, Callable],
        data: Optional[pd.DataFrame] = None
    ) -> Dict[str, BacktestResult]:
        """
        运行多策略回测
        
        Args:
            strategies: 策略字典 {名称: 策略函数}
            data: 回测数据
            
        Returns:
            Dict[str, BacktestResult]: 回测结果字典
        """
        results = {}
        
        for name, strategy in strategies.items():
            result = self.run(strategy=strategy, data=data)
            results[name] = result
        
        return results
    
    def compare_strategies(
        self,
        results: Dict[str, BacktestResult]
    ) -> pd.DataFrame:
        """
        对比多策略表现
        
        Args:
            results: 回测结果字典
            
        Returns:
            pd.DataFrame: 对比表
        """
        comparison_data = []
        
        for name, result in results.items():
            metrics = result.metrics
            comparison_data.append({
                '策略': name,
                '累计收益': metrics.total_return,
                '年化收益': metrics.annual_return,
                '最大回撤': metrics.max_drawdown,
                '夏普比率': metrics.sharpe_ratio,
                '卡玛比率': metrics.calmar_ratio,
                '胜率': metrics.win_rate,
                '交易次数': metrics.trade_count
            })
        
        return pd.DataFrame(comparison_data)
