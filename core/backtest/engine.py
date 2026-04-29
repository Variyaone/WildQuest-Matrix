"""
回测引擎

执行历史数据模拟交易。
集成：未来函数检测、交易日历、多频率支持。
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, date
from enum import Enum
import pandas as pd
import numpy as np
import logging

from .matcher import OrderMatcher, Order, OrderType, MatchResult
from .analyzer import PerformanceAnalyzer, PerformanceMetrics
from .reporter import BacktestReporter, ReportConfig
from .benchmark import BenchmarkManager, Benchmark
from .slippage import SlippageModel, SlippageType
from .cost import CostModel
from .lookahead_guard import LookAheadGuard, LookAheadBiasError, DataAccessor, LookAheadValidator
from .trading_calendar import TradingCalendar, MarketType, get_trading_calendar, is_trading_day
from .frequency import (
    BarFrequency,
    FrequencyConfig,
    DataResampler,
    MultiFrequencyBacktestEngine,
    FrequencyAwareBacktestConfig,
    detect_data_frequency
)

logger = logging.getLogger(__name__)


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
    enable_lookahead_guard: bool = True
    strict_lookahead_check: bool = True
    frequency: str = "d"
    market: str = "A_SHARE"
    trading_hours_only: bool = True


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
    lookahead_report: Optional[Dict[str, Any]] = None
    frequency_info: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'success': self.success,
            'config': {
                'initial_capital': self.config.initial_capital,
                'start_date': self.config.start_date,
                'end_date': self.config.end_date,
                'benchmark': self.config.benchmark,
                'frequency': self.config.frequency,
                'enable_lookahead_guard': self.config.enable_lookahead_guard
            },
            'metrics': self.metrics.to_dict(),
            'daily_returns': self.daily_returns.to_dict() if len(self.daily_returns) > 0 else {},
            'positions': self.positions.to_dict() if len(self.positions) > 0 else {},
            'trades': self.trades,
            'equity_curve': self.equity_curve.to_dict() if len(self.equity_curve) > 0 else {},
            'error_message': self.error_message,
            'lookahead_report': self.lookahead_report,
            'frequency_info': self.frequency_info
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
        pnl = 0.0
        
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
                # 计算盈亏
                avg_cost = self.positions[stock_code]['avg_cost']
                pnl = (price - avg_cost) * quantity - cost
                
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
            'pnl': pnl,
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
    集成未来函数检测、交易日历、多频率支持。
    """
    
    FREQUENCY_MAP = {
        '1m': BarFrequency.MINUTE_1,
        '5m': BarFrequency.MINUTE_5,
        '15m': BarFrequency.MINUTE_15,
        '30m': BarFrequency.MINUTE_30,
        '60m': BarFrequency.MINUTE_60,
        'd': BarFrequency.DAILY,
        'w': BarFrequency.WEEKLY,
        'M': BarFrequency.MONTHLY,
    }
    
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
            slippage_model="fixed",
            cost_model="ashare",
            slippage_params={'slippage_rate': self.config.slippage_rate},
            cost_params={'commission_rate': self.config.commission_rate}
        )
        
        self.analyzer = PerformanceAnalyzer()
        self.benchmark_manager = BenchmarkManager()
        self.reporter = BacktestReporter()
        
        self._portfolio: Optional[Portfolio] = None
        self._data: Optional[pd.DataFrame] = None
        self._strategy: Optional[Callable] = None
        
        self._lookahead_guard = LookAheadGuard(
            strict_mode=self.config.strict_lookahead_check,
            log_access=True,
            raise_on_violation=False
        )
        
        self._trading_calendar = get_trading_calendar(self.config.market)
        
        self._bar_frequency = self.FREQUENCY_MAP.get(
            self.config.frequency, BarFrequency.DAILY
        )
    
    def set_data(self, data: pd.DataFrame):
        """设置回测数据"""
        self._data = data.copy()
        
        # 重置索引，确保iloc[-1]返回最后一行
        self._data = self._data.reset_index(drop=True)
        
        time_column = 'datetime' if 'datetime' in self._data.columns else 'date'
        if time_column in self._data.columns:
            self._data[time_column] = pd.to_datetime(self._data[time_column])
            self._data = self._data.sort_values(time_column)
            self._data = self._data.reset_index(drop=True)
        
        if self.config.frequency == 'auto':
            detected = detect_data_frequency(self._data, time_column)
            self._bar_frequency = detected
            self.config.frequency = detected.value
            logger.info(f"自动检测数据频率: {detected.value}")
    
    def set_strategy(self, strategy: Callable):
        """设置策略函数"""
        self._strategy = strategy
    
    def set_benchmark(self, benchmark_data: pd.DataFrame, code: str, name: str):
        """设置基准"""
        self.benchmark_manager.create_from_dataframe(benchmark_data, code, name)
        self.benchmark_manager.set_default(code)
    
    def validate_strategy(
        self,
        strategy: Optional[Callable] = None,
        data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        验证策略是否存在未来函数
        
        Args:
            strategy: 策略函数
            data: 数据
            
        Returns:
            Dict: 验证结果
        """
        if strategy is None:
            strategy = self._strategy
        if data is None:
            data = self._data
        
        if strategy is None or data is None:
            return {'valid': False, 'message': '缺少策略或数据'}
        
        validator = LookAheadValidator()
        return validator.validate_strategy(strategy, data)
    
    def estimate_backtest_time(
        self,
        data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        估算回测时间
        
        Args:
            data: 数据
            
        Returns:
            Dict: 估算结果
        """
        if data is None:
            data = self._data
        
        if data is None:
            return {'estimated_seconds': 0, 'message': '无数据'}
        
        time_column = 'datetime' if 'datetime' in data.columns else 'date'
        if time_column in data.columns:
            start = pd.to_datetime(data[time_column].min()).date()
            end = pd.to_datetime(data[time_column].max()).date()
        else:
            return {'estimated_seconds': 0, 'message': '无法确定日期范围'}
        
        stock_count = data['stock_code'].nunique() if 'stock_code' in data.columns else 100
        
        return FrequencyAwareBacktestConfig.estimate_backtest_duration(
            frequency=self._bar_frequency,
            start_date=start,
            end_date=end,
            stock_count=stock_count
        )
    
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
        except LookAheadBiasError as e:
            return BacktestResult(
                success=False,
                config=self.config,
                metrics=PerformanceMetrics(),
                daily_returns=pd.Series(),
                positions=pd.DataFrame(),
                trades=[],
                equity_curve=pd.Series(),
                error_message=f"未来函数错误: {str(e)}",
                lookahead_report=self._lookahead_guard.get_report()
            )
        except Exception as e:
            logger.exception("回测执行失败")
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
        self._lookahead_guard.clear_records()
        
        time_column = 'datetime' if 'datetime' in self._data.columns else 'date'
        
        if self._bar_frequency == BarFrequency.DAILY:
            dates = self._get_trading_dates()
        else:
            dates = self._data[time_column].unique()
        
        accessor = DataAccessor(self._data, self._lookahead_guard, time_column)
        
        for bar_time in dates:
            if isinstance(bar_time, str):
                bar_time = pd.to_datetime(bar_time)
            
            if bar_time < pd.to_datetime(self.config.start_date):
                continue
            if bar_time > pd.to_datetime(self.config.end_date):
                break
            
            self._lookahead_guard.set_bar_time(bar_time)
            
            if self._bar_frequency == BarFrequency.DAILY:
                if hasattr(bar_time, 'date'):
                    bar_date = bar_time.date()
                else:
                    bar_date = bar_time
                if not self._trading_calendar.is_trading_day(bar_date):
                    continue
            
            if time_column in self._data.columns:
                daily_data = self._data[self._data[time_column] == bar_time]
            else:
                daily_data = self._data[self._data['date'] == bar_time]
            
            if isinstance(daily_data, pd.Series):
                daily_data = pd.DataFrame([daily_data])
            
            if len(daily_data) == 0:
                continue
            
            if self.config.enable_lookahead_guard:
                daily_data = self._lookahead_guard.filter_future_data(
                    self._data, time_column
                )
                if time_column in self._data.columns:
                    daily_data = daily_data[daily_data[time_column] == bar_time]
            
            prices = self._extract_prices(daily_data)
            self._portfolio.update_prices(prices)
            
            signals = self._strategy(
                date=bar_time,
                data=daily_data,
                portfolio=self._portfolio,
                accessor=accessor,
                context={'config': self.config}
            )
            
            if signals:
                self._execute_signals(signals, daily_data, bar_time)
            
            self._portfolio.record_daily_value(bar_time)
        
        lookahead_report = None
        if self.config.enable_lookahead_guard and self._lookahead_guard.has_violations():
            lookahead_report = self._lookahead_guard.get_report()
            logger.warning(f"检测到 {len(self._lookahead_guard.get_violations())} 个未来函数违规")
        
        result = self._generate_result()
        result.lookahead_report = lookahead_report
        result.frequency_info = {
            'frequency': self._bar_frequency.value,
            'is_intraday': self._bar_frequency.is_intraday,
            'estimated_time_factor': self._get_time_factor()
        }
        
        return result
    
    def _run_vectorized(self) -> BacktestResult:
        """向量化回测"""
        self._portfolio = Portfolio(self.config.initial_capital)
        
        signals = self._strategy(
            data=self._data,
            context={'config': self.config}
        )
        
        if signals is None or len(signals) == 0:
            return self._generate_result()
        
        time_column = 'datetime' if 'datetime' in self._data.columns else 'date'
        
        for date, date_signals in signals.groupby(
            signals.index if hasattr(signals, 'index') else signals['date']
        ):
            if isinstance(date, str):
                date = pd.to_datetime(date)
            
            self._lookahead_guard.set_bar_time(date)
            
            if time_column in self._data.columns:
                daily_data = self._data[self._data[time_column] == date]
            else:
                daily_data = self._data[self._data['date'] == date]
            
            if isinstance(daily_data, pd.Series):
                daily_data = pd.DataFrame([daily_data])
            
            prices = self._extract_prices(daily_data)
            self._portfolio.update_prices(prices)
            
            self._execute_signals(date_signals.to_dict('records'), daily_data, date)
            
            self._portfolio.record_daily_value(date)
        
        return self._generate_result()
    
    def _get_trading_dates(self) -> List:
        """获取交易日列表"""
        time_column = 'datetime' if 'datetime' in self._data.columns else 'date'
        
        if time_column in self._data.columns:
            all_dates = self._data[time_column].unique()
        else:
            all_dates = self._data['date'].unique()
        
        trading_dates = []
        for d in all_dates:
            if hasattr(d, 'date'):
                bar_date = d.date()
            else:
                bar_date = pd.to_datetime(d).date()
            
            if self._trading_calendar.is_trading_day(bar_date):
                trading_dates.append(d)
        
        return trading_dates
    
    def _get_time_factor(self) -> float:
        """获取时间因子"""
        engine = MultiFrequencyBacktestEngine(self._bar_frequency)
        return engine._estimated_time_factor
    
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
            
            if 'stock_code' in daily_data.columns:
                stock_data = daily_data[daily_data['stock_code'] == stock_code]
            else:
                stock_data = daily_data
            
            if len(stock_data) == 0:
                continue
            
            price = stock_data[self.config.price_field].iloc[0]
            
            if pd.isna(price) or price <= 0:
                continue
            
            if target_weight is not None:
                target_value = self._portfolio.total_value * target_weight
                current_value = 0
                if stock_code in self._portfolio.positions:
                    pos = self._portfolio.positions[stock_code]
                    cp = pos.get('current_price', 0)
                    if pd.isna(cp):
                        cp = 0
                    current_value = pos['quantity'] * cp
                
                if target_weight == 0 and stock_code in self._portfolio.positions:
                    pos = self._portfolio.positions[stock_code]
                    quantity = pos['quantity']
                    direction = 'sell'
                elif target_value < 0:
                    continue
                else:
                    trade_value = target_value - current_value
                    if pd.isna(trade_value):
                        continue
                    quantity = int(trade_value / price / self.config.min_trade_amount) * self.config.min_trade_amount
                    
                    if trade_value > 0:
                        direction = 'buy'
                        max_quantity = int(self._portfolio.cash / price / self.config.min_trade_amount) * self.config.min_trade_amount
                        quantity = min(quantity, max_quantity)
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
                # 添加date字段用于胜率计算
                trade_copy['date'] = trade_copy['timestamp']
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
    
    def run_factor_backtest(
        self,
        factor_data: pd.DataFrame,
        stock_pool: pd.DataFrame = None,
        holding_period: int = 5,
        top_n: int = 50
    ) -> Dict[str, Any]:
        """
        因子回测
        
        Args:
            factor_data: 因子数据，包含 stock_code, date, factor_value 列
            stock_pool: 股票池数据
            holding_period: 持仓周期（天）
            top_n: 选股数量
        
        Returns:
            回测结果字典
        """
        import time
        from datetime import timedelta
        
        start_time = time.time()
        
        logger.info("=" * 60)
        logger.info("开始因子回测")
        logger.info("=" * 60)
        
        if factor_data is None or factor_data.empty:
            logger.error("因子数据为空")
            return {
                "success": False,
                "error": "因子数据为空",
                "sharpe_ratio": 0,
                "max_drawdown": 0,
                "annual_return": 0,
                "win_rate": 0,
                "total_trades": 0
            }
        
        logger.info(f"因子数据: {len(factor_data)} 行")
        logger.info(f"持仓周期: {holding_period} 天")
        logger.info(f"选股数量: {top_n}")
        
        required_cols = ['stock_code', 'date', 'factor_value']
        for col in required_cols:
            if col not in factor_data.columns:
                logger.error(f"缺少必要列: {col}")
                return {
                    "success": False,
                    "error": f"缺少必要列: {col}",
                    "sharpe_ratio": 0,
                    "max_drawdown": 0,
                    "annual_return": 0,
                    "win_rate": 0,
                    "total_trades": 0
                }
        
        factor_data['date'] = pd.to_datetime(factor_data['date'])
        dates = sorted(factor_data['date'].unique())
        
        # 设置回测数据
        self.set_data(factor_data)
        
        if len(dates) < 10:
            logger.error("日期数量不足")
            return {
                "success": False,
                "error": "日期数量不足",
                "sharpe_ratio": 0,
                "max_drawdown": 0,
                "annual_return": 0,
                "win_rate": 0,
                "total_trades": 0
            }
        
        logger.info(f"日期范围: {dates[0]} 至 {dates[-1]} ({len(dates)} 个交易日)")
        
        portfolio_values = []
        current_holdings = {}
        cash = self.config.initial_capital
        total_value = cash
        
        trades = []
        rebalance_dates = dates[::holding_period]
        
        for i, date in enumerate(rebalance_dates):
            try:
                date_data = factor_data[factor_data['date'] == date]
                
                if date_data.empty:
                    continue
                
                date_data = date_data.sort_values('factor_value', ascending=False)
                selected_stocks = date_data.head(top_n)['stock_code'].tolist()
                
                for stock_code in list(current_holdings.keys()):
                    shares = current_holdings[stock_code]
                    
                    logger.info(f"准备卖出 {stock_code}, 持仓数量: {shares}")
                    
                    try:
                        stock_history = self._data[
                            (self._data['stock_code'] == stock_code) & 
                            (self._data['date'] <= date)
                        ]
                        
                        if not stock_history.empty:
                            sell_price = stock_history.iloc[-1][self.config.price_field]
                            proceeds = shares * sell_price * (1 - self.config.commission_rate)
                            cash += proceeds
                            
                            trades.append({
                                'date': date,
                                'stock_code': stock_code,
                                'direction': 'sell',
                                'shares': shares,
                                'price': sell_price
                            })
                            
                            logger.info(f"成功卖出 {stock_code}, 价格: {sell_price}, 收益: {proceeds}")
                    except Exception as e:
                        logger.warning(f"卖出 {stock_code} 失败: {e}")
                    
                    del current_holdings[stock_code]
                
                if selected_stocks and cash > 0:
                    weight_per_stock = 1.0 / len(selected_stocks)
                    amount_per_stock = total_value * weight_per_stock
                    
                    for stock_code in selected_stocks:
                        try:
                            stock_history = self._data[
                                (self._data['stock_code'] == stock_code) & 
                                (self._data['date'] <= date)
                            ]
                            
                            if not stock_history.empty:
                                buy_price = stock_history.iloc[-1][self.config.price_field]
                                shares = int(amount_per_stock / buy_price / 100) * 100
                                
                                if shares > 0:
                                    cost = shares * buy_price * (1 + self.config.commission_rate)
                                    if cost <= cash:
                                        cash -= cost
                                        current_holdings[stock_code] = shares
                                        
                                        trades.append({
                                            'date': date,
                                            'stock_code': stock_code,
                                            'direction': 'buy',
                                            'shares': shares,
                                            'price': buy_price
                                        })
                        except Exception as e:
                            logger.warning(f"买入 {stock_code} 失败: {e}")
                
                position_value = 0
                for stock_code, shares in current_holdings.items():
                    try:
                        stock_history = self._data[
                            (self._data['stock_code'] == stock_code) & 
                            (self._data['date'] <= date)
                        ]
                        
                        if not stock_history.empty:
                            current_price = stock_history.iloc[-1][self.config.price_field]
                            position_value += shares * current_price
                    except Exception:
                        pass
                
                total_value = cash + position_value
                portfolio_values.append({
                    'date': date,
                    'total_value': total_value,
                    'cash': cash,
                    'position_value': position_value
                })
                
            except Exception as e:
                logger.error(f"处理日期 {date} 失败: {e}")
        
        if not portfolio_values:
            logger.error("没有有效的组合数据")
            return {
                "success": False,
                "error": "没有有效的组合数据",
                "sharpe_ratio": 0,
                "max_drawdown": 0,
                "annual_return": 0,
                "win_rate": 0,
                "total_trades": 0
            }
        
        portfolio_df = pd.DataFrame(portfolio_values)
        portfolio_df['daily_return'] = portfolio_df['total_value'].pct_change()
        
        total_return = (portfolio_df['total_value'].iloc[-1] / self.config.initial_capital - 1)
        years = (dates[-1] - dates[0]).days / 365.0
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        daily_returns = portfolio_df['daily_return'].dropna()
        sharpe_ratio = (daily_returns.mean() / daily_returns.std() * np.sqrt(252)) if daily_returns.std() > 0 else 0
        
        cumulative = (1 + daily_returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = abs(drawdown.min())
        
        # 正确计算胜率：匹配买入和卖出交易，计算盈亏
        winning_trades = 0
        total_sell_trades = sum(1 for t in trades if t['direction'] == 'sell')
        
        if total_sell_trades > 0:
            for sell_trade in trades:
                if sell_trade['direction'] == 'sell':
                    # 找到对应的买入交易
                    buy_trades = [t for t in trades 
                                 if t['stock_code'] == sell_trade['stock_code'] 
                                 and t['direction'] == 'buy' 
                                 and t['date'] < sell_trade['date']]
                    
                    if buy_trades:
                        # 使用最近一次买入的价格
                        buy_trade = max(buy_trades, key=lambda x: x['date'])
                        if sell_trade['price'] > buy_trade['price']:
                            winning_trades += 1
        
        win_rate = winning_trades / total_sell_trades if total_sell_trades > 0 else 0
        
        duration = time.time() - start_time
        
        logger.info("=" * 60)
        logger.info("因子回测完成")
        logger.info(f"  总收益: {total_return:.2%}")
        logger.info(f"  年化收益: {annual_return:.2%}")
        logger.info(f"  夏普比率: {sharpe_ratio:.2f}")
        logger.info(f"  最大回撤: {max_drawdown:.2%}")
        logger.info(f"  胜率: {win_rate:.2%}")
        logger.info(f"  交易次数: {len(trades)}")
        logger.info(f"  耗时: {duration:.2f} 秒")
        logger.info("=" * 60)
        
        return {
            "success": True,
            "total_return": total_return,
            "annual_return": annual_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "total_trades": len(trades),
            "duration_seconds": duration,
            "portfolio_values": portfolio_df.to_dict('records'),
            "trades": trades
        }
