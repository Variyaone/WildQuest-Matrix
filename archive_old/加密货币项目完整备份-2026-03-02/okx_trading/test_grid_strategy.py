"""
网格交易策略测试脚本
演示如何使用GridStrategy
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strategy.grid import GridStrategy
import json


def load_config(config_path: str) -> dict:
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    """主测试函数"""
    print("🚀 网格交易策略测试\n")

    # 加载配置
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'grid_config.json')
    config = load_config(config_path)

    # 创建策略实例
    strategy = GridStrategy(config)

    # 启动策略
    strategy.start()

    print("\n📈 模拟价格波动...\n")

    # 模拟价格波动（价格先下跌触发买入，再上涨触发卖出）
    test_prices = [
        95000.0,  # 初始价格
        93500.0,  # 下跌，触发买入
        92000.0,  # 继续下跌，触发买入
        90500.0,  # 继续下跌，触发买入
        92000.0,  # 上涨，触发卖出
        93500.0,  # 继续上涨，触发卖出
        95000.0,  # 继续上涨
    ]

    for i, price in enumerate(test_prices, 1):
        print(f"📍 第{i}次价格更新: {price:.2f} USDT")

        # 计算信号
        signal = strategy.calculate_signal(price)

        if signal:
            print(f"   🎯 信号: {signal.action} {signal.quantity:.6f} @ {signal.price:.2f}")
            print(f"   💡 原因: {signal.reason}")

            # 模拟订单成交
            if signal.action == 'BUY':
                order = {
                    'id': f"order_{i}",
                    'symbol': signal.symbol,
                    'side': 'BUY',
                    'quantity': signal.quantity,
                    'price': signal.price,
                    'timestamp': None
                }
            else:  # SELL
                order = {
                    'id': f"order_{i}",
                    'symbol': signal.symbol,
                    'side': 'SELL',
                    'quantity': signal.quantity,
                    'price': signal.price,
                    'timestamp': None
                }

            strategy.on_order_filled(order)
        else:
            print(f"   无交易信号")

    # 显示最终状态
    print("\n" + "="*60)
    print("📊 策略运行结果")
    print("="*60)

    # 输出持仓信息
    position_info = strategy.get_position_info()
    print(f"\n持仓信息:")
    print(f"  交易对: {position_info['symbol']}")
    print(f"  持仓数量: {position_info['quantity']:.6f}")
    print(f"  平均价格: {position_info['avg_price']:.2f}")
    print(f"  总成本: {position_info['total_cost']:.2f}")
    print(f"  已实现盈亏: {position_info['realized_pnl']:.2f}")

    # 输出网格状态
    grid_status = strategy.get_grid_status()
    print(f"\n网格状态:")
    print(f"  当前价格: {grid_status['current_price']:.2f}")
    print(f"  价格区间: [{grid_status['lower_price']:.2f}, {grid_status['upper_price']:.2f}]")
    print(f"  已买入网格: {grid_status['bought_grids']}")
    print(f"  待卖出网格: {grid_status['sell_pending_grids']}")

    # 输出交易历史
    trade_history = strategy.get_trade_history()
    print(f"\n交易历史 (共{len(trade_history)}笔):")
    for i, trade in enumerate(trade_history, 1):
        print(f"  {i}. {trade['side']} {trade['quantity']:.6f} @ {trade['price']:.2f}")

    print("="*60 + "\n")

    # 停止策略
    strategy.stop()


if __name__ == '__main__':
    main()
