"""
Ashare A股数据下载脚本
数据源: 新浪财经 + 腾讯股票 (双内核自动切换)
GitHub: https://github.com/mpquant/Ashare
"""

import os
import time
import pandas as pd
from datetime import datetime, timedelta
import requests
from io import StringIO

DATA_DIR = "./data/ashare"
os.makedirs(DATA_DIR, exist_ok=True)


def get_price_sina(code, start_date='2008-01-01', end_date=None):
    """从新浪获取历史K线数据"""
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    code_map = {
        'sh': 'sh',
        'sz': 'sz',
        'bj': 'bj'
    }
    
    market = 'sh' if code.startswith('6') else 'sz'
    if code.startswith('8') or code.startswith('4'):
        market = 'bj'
    
    full_code = f"{market}{code}"
    
    url = f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
    params = {
        'symbol': full_code,
        'scale': '240',
        'ma': 'no',
        'datalen': '5000'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if not data or isinstance(data, dict):
            return None
        
        df = pd.DataFrame(data)
        df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        df['date'] = pd.to_datetime(df['date'])
        df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
        df = df.set_index('date')
        df = df.sort_index()
        
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        
        return df
    except Exception as e:
        print(f"新浪接口获取 {code} 失败: {e}")
        return None


def get_price_tencent(code, start_date='2008-01-01', end_date=None):
    """从腾讯获取历史K线数据"""
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    market = 'sh' if code.startswith('6') else 'sz'
    if code.startswith('8') or code.startswith('4'):
        market = 'bj'
    
    full_code = f"{market}{code}"
    
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    params = {
        '_var': f'kline_{full_code}day',
        'param': f'{full_code},day,,,5000,qfq',
        'r': str(int(time.time() * 1000))
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        text = response.text
        json_str = text.split('=')[1] if '=' in text else text
        data = eval(json_str)
        
        kline_data = data['data'][full_code]['day']
        
        df = pd.DataFrame(kline_data, columns=['date', 'open', 'close', 'high', 'low', 'volume'])
        df['date'] = pd.to_datetime(df['date'])
        df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
        df = df.set_index('date')
        df = df.sort_index()
        
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        
        return df
    except Exception as e:
        print(f"腾讯接口获取 {code} 失败: {e}")
        return None


def get_price(code, start_date='2008-01-01', end_date=None):
    """获取股票历史数据，自动切换数据源"""
    df = get_price_sina(code, start_date, end_date)
    if df is None or len(df) == 0:
        print(f"新浪失败，尝试腾讯接口...")
        df = get_price_tencent(code, start_date, end_date)
    return df


def get_stock_list():
    """获取A股股票列表"""
    print("正在获取A股股票列表...")
    
    stock_list = []
    
    try:
        url = "http://api.mairui.club/hslt/list/6000001d09"
        response = requests.get(url, timeout=10)
        data = response.json()
        for item in data:
            stock_list.append({
                'code': item['dm'],
                'name': item['mc'],
                'market': 'sh' if item['dm'].startswith('6') else 'sz'
            })
    except:
        pass
    
    if not stock_list:
        print("尝试备用接口获取股票列表...")
        try:
            url = "http://82.156.73.247/api/stock/list"
            response = requests.get(url, timeout=10)
            data = response.json()
            for item in data.get('data', []):
                stock_list.append({
                    'code': item['code'],
                    'name': item['name'],
                    'market': item.get('market', 'sh')
                })
        except Exception as e:
            print(f"获取股票列表失败: {e}")
    
    return stock_list


def download_single_stock(code, name, start_date='2008-01-01'):
    """下载单只股票数据"""
    print(f"正在下载: {code} {name}")
    
    df = get_price(code, start_date)
    
    if df is not None and len(df) > 0:
        file_path = os.path.join(DATA_DIR, f"{code}.csv")
        df.to_csv(file_path, encoding='utf-8')
        print(f"  保存成功: {file_path} ({len(df)} 条记录)")
        return True
    else:
        print(f"  下载失败: {code}")
        return False


def download_all_stocks(start_date='2008-01-01', max_stocks=None):
    """批量下载所有A股数据"""
    stock_list = get_stock_list()
    
    if not stock_list:
        print("无法获取股票列表，使用默认列表...")
        stock_list = [
            {'code': '000001', 'name': '平安银行'},
            {'code': '000002', 'name': '万科A'},
            {'code': '600000', 'name': '浦发银行'},
            {'code': '600036', 'name': '招商银行'},
            {'code': '600519', 'name': '贵州茅台'},
        ]
    
    if max_stocks:
        stock_list = stock_list[:max_stocks]
    
    print(f"\n共需下载 {len(stock_list)} 只股票")
    print("=" * 50)
    
    success_count = 0
    fail_count = 0
    
    for i, stock in enumerate(stock_list):
        print(f"\n[{i+1}/{len(stock_list)}]", end=" ")
        if download_single_stock(stock['code'], stock['name'], start_date):
            success_count += 1
        else:
            fail_count += 1
        time.sleep(0.5)
    
    print("\n" + "=" * 50)
    print(f"下载完成! 成功: {success_count}, 失败: {fail_count}")
    print(f"数据保存目录: {DATA_DIR}")


def download_index_data(start_date='2008-01-01'):
    """下载主要指数数据"""
    indices = [
        {'code': '000001', 'name': '上证指数', 'market': 'sh'},
        {'code': '399001', 'name': '深证成指', 'market': 'sz'},
        {'code': '399006', 'name': '创业板指', 'market': 'sz'},
        {'code': '000016', 'name': '上证50', 'market': 'sh'},
        {'code': '000300', 'name': '沪深300', 'market': 'sh'},
        {'code': '000905', 'name': '中证500', 'market': 'sh'},
    ]
    
    print("正在下载指数数据...")
    for idx in indices:
        df = get_price(idx['code'], start_date)
        if df is not None and len(df) > 0:
            file_path = os.path.join(DATA_DIR, f"index_{idx['code']}.csv")
            df.to_csv(file_path, encoding='utf-8')
            print(f"  {idx['name']}: {len(df)} 条记录")
        time.sleep(0.3)


if __name__ == "__main__":
    print("=" * 50)
    print("Ashare A股数据下载工具")
    print("数据源: 新浪财经 + 腾讯股票")
    print("=" * 50)
    
    print("\n请选择下载模式:")
    print("1. 下载指数数据")
    print("2. 下载单只股票")
    print("3. 批量下载所有A股 (测试前10只)")
    print("4. 批量下载所有A股 (完整)")
    
    choice = input("\n请输入选项 (1-4): ").strip()
    
    start_date = '2010-01-01'
    
    if choice == '1':
        download_index_data(start_date)
    elif choice == '2':
        code = input("请输入股票代码 (如 600519): ").strip()
        name = input("请输入股票名称 (如 贵州茅台): ").strip()
        download_single_stock(code, name, start_date)
    elif choice == '3':
        download_all_stocks(start_date, max_stocks=10)
    elif choice == '4':
        confirm = input("确认下载全部A股数据? (y/n): ").strip().lower()
        if confirm == 'y':
            download_all_stocks(start_date)
    else:
        print("无效选项")
