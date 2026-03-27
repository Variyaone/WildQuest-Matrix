"""
A股数据下载测试脚本
测试三个数据源: Ashare(新浪+腾讯), efinance(东方财富), AKShare
"""

import os
import sys
import time
from datetime import datetime

TEST_STOCKS = [
    {'code': '600519', 'name': '贵州茅台'},
    {'code': '000001', 'name': '平安银行'},
    {'code': '000858', 'name': '五粮液'},
]

START_DATE = '2010-01-01'


def test_ashare():
    """测试Ashare数据源"""
    print("\n" + "=" * 60)
    print("测试 Ashare (新浪+腾讯)")
    print("=" * 60)
    
    try:
        from download_ashare import get_price, DATA_DIR
        
        for stock in TEST_STOCKS:
            print(f"\n获取 {stock['code']} {stock['name']}...")
            start_time = time.time()
            df = get_price(stock['code'], START_DATE)
            elapsed = time.time() - start_time
            
            if df is not None and len(df) > 0:
                print(f"  成功! 获取 {len(df)} 条记录, 耗时 {elapsed:.2f}秒")
                print(f"  日期范围: {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}")
                print(f"  最新数据: 开{df['open'].iloc[-1]:.2f} 高{df['high'].iloc[-1]:.2f} 低{df['low'].iloc[-1]:.2f} 收{df['close'].iloc[-1]:.2f}")
            else:
                print(f"  失败!")
            time.sleep(0.5)
        
        return True
    except Exception as e:
        print(f"Ashare 测试失败: {e}")
        return False


def test_efinance():
    """测试efinance数据源"""
    print("\n" + "=" * 60)
    print("测试 efinance (东方财富)")
    print("=" * 60)
    
    try:
        import efinance as ef
        
        for stock in TEST_STOCKS:
            print(f"\n获取 {stock['code']} {stock['name']}...")
            start_time = time.time()
            
            df = ef.stock.get_quote_history(
                stock['code'],
                beg=START_DATE.replace('-', ''),
                end=datetime.now().strftime('%Y%m%d'),
                klt=101,
                fqt=1
            )
            elapsed = time.time() - start_time
            
            if df is not None and len(df) > 0:
                print(f"  成功! 获取 {len(df)} 条记录, 耗时 {elapsed:.2f}秒")
                print(f"  日期范围: {df['日期'].iloc[0]} ~ {df['日期'].iloc[-1]}")
                print(f"  最新数据: 开{df['开盘'].iloc[-1]:.2f} 高{df['最高'].iloc[-1]:.2f} 低{df['最低'].iloc[-1]:.2f} 收{df['收盘'].iloc[-1]:.2f}")
            else:
                print(f"  失败!")
            time.sleep(0.5)
        
        return True
    except ImportError:
        print("efinance 未安装，请运行: pip install efinance")
        return False
    except Exception as e:
        print(f"efinance 测试失败: {e}")
        return False


def test_akshare():
    """测试AKShare数据源"""
    print("\n" + "=" * 60)
    print("测试 AKShare (多源聚合)")
    print("=" * 60)
    
    try:
        import akshare as ak
        
        for stock in TEST_STOCKS:
            print(f"\n获取 {stock['code']} {stock['name']}...")
            start_time = time.time()
            
            df = ak.stock_zh_a_hist(
                symbol=stock['code'],
                period='daily',
                start_date=START_DATE.replace('-', ''),
                end_date=datetime.now().strftime('%Y%m%d'),
                adjust='qfq'
            )
            elapsed = time.time() - start_time
            
            if df is not None and len(df) > 0:
                print(f"  成功! 获取 {len(df)} 条记录, 耗时 {elapsed:.2f}秒")
                print(f"  日期范围: {df['日期'].iloc[0]} ~ {df['日期'].iloc[-1]}")
                print(f"  最新数据: 开{df['开盘'].iloc[-1]:.2f} 高{df['最高'].iloc[-1]:.2f} 低{df['最低'].iloc[-1]:.2f} 收{df['收盘'].iloc[-1]:.2f}")
            else:
                print(f"  失败!")
            time.sleep(0.5)
        
        return True
    except ImportError:
        print("akshare 未安装，请运行: pip install akshare")
        return False
    except Exception as e:
        print(f"AKShare 测试失败: {e}")
        return False


def test_yfinance():
    """测试yfinance数据源 (主要用于美股)"""
    print("\n" + "=" * 60)
    print("测试 yfinance (雅虎财经 - 主要用于美股/港股)")
    print("=" * 60)
    
    try:
        import yfinance as yf
        
        test_stocks = [
            {'code': 'AAPL', 'name': '苹果'},
            {'code': '0700.HK', 'name': '腾讯控股'},
        ]
        
        for stock in test_stocks:
            print(f"\n获取 {stock['code']} {stock['name']}...")
            start_time = time.time()
            
            ticker = yf.Ticker(stock['code'])
            df = ticker.history(start=START_DATE)
            elapsed = time.time() - start_time
            
            if df is not None and len(df) > 0:
                print(f"  成功! 获取 {len(df)} 条记录, 耗时 {elapsed:.2f}秒")
                print(f"  日期范围: {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}")
                print(f"  最新数据: 开{df['Open'].iloc[-1]:.2f} 高{df['High'].iloc[-1]:.2f} 低{df['Low'].iloc[-1]:.2f} 收{df['Close'].iloc[-1]:.2f}")
            else:
                print(f"  失败!")
            time.sleep(0.5)
        
        return True
    except ImportError:
        print("yfinance 未安装，请运行: pip install yfinance")
        return False
    except Exception as e:
        print(f"yfinance 测试失败: {e}")
        return False


def main():
    print("=" * 60)
    print("A股数据接口测试工具")
    print(f"测试股票: {[s['name'] for s in TEST_STOCKS]}")
    print(f"起始日期: {START_DATE}")
    print("=" * 60)
    
    results = {}
    
    results['Ashare'] = test_ashare()
    results['efinance'] = test_efinance()
    results['AKShare'] = test_akshare()
    results['yfinance'] = test_yfinance()
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, success in results.items():
        status = "✓ 成功" if success else "✗ 失败"
        print(f"  {name}: {status}")
    
    print("\n推荐使用:")
    success_list = [k for k, v in results.items() if v]
    if success_list:
        print(f"  可用接口: {', '.join(success_list)}")
        if 'Ashare' in success_list:
            print("  A股首选: Ashare (新浪+腾讯双内核)")
        elif 'AKShare' in success_list:
            print("  A股首选: AKShare")
        elif 'efinance' in success_list:
            print("  A股首选: efinance")
    else:
        print("  所有接口均不可用，请检查网络或安装依赖")


if __name__ == "__main__":
    main()
