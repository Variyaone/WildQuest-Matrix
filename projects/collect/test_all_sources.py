"""测试所有数据源"""
import time

print("=" * 60)
print("测试所有数据源")
print("=" * 60)

# 测试 Ashare
print("\n1. Ashare (新浪+腾讯):")
try:
    from download_ashare import get_price
    df = get_price("600519", "2024-01-01")
    if df is not None and len(df) > 0:
        print(f"   ✓ 成功: {len(df)} 条记录")
    else:
        print("   ✗ 失败: 无数据")
except Exception as e:
    print(f"   ✗ 失败: {e}")

time.sleep(1)

# 测试 efinance
print("\n2. efinance (东方财富):")
try:
    import efinance as ef
    df = ef.stock.get_quote_history("600519", beg="20240101", end="20260327", klt=101, fqt=1)
    if df is not None and len(df) > 0:
        print(f"   ✓ 成功: {len(df)} 条记录")
    else:
        print("   ✗ 失败: 无数据")
except Exception as e:
    print(f"   ✗ 失败: {str(e)[:100]}")

time.sleep(1)

# 测试 AKShare
print("\n3. AKShare:")
try:
    import akshare as ak
    df = ak.stock_zh_a_hist(symbol="600519", period="daily", start_date="20240101", end_date="20260327", adjust="qfq")
    if df is not None and len(df) > 0:
        print(f"   ✓ 成功: {len(df)} 条记录")
    else:
        print("   ✗ 失败: 无数据")
except Exception as e:
    print(f"   ✗ 失败: {str(e)[:100]}")

time.sleep(1)

# 测试 yfinance (港股)
print("\n4. yfinance (港股测试 - 腾讯控股):")
try:
    import yfinance as yf
    ticker = yf.Ticker("0700.HK")
    df = ticker.history(start="2024-01-01")
    if df is not None and len(df) > 0:
        print(f"   ✓ 成功: {len(df)} 条记录")
    else:
        print("   ✗ 失败: 无数据")
except Exception as e:
    print(f"   ✗ 失败: {str(e)[:100]}")

print("\n" + "=" * 60)
print("测试完成")
