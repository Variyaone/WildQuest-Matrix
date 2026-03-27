"""
Grid Trend Filter Strategy V3 回测脚本
"""

import sys
import os

# 添加父目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest_engine import (
    BacktestEngine,
    print_backtest_summary,
)

from grid_trend_filter_strategy_v3 import GridTrendFilterStrategyV3

import pandas as pd


def load_btc_data(filepath: str) -> pd.DataFrame:
    """加载BTC历史数据"""
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')
    return df


def main():
    """主函数"""
    print("="*70)
    print("Grid Trend Filter Strategy V3 - 回测")
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

    # 3. 创建GridTrendFilterStrategyV3策略
    print("\n创建策略: GridTrendFilterStrategyV3")
    strategy_params = {
        'ma_short_period': 20,
        'ma_long_period': 50,
        'grid_count': 4,
        'investment_per_grid': 10000,
        'price_range_pct': 0.15,  # ±7.5%
        'symbol': 'BTC-USDT',
        'stop_loss_pct': 0.02,  # 止损-2%
        'profit_target_pct': 0.03,  # 止盈3%
        'trend_threshold': 0.01,  # 趋势阈值1%
        'rsi_period': 14,
    }

    print(f"  策略参数:")
    print(f"    MA短期周期: {strategy_params['ma_short_period']}日")
    print(f"    MA长期周期: {strategy_params['ma_long_period']}日")
    print(f"    网格数量: {strategy_params['grid_count']}格")
    print(f"    单格金额: ${strategy_params['investment_per_grid']:,.0f}")
    print(f"    价格区间: ±{strategy_params['price_range_pct']*100:.1f}%")
    print(f"    止损: {strategy_params['stop_loss_pct']*100:.1f}%")
    print(f"    止盈: {strategy_params['profit_target_pct']*100:.1f}%")
    print(f"    趋势阈值: {strategy_params['trend_threshold']*100:.1f}%")

    strategy = GridTrendFilterStrategyV3(
        name="GridTrendFilterV3",
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
    report_path = "/Users/variya/.openclaw/workspace-architect/okx-trading/backtest/grid_trend_filter_v3_results.json"
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

    total_return = result.metrics.total_return
    max_dd = result.metrics.max_drawdown
    sharpe = result.metrics.sharpe_ratio
    win_rate = result.metrics.win_rate
    profit_factor = result.metrics.profit_factor

    print(f"{'总收益率':<20} {'> 0%':<15} {f'{total_return*100:+.2f}%':<15} {'✓ PASS' if total_return > 0 else '✗ FAIL'}")
    print(f"{'最大回撤':<20} {'< 10%':<15} {f'{abs(max_dd)*100:.2f}%':<15} {'✓ PASS' if max_dd < 0.10 else '✗ FAIL'}")
    print(f"{'夏普比率':<20} {'> 1.0':<15} {f'{sharpe:.4f}':<15} {'✓ PASS' if sharpe > 1.0 else '✗ FAIL'}")
    print(f"{'胜率':<20} {'> 70%':<15} {f'{win_rate*100:.2f}%':<15} {'✓ PASS' if win_rate > 0.70 else '✗ FAIL'}")
    print(f"{'盈亏比':<20} {'> 1.0':<15} {f'{profit_factor:.4f}':<15} {'✓ PASS' if profit_factor > 1.0 else '✗ FAIL'}")

    # 9. 总结
    print("\n" + "="*70)
    total_pnl = result.final_capital - result.initial_capital
    print(f"净收益: ${total_pnl:,.2f}")
    print(f"手续费: ${result.metrics.total_commission:,.2f}")
    print("="*70)

    return result


if __name__ == "__main__":
    result = main()
