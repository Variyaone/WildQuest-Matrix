#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OKX模拟盘连接测试脚本
"""

import os
import sys

# 添加脚本目录到路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# 导入配置
from simulation_funding_arbitrage import load_env_file, OKX_API_KEY, OKX_SECRET_KEY, OKX_PASSPHRASE

def main():
    print("=" * 60)
    print("OKX模拟盘 - 连接配置检查")
    print("=" * 60)

    # 1. 检查依赖
    print("\n[1/4] 检查Python依赖...")
    try:
        import ccxt
        print(f"  ✅ ccxt: {ccxt.__version__}")
    except ImportError:
        print("  ❌ ccxt: 未安装")
        print("  提示: 在okx-temp目录运行: source venv/bin/activate && pip install ccxt")
        return False

    try:
        import pandas
        print(f"  ✅ pandas: {pandas.__version__}")
    except ImportError:
        print("  ❌ pandas: 未安装")

    try:
        import numpy
        print(f"  ✅ numpy: {numpy.__version__}")
    except ImportError:
        print("  ❌ numpy: 未安装")

    # 2. 检查.env文件
    print("\n[2/4] 检查.env文件...")
    env_file = os.path.join(SCRIPT_DIR, '.env')
    if os.path.exists(env_file):
        print(f"  ✅ .env文件存在: {env_file}")
        try:
            env_vars = load_env_file(env_file)
            print(f"  ✅ 成功加载.env文件，找到 {len(env_vars)} 个变量")
        except Exception as e:
            print(f"  ❌ 读取.env文件失败: {e}")
            return False
    else:
        print(f"  ❌ .env文件不存在: {env_file}")

    # 3. 检查API密钥
    print("\n[3/4] 检查API密钥配置...")
    api_configured = True

    if OKX_API_KEY and OKX_API_KEY != 'your-api-key-here':
        print(f"  ✅ API Key: {OKX_API_KEY[:8]}...{OKX_API_KEY[-8:]}")
    else:
        print("  ❌ API Key: 未配置")
        api_configured = False

    if OKX_SECRET_KEY and OKX_SECRET_KEY != 'your-secret-key-here':
        print(f"  ✅ Secret Key: {OKX_SECRET_KEY[:8]}...{OKX_SECRET_KEY[-8:]}")
    else:
        print("  ❌ Secret Key: 未配置")
        api_configured = False

    if OKX_PASSPHRASE and OKX_PASSPHRASE != 'your-passphrase-here':
        print(f"  ✅ Passphrase: {OKX_PASSPHRASE[:8]}...{OKX_PASSPHRASE[-8:]}")
    else:
        print("  ❌ Passphrase: 未配置")
        api_configured = False

    if not api_configured:
        print("\n  ⚠️ API密钥未配置，请按以下步骤操作：")
        print("  1. 访问 https://www.okx.com/account/my-api")
        print("  2. 创建API密钥时选择 Demo Trading Environment")
        print("  3. 编辑 .env 文件，填入你的API密钥:")
        print("     OKX_SIMULATION_API_KEY=你的API_KEY")
        print("     OKX_SIMULATION_SECRET_KEY=你的SECRET_KEY")
        print("     OKX_SIMULATION_PASSPHRASE=你的PASSPHRASE")
        return False

    # 4. 测试OKX连接
    print("\n[4/4] 测试OKX Sim环境连接...")
    try:
        from simulation_funding_arbitrage import OKXSimulationTrader
        trader = OKXSimulationTrader(
            api_key=OKX_API_KEY,
            secret_key=OKX_SECRET_KEY,
            passphrase=OKX_PASSPHRASE,
            sandbox=True
        )

        if trader.test_connection():
            print("\n" + "=" * 60)
            print("✅ 所有检查通过！可以开始运行模拟盘测试")
            print("=" * 60)
            print("\n运行命令:")
            print("  cd okx-temp")
            print("  source venv/bin/activate")
            print("  python3 simulation_funding_arbitrage.py")
            return True
        else:
            print("\n❌ 连接OKX失败，请检查API密钥是否正确")
            return False

    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
