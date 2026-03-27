"""
策略回测器模块

多维度回测策略表现，支持不同时间段、市场环境、参数组合和压力测试。
"""

from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import pandas as pd
import numpy as np

from .registry import (
    StrategyMetadata, 
    StrategyPerformance, 
    RebalanceFrequency,
    get_strategy_registry
)
from .selector import StockSelector, SelectionResult, get_stock_selector
from ..infrastructure.exceptions import StrategyException


class BacktestMode(Enum):
    """回测模式"""
    FULL = "full"
    WALK_FORWARD = "walk_forward"
    MONTE_CARLO = "monte_carlo"


@dataclass
class Position:
    """持仓信息"""
    stock_code: str
    shares: int
    cost_price: float
    current_price: float
    market_value: float
    profit_loss: float
    profit_loss_pct: float
    holding_days: int = 0
    
    def update_price(self, price: float):
        """更新价格"""
        self.current_price = price
        self.market_value = self.shares * price
        self.profit_loss = self.market_value - self.shares * self.cost_price
        self.profit_loss_pct = self.profit_loss / (self.shares * self.cost_price)


@dataclass
class Portfolio:
    """投资组合"""
    date: str
    cash: float
    positions: Dict[str, Position]
    total_value: float
    daily_return: float = 0.0
    
    def get_position_value(self) -> float:
        """获取持仓市值"""
        return sum(p.market_value for p in self.positions.values())
    
    def get_position_count(self) -> int:
        """获取持仓数量"""
        return len(self.positions)


@dataclass
class Trade:
    """交易记录"""
    date: str
    stock_code: str
    direction: str  # 'buy' or 'sell'
    shares: int
    price: float
    amount: float
    commission: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "stock_code": self.stock_code,
            "direction": self.direction,
            "shares": self.shares,
            "price": self.price,
            "amount": self.amount,
            "commission": self.commission
        }


@dataclass
class BacktestResult:
    """回测结果"""
    strategy_id: str
    success: bool
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    profit_factor: float
    portfolios: List[Portfolio] = field(default_factory=list)
    trades: List[Trade] = field(default_factory=list)
    performance: Optional[StrategyPerformance] = None
    error_message: Optional[str] = None


class PortfolioSimulator:
    """
    组合模拟器
    
    模拟投资组合的运作。
    """
    
    def __init__(
        self,
        initial_capital: float = 1000000.0,
        commission_rate: float = 0.0003,
        slippage: float = 0.001
    ):
        """初始化组合模拟器"""
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.portfolios: List[Portfolio] = []
    
    def reset(self):
        """重置模拟器"""
        self.cash = self.initial_capital
        self.positions = {}
        self.trades = []
        self.portfolios = []
    
    def buy(
        self,
        stock_code: str,
        price: float,
        amount: float,
        date: str
    ) -> bool:
        """买入"""
        actual_price = price * (1 + self.slippage)
        shares = int(amount / actual_price / 100) * 100
        
        if shares <= 0:
            return False
        
        total_cost = shares * actual_price
        commission = total_cost * self.commission_rate
        
        if total_cost + commission > self.cash:
            shares = int((self.cash - commission) / actual_price / 100) * 100
            if shares <= 0:
                return False
            total_cost = shares * actual_price
            commission = total_cost * self.commission_rate
        
        self.cash -= (total_cost + commission)
        
        if stock_code in self.positions:
            pos = self.positions[stock_code]
            total_shares = pos.shares + shares
            total_cost_basis = pos.shares * pos.cost_price + total_cost
            pos.shares = total_shares
            pos.cost_price = total_cost_basis / total_shares
            pos.current_price = actual_price
            pos.market_value = total_shares * actual_price
        else:
            self.positions[stock_code] = Position(
                stock_code=stock_code,
                shares=shares,
                cost_price=actual_price,
                current_price=actual_price,
                market_value=shares * actual_price,
                profit_loss=0,
                profit_loss_pct=0
            )
        
        self.trades.append(Trade(
            date=date,
            stock_code=stock_code,
            direction="buy",
            shares=shares,
            price=actual_price,
            amount=total_cost,
            commission=commission
        ))
        
        return True
    
    def sell(
        self,
        stock_code: str,
        price: float,
        shares: Optional[int] = None,
        date: str = ""
    ) -> bool:
        """卖出"""
        if stock_code not in self.positions:
            return False
        
        pos = self.positions[stock_code]
        
        if shares is None:
            shares = pos.shares
        
        if shares > pos.shares:
            shares = pos.shares
        
        actual_price = price * (1 - self.slippage)
        total_value = shares * actual_price
        commission = total_value * self.commission_rate
        
        self.cash += (total_value - commission)
        
        pos.shares -= shares
        if pos.shares == 0:
            del self.positions[stock_code]
        else:
            pos.market_value = pos.shares * actual_price
        
        self.trades.append(Trade(
            date=date,
            stock_code=stock_code,
            direction="sell",
            shares=shares,
            price=actual_price,
            amount=total_value,
            commission=commission
        ))
        
        return True
    
    def update_prices(self, prices: Dict[str, float]):
        """更新价格"""
        for stock_code, price in prices.items():
            if stock_code in self.positions:
                self.positions[stock_code].update_price(price)
    
    def record_portfolio(self, date: str):
        """记录组合状态"""
        position_value = self.get_position_value()
        total_value = self.cash + position_value
        
        portfolio = Portfolio(
            date=date,
            cash=self.cash,
            positions=self.positions.copy(),
            total_value=total_value
        )
        
        self.portfolios.append(portfolio)
    
    def get_position_value(self) -> float:
        """获取持仓市值"""
        return sum(p.market_value for p in self.positions.values())
    
    def get_total_value(self) -> float:
        """获取总资产"""
        return self.cash + self.get_position_value()


