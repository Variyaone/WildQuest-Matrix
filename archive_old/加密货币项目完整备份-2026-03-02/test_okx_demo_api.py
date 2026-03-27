#!/usr/bin/env python3
"""
 直接使用requests测试OKX模拟盘API
 """
import requests
import hmac
import base64
import hashlib
import time
import json

# OKX模拟盘配置
api_key = 'd97acda8-2983-4295-95a4-09424b0f780b'
secret = '116FC7791BEEF0DD0229CCB995752D8F'
passphrase = 'S2yCfpg!NjyLwHs'
base_url = 'https://www.okx.com'

def sign(timestamp, method, request_path, body=''):
    message = timestamp + method + request_path + body
    mac = hmac.new(bytes(secret, 'utf-8'), bytes(message, 'utf-8'), digestmod=hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()

print("=" * 60)
print("OKX模拟盘API测试 (requests)")
print("=" * 60)
print()

# 1. 测试无需认证的市场数据（应该无需headers就能成功）
print("1. 测试市场数据（无需认证）")
try:
    # 不需要headers的公共端点
    resp = requests.get(f"{base_url}/api/v5/market/ticker?instId=BTC-USDT-USDT", timeout=10)
    result = resp.json()
    if result['code'] == '0':
        price = result['data'][0]['last']
        print(f"   ✅ 成功！")
        print(f"   BTC/USDT永续价格: ${float(price):,.2f}")
    else:
        print(f"   ❌ API错误: {result['msg']}")
except Exception as e:
    print(f"   ❌ {e}")

print()

# 2. 测试需要认证的接口（添加 x-simulated-trading header）
print("2. 测试账户余额（需要认证 + 模拟盘header）")
timestamp = str(int(time.time()))
method = 'GET'
request_path = '/api/v5/account/balance'
signature = sign(timestamp, method, request_path, '')

headers = {
    'OK-ACCESS-KEY': api_key,
    'OK-ACCESS-SIGN': signature,
    'OK-ACCESS-TIMESTAMP': timestamp,
    'OK-ACCESS-PASSPHRASE': passphrase,
    'Content-Type': 'application/json',
    'x-simulated-trading': '1'  # ← 模拟盘关键header
}

try:
    resp = requests.get(
        f"{base_url}{request_path}",
        headers=headers,
        params={'instType': 'SWAP'},
        timeout=10
    )
    result = resp.json()
    if result['code'] == '0':
        print(f"   ✅ 成功！")
        if result['data']:
            details = result['data'][0].get('details', [])
            print(f"   模拟盘账户信息:")
            for d in details:
                if float(d['availBal']) > 0:
                    print(f"     {d['ccy']}: {d['availBal']}")
    else:
        print(f"   ❌ API错误: {result['msg']} (code: {result['code']})")
except Exception as e:
    print(f"   ❌ {e}")

print()
print("3. 测试持仓查询")
timestamp = str(int(time.time()))
request_path = '/api/v5/account/positions'
signature = sign(timestamp, 'GET', request_path, '') 

headers = {
    'OK-ACCESS-KEY': api_key,
    'OK-ACCESS-SIGN': signature,
    'OK-ACCESS-TIMESTAMP': timestamp,
    'OK-ACCESS-PASSPHRASE': passphrase,
    'Content-Type': 'application/json',
    'x-simulated-trading': '1'
}

try:
    resp = requests.get(
        f"{base_url}{request_path}",
        headers=headers,
        params={'instType': 'SWAP', 'instId': 'BTC-USDT-USDT'},
        timeout=10
    )
    result = resp.json()
    if result['code'] == '0':
        print(f"   ✅ 成功！")
        if result['data']:
            print(f"   持仓数量: {len(result['data'])}")
        else:
            print(f"   暂无持仓")
    else:
        print(f"   ❌ {result['msg']}")
except Exception as e:
    print(f"   ❌ {e}")

print()
print("=" * 60)
