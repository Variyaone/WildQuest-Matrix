"""
efinance A股数据下载脚本
数据源: 东方财富
GitHub: https://github.com/Micro-sheep/efinance
"""

import os
import time
import pandas as pd
from datetime import datetime, timedelta

DATA_DIR = "./data/efinance"
os.makedirs(DATA_DIR, exist_ok=True)

EFINANCE_AVAILABLE = False

try:
    import efinance as ef
    EFINANCE_AVAILABLE = True
    print("efinance 库加载成功")
except ImportError:
    print("警告: efinance 未安装，请运行: pip install efinance")


def get_stock_list():
    """获取全部A股股票列表"""
    if not EFINANCE_AVAILABLE:
        return []
    
    print("正在获取A股股票列表...")
    try:
        df = ef.stock.get_base_info()
        stock_list = []
        for _, row in df.iterrows():
            stock_list.append({
                'code': row['股票代码'],
                'name': row['股票名称']
            })
        print(f"获取到 {len(stock_list)} 只股票")
        return stock_list
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return []


def get_price(code, start_date='2010-01-01', end_date=None, klt=101):
    """
    获取股票历史K线数据
    
    参数:
        code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        klt: K线类型 101=日线, 102=周线, 103=月线, 60=60分钟, 30=30分钟, 15=15分钟, 5=5分钟, 1=1分钟
    """
    if not EFINANCE_AVAILABLE:
        return None
    
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    try:
        df = ef.stock.get_quote_history(
            code,
            beg=start_date.replace('-', ''),
            end=end_date.replace('-', ''),
            klt=klt,
            fqt=1
        )
        
        if df is None or len(df) == 0:
            return None
        
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount',
            '振幅': 'amplitude',
            '涨跌幅': 'pct_change',
            '涨跌额': 'change',
            '换手率': 'turnover'
        })
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        df = df.sort_index()
        
        return df
    except Exception as e:
        print(f"获取 {code} 数据失败: {e}")
        return None


def download_single_stock(code, name, start_date='2010-01-01'):
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


def download_all_stocks(start_date='2010-01-01', max_stocks=None):
    """批量下载所有A股数据"""
    if not EFINANCE_AVAILABLE:
        print("efinance 未安装，无法下载")
        return
    
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
        time.sleep(0.3)
    
    print("\n" + "=" * 50)
    print(f"下载完成! 成功: {success_count}, 失败: {fail_count}")
    print(f"数据保存目录: {DATA_DIR}")


def download_index_data(start_date='2010-01-01'):
    """下载主要指数数据"""
    indices = [
        {'code': '000001', 'name': '上证指数'},
        {'code': '399001', 'name': '深证成指'},
        {'code': '399006', 'name': '创业板指'},
        {'code': '000016', 'name': '上证50'},
        {'code': '000300', 'name': '沪深300'},
        {'code': '000905', 'name': '中证500'},
        {'code': '000852', 'name': '中证1000'},
    ]
    
    print("正在下载指数数据...")
    for idx in indices:
        df = get_price(idx['code'], start_date)
        if df is not None and len(df) > 0:
            file_path = os.path.join(DATA_DIR, f"index_{idx['code']}.csv")
            df.to_csv(file_path, encoding='utf-8')
            print(f"  {idx['name']}: {len(df)} 条记录")
        time.sleep(0.3)


def download_minute_data(code, name, klt=5, start_date=None):
    """
    下载分钟K线数据
    
    参数:
        code: 股票代码
        name: 股票名称
        klt: K线类型 1=1分钟, 5=5分钟, 15=15分钟, 30=30分钟, 60=60分钟
    """
    if not EFINANCE_AVAILABLE:
        print("efinance 未安装")
        return
    
    print(f"正在下载 {code} {name} 分钟K线...")
    
    df = get_price(code, start_date=start_date, klt=klt)
    
    if df is not None and len(df) > 0:
        klt_name = {1: '1min', 5: '5min', 15: '15min', 30: '30min', 60: '60min'}.get(klt, f'{klt}min')
        file_path = os.path.join(DATA_DIR, f"{code}_{klt_name}.csv")
        df.to_csv(file_path, encoding='utf-8')
        print(f"  保存成功: {file_path} ({len(df)} 条记录)")
    else:
        print(f"  下载失败")


def get_realtime_quote(codes):
    """获取实时行情"""
    if not EFINANCE_AVAILABLE:
        return None
    
    try:
        df = ef.stock.get_realtime_quotes(codes)
        return df
    except Exception as e:
        print(f"获取实时行情失败: {e}")
        return None


if __name__ == "__main__":
    if not EFINANCE_AVAILABLE:
        print("\n请先安装 efinance: pip install efinance")
        exit(1)
    
    print("=" * 50)
    print("efinance A股数据下载工具")
    print("数据源: 东方财富")
    print("=" * 50)
    
    print("\n请选择下载模式:")
    print("1. 下载指数数据")
    print("2. 下载单只股票 (日线)")
    print("3. 下载单只股票 (分钟线)")
    print("4. 批量下载所有A股 (测试前10只)")
    print("5. 批量下载所有A股 (完整)")
    print("6. 获取实时行情")
    
    choice = input("\n请输入选项 (1-6): ").strip()
    
    start_date = '2010-01-01'
    
    if choice == '1':
        download_index_data(start_date)
    elif choice == '2':
        code = input("请输入股票代码 (如 600519): ").strip()
        name = input("请输入股票名称 (如 贵州茅台): ").strip()
        download_single_stock(code, name, start_date)
    elif choice == '3':
        code = input("请输入股票代码 (如 600519): ").strip()
        name = input("请输入股票名称 (如 贵州茅台): ").strip()
        print("\n分钟K线类型:")
        print("1=1分钟, 5=5分钟, 15=15分钟, 30=30分钟, 60=60分钟")
        klt = int(input("请选择 (默认5): ") or "5")
        download_minute_data(code, name, klt)
    elif choice == '4':
        download_all_stocks(start_date, max_stocks=10)
    elif choice == '5':
        confirm = input("确认下载全部A股数据? (y/n): ").strip().lower()
        if confirm == 'y':
            download_all_stocks(start_date)
    elif choice == '6':
        codes = input("请输入股票代码 (逗号分隔，如 600519,000001): ").strip()
        code_list = [c.strip() for c in codes.split(',')]
        df = get_realtime_quote(code_list)
        if df is not None:
            print(df)
    else:
        print("无效选项")
