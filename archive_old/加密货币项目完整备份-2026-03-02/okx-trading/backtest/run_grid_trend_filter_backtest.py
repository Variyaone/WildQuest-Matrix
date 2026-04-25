"""
Grid Trend Filter Strategy 回测脚本

针对GridTrendFilterStrategy进行回测验证
"""

import sys
import os
import json

# 添加父目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest_engine import (
    BacktestEngine,
    print_backtest_summary,
)

from grid_trend_filter_strategy import GridTrendFilterStrategy

import pandas as pd
from datetime import datetime


def load_btc_data(filepath: str) -> pd.DataFrame:
    """
    加载BTC历史数据

    Args:
        filepath: CSV文件路径

    Returns:
        DataFrame，索引为datetime
    """
    df = pd.read_csv(filepath)

    # 转换日期列
    df['date'] = pd.to_datetime(df['date'])

    # 设置索引
    df = df.set_index('date')

    return df


def main():
    """主函数"""
    print("="*70)
    print("Grid Trend Filter Strategy - 回测")
    print("="*70)

    # 1. 加载数据
    data_path = "/Users/variya/.openclaw/workspace-architect/backtest/data/btc_usdt_90d.csv"
    print(f"\n加载数据: {data_path}")

    if not os.path.exists(data_path):
        print(f"错误: 数据文件不存在: {data_path}")
        return

    data = load_btc_data(data_path)
    print(f"  数据期间: {data.index[0]} 到 {data.index[-1]}")
    print(f"  数据长度: {len(data)} 条")
    print(f"  价格范围: ${data['low'].min():.2f} - ${data['high'].max():.2f}")
    print(f"  起始价格: ${data.iloc[0]['close']:.2f}")
    print(f"  结束价格: ${data.iloc[-1]['close']:.2f}")

    # 计算期间涨跌幅
    start_price = data.iloc[0]['close']
    end_price = data.iloc[-1]['close']
    total_return_pct = (end_price - start_price) / start_price * 100
    print(f"  期间涨跌: {total_return_pct:+.2f}%")

    # 准备回测数据
    data_dict = {'BTC-USDT': data}

    # 2. 创建回测引擎
    print("\n初始化回测引擎...")
    engine = BacktestEngine(
        initial_capital=100_000,
        maker_commission=0.0008,
        taker_commission=0.0010,
        slippage_model='size_based',
        market_impact_model='linear'
    )
    print(f"  初始资金: ${engine.initial_capital:,.2f}")

    # 3. 创建GridTrendFilterStrategy策略
    print("\n创建策略: GridTrendFilterStrategy")
    strategy_params = {
        'ma_short_period': 20,
        'ma_long_period': 50,
        'grid_count': 6,  # 6格
        'investment_per_grid': 8000,  # 每格$8,000
        'price_range_pct': 0.30,  # ±15%
        'symbol': 'BTC-USDT',
        'hard_stop_loss_pct': 0.05,  # 硬止损-5%
        'daily_stop_loss_pct': 0.03,  # 每日止损-3%
    }

    print(f"  策略参数:")
    print(f"    MA短期周期: {strategy_params['ma_short_period']}日")
    print(f"    MA长期周期: {strategy_params['ma_long_period']}日")
    print(f"    网格数量: {strategy_params['grid_count']}格")
    print(f"    单格金额: ${strategy_params['investment_per_grid']:,.0f}")
    print(f"    价格区间: ±{strategy_params['price_range_pct']*100:.1f}%")
    print(f"    硬止损: {strategy_params['hard_stop_loss_pct']*100:.1f}%")
    print(f"    每日止损: {strategy_params['daily_stop_loss_pct']*100:.1f}%")

    strategy = GridTrendFilterStrategy(
        name="GridTrendFilter",
        params=strategy_params
    )

    # 4. 设置策略（用于回调）
    engine._current_strategy = strategy

    # 5. 运行回测
    print("\n" + "="*70)
    print("开始回测...")
    print("="*70)

    result = engine.run_backtest(data_dict, strategy)

    # 6. 打印结果
    print("\n" + "="*70)
    print("回测结果摘要")
    print("="*70)
    print_backtest_summary(result)

    # 7. 保存报告
    report_path = "/Users/variya/.openclaw/workspace-architect/okx-trading/backtest/grid_trend_filter_results.json"
    report = engine.generate_report(result, report_path)
    print(f"\n回测报告已保存到: {report_path}")

    # 8. 生成详细分析报告
    print("\n" + "="*70)
    print("结果分析")
    print("="*70)

    # 目标指标对比
    print("\n目标指标对比（评审官要求）:")
    print(f"{'指标':<20} {'目标':<15} {'实际':<15} {'状态':<10}")
    print("-"*60)

    # 收益率
    total_return = result.metrics.total_return
    status = "✓ PASS" if total_return > 0 else "✗ FAIL"
    print(f"{'总收益率':<20} {'> 0%':<15} {f'{total_return*100:+.2f}%':<15} {status}")

    # 最大回撤
    max_dd = result.metrics.max_drawdown
    status = "✓ PASS" if max_dd < 0.10 else "✗ FAIL"
    print(f"{'最大回撤':<20} {'< 10%':<15} {f'{abs(max_dd)*100:.2f}%':<15} {status}")

    # 夏普比率
    sharpe = result.metrics.sharpe_ratio
    status = "✓ PASS" if sharpe > 1.0 else "✗ FAIL"
    print(f"{'夏普比率':<20} {'> 1.0':<15} {f'{sharpe:.4f}':<15} {status}")

    # 胜率
    win_rate = result.metrics.win_rate
    status = "✓ PASS" if win_rate > 0.70 else "✗ FAIL"
    print(f"{'胜率':<20} {'> 70%':<15} {f'{win_rate*100:.2f}%':<15} {status}")

    # 盈亏比
    profit_factor = result.metrics.profit_factor
    status = "✓ PASS" if profit_factor > 1.0 else "✗ FAIL"
    print(f"{'盈亏比':<20} {'> 1.0':<15} {f'{profit_factor:.4f}':<15} {status}")

    # 9. 改进分析
    print("\n改进分析:")
    total_pnl = result.final_capital - result.initial_capital
    total_costs = result.metrics.total_commission

    print(f"  净收益: ${total_pnl:,.2f}")
    print(f"  手续费: ${total_costs:,.2f}")

    if total_pnl > 0:
        cost_ratio = total_costs / total_pnl * 100
        print(f"  成本占收益比例: {cost_ratio:.2f}%")

        if result.metrics.sharpe_ratio > 1.0:
            print(f"  ✓ 夏普比率达标！策略具有良好的风险调整收益")
        else:
            print(f"  ✗ 夏普比率未达标，需要进一步优化")

        if result.metrics.max_drawdown < 0.10:
            print(f"  ✓ 最大回撤控制良好")
        else:
            print(f"  ✗ 最大回撤过大，需要加强风险控制")
    else:
        print(f"  ✗ 策略仍然亏损，需要继续优化")

    # 统计市场状态
    print("\n交易统计:")
    print(f"  总交易次数: {result.metrics.total_trades}")
    print(f"  平均持仓时间: {result.metrics.avg_holding_time:.2f} 小时")

    # 分析各阶段表现
    print("\n交易分析:")
    buy_trades = [t for t in result.trades if t.side.value == 'buy']
    sell_trades = [t for t in result.trades if t.side.value == 'sell']
    print(f"  买入次数: {len(buy_trades)}")
    print(f"  卖出次数: {len(sell_trades)}")

    # 计算（简化）每笔交易的平均收益
    if buy_trades and sell_trades:
        avg_buy_price = sum(t.price for t in buy_trades) / len(buy_trades)
        avg_sell_price = sum(t.price for t in sell_trades) / len(sell_trades)
        print(f"  平均买入价格: ${avg_buy_price:.2f}")
        print(f"  平均卖出价格: ${avg_sell_price:.2f}")

    print("\n" + "="*70)
    print("回测完成！")
    print("="*70)

    # 返回结果以便进一步使用
    return result


if __name__ == "__main__":
    result = main()
