"""
Grid Trend Filter Strategy V2 回测脚本
"""

import sys
import os

# 添加父目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest_engine import (
    BacktestEngine,
    print_backtest_summary,
)

from grid_trend_filter_strategy_v2 import GridTrendFilterStrategyV2

import pandas as pd
from datetime import datetime


def load_btc_data(filepath: str) -> pd.DataFrame:
    """加载BTC历史数据"""
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')
    return df


def main():
    """主函数"""
    print("="*70)
    print("Grid Trend Filter Strategy V2 - 回测")
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
    print(f"  起始价格: ${start_price:.2f}")
    print(f"  结束价格: ${end_price:.2f}")

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

    # 3. 创建GridTrendFilterStrategyV2策略
    print("\n创建策略: GridTrendFilterStrategyV2")
    strategy_params = {
        'ma_short_period': 20,
        'ma_long_period': 50,
        'grid_count': 6,
        'investment_per_grid': 8000,
        'price_range_pct': 0.20,  # ±10%
        'symbol': 'BTC-USDT',
        'hard_stop_loss_pct': 0.03,  # 硬止损-3%
        'trend_stop_threshold': 0.005,  # 趋势转向阈值0.5%
        'profit_target_pct': 0.02,  # 止盈2%
        'cooldown_bars': 24,  # 冷却24小时
    }

    print(f"  策略参数:")
    print(f"    MA短期周期: {strategy_params['ma_short_period']}日")
    print(f"    MA长期周期: {strategy_params['ma_long_period']}日")
    print(f"    网格数量: {strategy_params['grid_count']}格")
    print(f"    单格金额: ${strategy_params['investment_per_grid']:,.0f}")
    print(f"    价格区间: ±{strategy_params['price_range_pct']*100:.1f}%")
    print(f"    趋势转向阈值: {strategy_params['trend_stop_threshold']*100:.1f}%")
    print(f"    止盈目标: {strategy_params['profit_target_pct']*100:.1f}%")
    print(f"    冷却时间: {strategy_params['cooldown_bars']}小时")

    strategy = GridTrendFilterStrategyV2(
        name="GridTrendFilterV2",
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
    report_path = "/Users/variya/.openclaw/workspace-architect/okx-trading/backtest/grid_trend_filter_v2_results.json"
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

    # 9. 改进分析
    print("\n改进分析:")
    total_pnl = result.final_capital - result.initial_capital
    total_costs = result.metrics.total_commission

    print(f"  净收益: ${total_pnl:,.2f}")
    print(f"  手续费: ${total_costs:,.2f}")

    if total_pnl > 0:
        cost_ratio = total_costs / total_pnl * 100
        print(f"  成本占收益比例: {cost_ratio:.2f}%")

        if sharpe > 1.0:
            print(f"  ✓ 夏普比率达标！策略具有良好的风险调整收益")
        else:
            print(f"  ✗ 夏普比率未达标，需要进一步优化")

        if abs(max_dd) < 0.10:
            print(f"  ✓ 最大回撤控制良好")
        else:
            print(f"  ✗ 最大回撤过大，需要加强风险控制")
    else:
        print(f"  ✗ 策略仍然亏损，需要继续优化")

    print("\n" + "="*70)
    print("回测完成！")
    print("="*70)

    return result


if __name__ == "__main__":
    result = main()