class PerformanceCalculator:
    """
    绩效计算器
    
    计算策略绩效指标。
    """
    
    @staticmethod
    def calculate_returns(portfolios: List[Portfolio]) -> pd.Series:
        """计算收益率序列"""
        if len(portfolios) < 2:
            return pd.Series()
        
        values = [p.total_value for p in portfolios]
        returns = pd.Series(values).pct_change().dropna()
        
        return returns
    
    @staticmethod
    def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.03) -> float:
        """计算夏普比率"""
        if returns.empty or returns.std() == 0:
            return 0.0
        
        excess_return = returns.mean() * 252 - risk_free_rate
        volatility = returns.std() * np.sqrt(252)
        
        return excess_return / volatility if volatility > 0 else 0.0
    
    @staticmethod
    def calculate_max_drawdown(portfolios: List[Portfolio]) -> float:
        """计算最大回撤"""
        if not portfolios:
            return 0.0
        
        values = [p.total_value for p in portfolios]
        peak = values[0]
        max_dd = 0.0
        
        for value in values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
        
        return -max_dd
    
    @staticmethod
    def calculate_win_rate(trades: List[Trade]) -> float:
        """计算胜率"""
        if not trades:
            return 0.0
        
        buy_trades = {t.stock_code: t for t in trades if t.direction == "buy"}
        sell_trades = [t for t in trades if t.direction == "sell"]
        
        wins = 0
        total = 0
        
        for sell in sell_trades:
            if sell.stock_code in buy_trades:
                buy = buy_trades[sell.stock_code]
                if sell.price > buy.price:
                    wins += 1
                total += 1
        
        return wins / total if total > 0 else 0.0
    
    @staticmethod
    def calculate_profit_factor(trades: List[Trade]) -> float:
        """计算盈亏比"""
        if not trades:
            return 0.0
        
        profits = []
        losses = []
        
        buy_trades = {t.stock_code: t for t in trades if t.direction == "buy"}
        
        for sell in trades:
            if sell.direction == "sell" and sell.stock_code in buy_trades:
                buy = buy_trades[sell.stock_code]
                pnl = (sell.price - buy.price) * sell.shares
                if pnl > 0:
                    profits.append(pnl)
                else:
                    losses.append(abs(pnl))
        
        total_profit = sum(profits)
        total_loss = sum(losses)
        
        return total_profit / total_loss if total_loss > 0 else float('inf')


