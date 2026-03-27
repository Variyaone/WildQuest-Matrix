"""
OKXTrading 回测引擎测试脚本

这个脚本演示了如何使用回测引擎。
"""

import sys
import os

# 添加父目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest_engine import (
    BacktestEngine,
    BaseStrategy,
    Order,
    OrderType,
    OrderSide,
    print_backtest_summary,
)

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any


def generate_sample_data(
    n_days: int = 365,
    start_price: float = 100,
    volatility: float = 0.02,
    drift: float = 0.0005
) -> pd.DataFrame:
    """
    生成模拟市场数据

    Args:
        n_days: 天数
        start_price: 起始价格
        volatility: 波动率
        drift: 漂移率（日均收益）

    Returns:
        包含 OHLCV 列的DataFrame
    """
    np.random.seed(42)

    # 生成日期
    dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(n_days)]

    # 生成收益率（布朗运动）
    returns = np.random.normal(drift, volatility, n_days)

    # 生成价格序列
    price = start_price * np.cumprod(1 + returns)

    # 生成K线数据
    data = pd.DataFrame({
        'date': dates,
        'open': price * (1 + np.random.normal(0, 0.002, n_days)),
        'high': price * (1 + np.abs(np.random.normal(0, 0.008, n_days))),
        'low': price * (1 - np.abs(np.random.normal(0, 0.008, n_days))),
        'close': price,
        'volume': np.random.uniform(1000000, 10000000, n_days)
    })

    # 确保high >= close >= low
    data['high'] = data[['high', 'close']].max(axis=1)
    data['low'] = data[['low', 'close']].min(axis=1)
    data['high'] = data[['high', 'open']].max(axis=1)
    data['low'] = data[['low', 'open']].min(axis=1)

    return data.set_index('date')


class DemoStrategy(BaseStrategy):
    """
    演示策略：双均线交叉

    规则：
    - 快线上穿慢线：买入
    - 快线下穿慢线：卖出
    """

    def __init__(self, name: str, params: Dict[str, Any]):
        super().__init__(name, params)
        self.fast_period = params.get('fast_period', 10)
        self.slow_period = params.get('slow_period', 30)
        self.position_size = params.get('position_size', 10)  # 持仓数量

    def generate_signals(
        self,
        data: Dict[str, pd.DataFrame],
        positions: Dict[str, Any],
        current_time: datetime
    ) -> List[Order]:
        orders = []

        for symbol, df in data.items():
            # 检查数据长度
            if len(df) < self.slow_period:
                continue

            # 计算均线
            df['fast_ma'] = df['close'].rolling(window=self.fast_period).mean()
            df['slow_ma'] = df['close'].rolling(window=self.slow_period).mean()

            # 获取当前和前一行
            current_row = df.iloc[-1]
            prev_row = df.iloc[-2] if len(df) > 1 else current_row

            # 检查是否有NaN值
            if pd.isna(current_row['fast_ma']) or pd.isna(current_row['slow_ma']):
                continue
            if pd.isna(prev_row['fast_ma']) or pd.isna(prev_row['slow_ma']):
                continue

            # 买入信号：快线上穿慢线
            if prev_row['fast_ma'] <= prev_row['slow_ma'] and current_row['fast_ma'] > current_row['slow_ma']:
                if symbol not in positions:
                    orders.append(Order(
                        symbol=symbol,
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        quantity=self.position_size,
                        timestamp=current_time
                    ))

            # 卖出信号：快线下穿慢线
            elif prev_row['fast_ma'] >= prev_row['slow_ma'] and current_row['fast_ma'] < current_row['slow_ma']:
                if symbol in positions:
                    orders.append(Order(
                        symbol=symbol,
                        side=OrderSide.SELL,
                        order_type=OrderType.MARKET,
                        quantity=positions[symbol].quantity,
                        timestamp=current_time
                    ))

        return orders


def main():
    """主函数"""
    print("="*70)
    print("OKXTrading 回测引擎 - 测试演示")
    print("="*70)

    # 1. 生成测试数据
    print("\n生成测试数据...")
    data = {
        'BTC-USDT': generate_sample_data(n_days=500, start_price=100, volatility=0.02, drift=0.0003),
        'ETH-USDT': generate_sample_data(n_days=500, start_price=200, volatility=0.025, drift=0.0002),
    }
    print(f"  已生成 {len(data)} 个标的的数据")
    for symbol, df in data.items():
        print(f"  {symbol}: {len(df)} 天数据, 价格范围: ${df['low'].min():.2f} - ${df['high'].max():.2f}")

    # 2. 创建回测引擎
    print("\n创建回测引擎...")
    engine = BacktestEngine(
        initial_capital=100_000,
        maker_commission=0.0008,
        taker_commission=0.0010,
        slippage_model='size_based',
        market_impact_model='linear'
    )
    print(f"  初始资金: ${engine.initial_capital:,.2f}")
    print(f"  Maker手续费: {engine.executor.maker_commission * 100:.3f}%")
    print(f"  Taker手续费: {engine.executor.taker_commission * 100:.2f}%")
    print(f"  滑点模型: {engine.executor.slippage_model}")
    print(f"  市场冲击模型: {engine.executor.market_impact_model}")

    # 3. 创建策略
    print("\n创建策略...")
    strategy = DemoStrategy(
        name="DualMovingAverage",
        params={
            'fast_period': 15,
            'slow_period': 45,
            'position_size': 20
        }
    )
    print(f"  策略名称: {strategy.name}")
    print(f"  快线周期: {strategy.fast_period}")
    print(f"  慢线周期: {strategy.slow_period}")
    print(f"  持仓数量: {strategy.position_size}")

    # 4. 运行回测
    print("\n运行回测...")
    result = engine.run_backtest(data, strategy)

    # 5. 打印结果
    print_backtest_summary(result)

    # 6. 保存报告
    report_file = "backtest_results.json"
    report = engine.generate_report(result, report_file)
    print(f"\n回测报告已保存到: {os.path.join(os.getcwd(), report_file)}")

    # 7. 分析结果
    print("\n" + "="*70)
    print("结果分析")
    print("="*70)

    # 计算关键指标
    if result.metrics.sharpe_ratio > 1.0:
        print("\n✓ 夏普比率良好 (>1.0)")
    elif result.metrics.sharpe_ratio > 0.5:
        print("\n○ 夏普比率一般 (>0.5)")
    else:
        print("\n✗ 夏普比率偏低 (<0.5)")

    if result.metrics.max_drawdown > -0.10:
        print("✓ 最大回撤控制良好 (<10%)")
    elif result.metrics.max_drawdown > -0.20:
        print("○ 最大回撤可接受 (<20%)")
    else:
        print("✗ 最大回撤过大 (>20%)")

    if result.metrics.win_rate > 0.6:
        print("✓ 胜率优秀 (>60%)")
    elif result.metrics.win_rate > 0.5:
        print("○ 胜率尚可 (>50%)")
    else:
        print("✗ 胜率偏低 (<50%)")

    # 成本分析
    total_pnl = result.final_capital - result.initial_capital
    total_costs = result.metrics.total_commission

    print(f"\n收益 vs 成本:")
    print(f"  净收益: ${total_pnl:,.2f}")
    print(f"  手续费: ${total_costs:,.2f} ({total_costs/total_pnl*100 if total_pnl != 0 else 0:.2f}% of profit)")

    print("\n" + "="*70)
    print("测试完成！")
    print("="*70)


if __name__ == "__main__":
    main()
