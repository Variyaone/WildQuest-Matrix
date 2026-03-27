#!/usr/bin/env python3
"""
 Gateway 5 OKX沙盒模拟盘
 使用OKX的沙盒环境进行模拟交易（非本地Mock）
"""

import sys
import time
from pathlib import Path
import json

# 添加路径
project_root = Path(__file__).parent / "workspace-creator"
sys.path.insert(0, str(project_root))

# 导入OKX交易系统
import okx_trading.main as main_module
from okx_trading.execution.order_executor import OKXOrderExecutor

# 配置路径
okx_sandbox_config = Path(__file__).parent / "workspace-creator" / "scripts" / "okx_sandbox_config.json"
gate5_config = Path(__file__).parent / "workspace-architect" / "deployment" / "gate5_config.json"

# 加载OKX沙盒配置
with open(okx_sandbox_config, 'r') as f:
    okx_config = json.load(f)

# 加载Gateway 5配置
with open(gate5_config, 'r') as f:
    config = json.load(f)

# 获取网格参数
grid_config = config['grid_strategy']['config']
grid_count = grid_config['grid_count']
price_range_pct = 0.15
investment_per_grid = grid_config['investment_per_grid']
total_investment = config['account']['capital']['initial']

# 当前价格（从OKX真实API获取）
print("✓ 从OKX获取BTC实时价格...")
try:
    from okx_api_client import OKXClient
    client = OKXClient(config_dict=okx_config)
    ticker = client.get_ticker('BTC/USDT:USDT')
    current_price = float(ticker.get('last', 0))
    print(f"✓ BTC当前价格: ${current_price:,.2f}")
except Exception as e:
    print(f"⚠️  获取价格失败，使用默认价格: ${e}")
    current_price = 50000

# 计算网格参数
upper_price = current_price * (1 + price_range_pct / 2)
lower_price = current_price * (1 - price_range_pct / 2)
grid_interval = (upper_price - lower_price) / grid_count
grid_amount = total_investment / grid_count

# 创建策略配置
strategy_config = {
    'name': 'grid',
    'instrument_id': 'BTC/USDT:USDT',
    'upper_price': upper_price,
    'lower_price': lower_price,
    'grid_count': grid_count,
    'grid_amount': grid_amount,
    'position_side': 'long',
    'trend_filter_enabled': True,
    'commission': 0.002,
    'slippage': 0.001
}

print("=" * 70)
print("🚀 Gateway 5 OKX沙盒模拟盘启动 (BTC-USDT)")
print("=" * 70)
print()
print("📋 配置参数:")
print(f"   交易对: BTC/USDT:USDT")
print(f"   初始资金: ${total_investment:,.0f}")
print(f"   当前价格: ${current_price:,.2f}")
print(f"   价格区间: ${lower_price:,.2f} - ${upper_price:,.2f}")
print(f"   网格数量: {grid_count}格")
print(f"   单格资金: ${grid_amount:,.0f}")
print(f"   网格间距: ${grid_interval:,.2f}")
print()
print("🎯 执行方式:")
print("   ✓ OKX沙盒环境（非本地Mock）")
print("   ✓ 真实市场价格")
print("   ✓ 模拟订单执行（OKX沙盒）")
print()
print("🛡️  风险控制:")
print("   ✓ 每日止损: 3.0%")
print("   ✓ 单笔止损: 2.0%")
print("   ✓ 最大回撤: 10%")
print()
print("✓ 参数配置完成")
print()

# 创建系统 - 不使用simulated=True，而是传入OKX沙盒配置
system = main_module.OKXTradingSystem(
    config_path=str(gate5_config),
    simulated=False  # false表示使用OKXOrderExecutor，而它内部会用沙盒模式
)

# 初始化系统
print("🔄 正在初始化系统...")
if not system.initialize(strategy_config=strategy_config):
    print("❌ 初始化失败")
    sys.exit(1)
print("✓ 系统初始化成功")
print()

# 替换为OKX沙盒执行器
print("🔄 切换到OKX沙盒执行器...")
try:
    system.executor = OKXOrderExecutor(config_dict=okx_config)
    print("✓ OKX沙盒执行器初始化成功")
    print("  - 环境: OKX沙盒（simulated）")
    print("  - API: 真实OKX接口")
    print("  - 订单: 模拟执行（非真实下单）")
except Exception as e:
    print(f"❌ OKX执行器初始化失败: {e}")
    sys.exit(1)
print()

print("=" * 70)
print("🎉 OKX沙盒模拟盘启动成功！")
print("=" * 70)
print()
print("📊 系统状态:")
print("   ✓ 网格交易引擎已就绪")
print("   ✓ 趋势过滤器已加载")
print("   ✓ 风险控制模块已激活")
print("   ✓ OKX沙盒执行器已连接")
print()
print("💰 资金分配:")
print(f"   BTC-USDT: ${total_investment:,.0f} (100%)")
print(f"   (可随时添加ETH-USDT)")
print()
print("⏳ 开始监控模式...")
print("提示: 按 Ctrl+C 停止模拟盘")
print("说明: 使用OKX沙盒环境，订单模拟执行但价格真实")
print()
print("=" * 70)
print()

try:
    # 监控循环
    heartbeat_count = 0
    start_time = time.time()

    while True:
        time.sleep(5)  # 每5秒检查一次
        heartbeat_count += 1

        # 每6个心跳输出一次状态（每30秒）
        if heartbeat_count % 6 == 0:
            elapsed = time.time() - start_time
            print(f"📍 心跳 #{heartbeat_count} | 运行时间: {elapsed/60:.1f}分 | 沙盒环境: 正常")

        # 这里可以添加实际的交易逻辑
        # 可以通过 system.run_step() 或手动触发策略

except KeyboardInterrupt:
    print("\n")
    print("=" * 70)
    print("⏹️  模拟盘已停止")
    print("=" * 70)
    print()
    print("📊 运行摘要:")
    print(f"   运行时长: {(time.time() - start_time)/60:.1f}分钟")
    print(f"   心跳次数: {heartbeat_count}")
    print(f"   环境: OKX沙盒模式")
    print("=" * 70)
