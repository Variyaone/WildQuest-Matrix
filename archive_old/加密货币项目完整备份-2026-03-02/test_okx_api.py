#!/usr/bin/env python3
"""测试OKX API返回格式"""

import json
import sys
from pathlib import Path

# 添加路径
proj_root = Path(__file__).parent / "workspace-creator"
sys.path.insert(0, str(proj_root))

# OKX API配置
api_config = {
    "api_key": "d97acda8-2983-4295-95a4-09424b0f780b",
    "secret": "116FC7791BEEF0DD0229CCB995752D8F",
    "passphrase": "S2yCfpg!NjyLwHs",
    "base_url": "https://www.okx.com",
    "simulated": True
}

print("测试OKX API返回格式...")
print()

from okx_api_client import OKXClient

client = OKXClient(config_dict=api_config)

try:
    print("调用 fetch_ticker('BTC/USDT:USDT')...")
    ticker = client.exchange.fetch_ticker('BTC/USDT:USDT')

    print(f"✓ 成功！返回类型: {type(ticker)}")
    print()

    if isinstance(ticker, dict):
        print("Top keys数量:", len(ticker))
        print("前20个keys:")
        for i, key in enumerate(list(ticker.keys())[:20]):
            val = ticker[key]
            if isinstance(val, dict):
                print(f"  {i}. {key}: <dict>")
            elif isinstance(val, list):
                print(f"  {i}. {key}: <list len={len(val)}>")
            else:
                print(f"  {i}. {key}: {type(val).__name__} = {str(val)[:40]}")

        print()
        print("重要字段:")
        for key in ['symbol', 'last', 'high', 'low', 'bid', 'ask', 'volume', 'timestamp']:
            if key in ticker:
                print(f"  {key}: {ticker[key]}")

    else:
        print(f"返回内容(type={type(ticker)}): {ticker}")

except Exception as e:
    print(f"❌ 失败: {e}")
    import traceback
    traceback.print_exc()