class StrategyBacktester:
    """
    策略回测器
    
    多维度回测策略表现。
    """
    
    def __init__(
        self,
        initial_capital: float = 1000000.0,
        commission_rate: float = 0.0003,
        slippage: float = 0.001
    ):
        """初始化策略回测器"""
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        
        self._registry = get_strategy_registry()
        self._selector = get_stock_selector()
        self._simulator = PortfolioSimulator(
            initial_capital, commission_rate, slippage
        )
        self._perf_calculator = PerformanceCalculator()
    
    def backtest(
        self,
        strategy: Union[str, StrategyMetadata],
        price_data: pd.DataFrame,
        factor_data: Dict[str, pd.DataFrame],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        mode: BacktestMode = BacktestMode.FULL
    ) -> BacktestResult:
        """
        回测策略
        
        Args:
            strategy: 策略ID或策略元数据
            price_data: 价格数据
            factor_data: 因子数据
            start_date: 开始日期
            end_date: 结束日期
            mode: 回测模式
            
        Returns:
            BacktestResult: 回测结果
        """
        if isinstance(strategy, str):
            strategy_meta = self._registry.get(strategy)
            if strategy_meta is None:
                return BacktestResult(
                    strategy_id=strategy,
                    success=False,
                    start_date=start_date or "",
                    end_date=end_date or "",
                    initial_capital=self.initial_capital,
                    final_capital=0,
                    total_return=0,
                    annual_return=0,
                    sharpe_ratio=0,
                    max_drawdown=0,
                    win_rate=0,
                    total_trades=0,
                    profit_factor=0,
                    error_message=f"策略不存在: {strategy}"
                )
        else:
            strategy_meta = strategy
        
        strategy_id = strategy_meta.id
        
        try:
            self._simulator.reset()
            
            if 'date' in price_data.columns:
                dates = sorted(price_data['date'].unique())
            else:
                dates = sorted(price_data.index.unique())
            
            if start_date:
                dates = [d for d in dates if d >= start_date]
            if end_date:
                dates = [d for d in dates if d <= end_date]
            
            if not dates:
                return BacktestResult(
                    strategy_id=strategy_id,
                    success=False,
                    start_date=start_date or "",
                    end_date=end_date or "",
                    initial_capital=self.initial_capital,
                    final_capital=0,
                    total_return=0,
                    annual_return=0,
                    sharpe_ratio=0,
                    max_drawdown=0,
                    win_rate=0,
                    total_trades=0,
                    profit_factor=0,
                    error_message="没有有效的回测日期"
                )
            
            rebalance_dates = self._get_rebalance_dates(
                dates, 
                strategy_meta.rebalance_freq
            )
            
            current_positions = []
            
            for date in dates:
                prices = self._get_prices(price_data, date)
                
                self._simulator.update_prices(prices)
                
                if date in rebalance_dates:
                    selection_result = self._selector.select(
                        strategy_meta,
                        date,
                        factor_data
                    )
                    
                    if selection_result.success:
                        new_stocks = [s.stock_code for s in selection_result.selections]
                        
                        for stock in current_positions:
                            if stock not in new_stocks and stock in prices:
                                self._simulator.sell(stock, prices[stock], date=date)
                        
                        position_value = self._simulator.get_total_value() / strategy_meta.max_positions
                        
                        for selection in selection_result.selections:
                            if selection.stock_code in prices:
                                if selection.stock_code not in current_positions:
                                    self._simulator.buy(
                                        selection.stock_code,
                                        prices[selection.stock_code],
                                        position_value,
                                        date
                                    )
                        
                        current_positions = new_stocks
                
                self._simulator.record_portfolio(date)
            
            portfolios = self._simulator.portfolios
            trades = self._simulator.trades
            
            returns = self._perf_calculator.calculate_returns(portfolios)
            
            final_capital = portfolios[-1].total_value if portfolios else self.initial_capital
            total_return = (final_capital - self.initial_capital) / self.initial_capital
            
            n_days = len(dates)
            annual_return = (1 + total_return) ** (252 / n_days) - 1 if n_days > 0 else 0
            
            sharpe_ratio = self._perf_calculator.calculate_sharpe_ratio(returns)
            max_drawdown = self._perf_calculator.calculate_max_drawdown(portfolios)
            win_rate = self._perf_calculator.calculate_win_rate(trades)
            profit_factor = self._perf_calculator.calculate_profit_factor(trades)
            
            performance = StrategyPerformance(
                annual_return=annual_return,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                total_trades=len(trades),
                profit_factor=profit_factor
            )
            
            self._registry.update_backtest_performance(strategy_id, performance)
            
            return BacktestResult(
                strategy_id=strategy_id,
                success=True,
                start_date=dates[0],
                end_date=dates[-1],
                initial_capital=self.initial_capital,
                final_capital=final_capital,
                total_return=total_return,
                annual_return=annual_return,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                total_trades=len(trades),
                profit_factor=profit_factor,
                portfolios=portfolios,
                trades=trades,
                performance=performance
            )
            
        except Exception as e:
            return BacktestResult(
                strategy_id=strategy_id,
                success=False,
                start_date=start_date or "",
                end_date=end_date or "",
                initial_capital=self.initial_capital,
                final_capital=0,
                total_return=0,
                annual_return=0,
                sharpe_ratio=0,
                max_drawdown=0,
                win_rate=0,
                total_trades=0,
                profit_factor=0,
                error_message=str(e)
            )
    
    def _get_rebalance_dates(
        self,
        dates: List[str],
        freq: RebalanceFrequency
    ) -> List[str]:
        """获取调仓日期"""
        if freq == RebalanceFrequency.DAILY:
            return dates
        elif freq == RebalanceFrequency.WEEKLY:
            return dates[::5]
        elif freq == RebalanceFrequency.BIWEEKLY:
            return dates[::10]
        elif freq == RebalanceFrequency.MONTHLY:
            return dates[::20]
        elif freq == RebalanceFrequency.QUARTERLY:
            return dates[::60]
        return dates[::5]
    
    def _get_prices(
        self,
        price_data: pd.DataFrame,
        date: str
    ) -> Dict[str, float]:
        """获取指定日期的价格"""
        if 'date' in price_data.columns:
            day_data = price_data[price_data['date'] == date]
        else:
            day_data = price_data.loc[date] if date in price_data.index else pd.DataFrame()
        
        if day_data.empty:
            return {}
        
        price_col = 'close' if 'close' in day_data.columns else 'price'
        stock_col = 'stock_code' if 'stock_code' in day_data.columns else 'code'
        
        if price_col in day_data.columns and stock_col in day_data.columns:
            return dict(zip(day_data[stock_col], day_data[price_col]))
        
        return {}
    
    def generate_backtest_report(
        self,
        result: BacktestResult
    ) -> str:
        """生成回测报告"""
        if not result.success:
            return f"回测失败: {result.error_message}"
        
        lines = [
            f"策略回测报告 - {result.strategy_id}",
            "=" * 50,
            f"回测区间: {result.start_date} 至 {result.end_date}",
            f"初始资金: {result.initial_capital:,.2f}",
            f"最终资金: {result.final_capital:,.2f}",
            "",
            "收益指标:",
            "-" * 50,
            f"  总收益率: {result.total_return:.2%}",
            f"  年化收益率: {result.annual_return:.2%}",
            f"  夏普比率: {result.sharpe_ratio:.2f}",
            "",
            "风险指标:",
            "-" * 50,
            f"  最大回撤: {result.max_drawdown:.2%}",
            f"  胜率: {result.win_rate:.2%}",
            f"  盈亏比: {result.profit_factor:.2f}",
            "",
            "交易统计:",
            "-" * 50,
            f"  总交易次数: {result.total_trades}",
        ]
        
        return "\n".join(lines)


_default_backtester: Optional[StrategyBacktester] = None


def get_strategy_backtester(
    initial_capital: float = 1000000.0,
    commission_rate: float = 0.0003,
    slippage: float = 0.001
) -> StrategyBacktester:
    """获取全局策略回测器实例"""
    global _default_backtester
    if _default_backtester is None:
        _default_backtester = StrategyBacktester(initial_capital, commission_rate, slippage)
    return _default_backtester


def reset_strategy_backtester():
    """重置全局策略回测器"""
    global _default_backtester
    _default_backtester = None
