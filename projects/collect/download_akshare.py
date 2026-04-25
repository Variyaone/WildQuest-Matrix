"""
AKShare A股数据下载脚本
数据源: 多个财经网站聚合
GitHub: https://github.com/akfamily/akshare
"""

import os
import time
import pandas as pd
from datetime import datetime, timedelta

DATA_DIR = "./data/akshare"
os.makedirs(DATA_DIR, exist_ok=True)

AKSHARE_AVAILABLE = False

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
    print("akshare 库加载成功")
except ImportError:
    print("警告: akshare 未安装，请运行: pip install akshare")


def get_stock_list():
    """获取全部A股股票列表"""
    if not AKSHARE_AVAILABLE:
        return []
    
    print("正在获取A股股票列表...")
    try:
        df = ak.stock_zh_a_spot_em()
        stock_list = []
        for _, row in df.iterrows():
            stock_list.append({
                'code': row['代码'],
                'name': row['名称']
            })
        print(f"获取到 {len(stock_list)} 只股票")
        return stock_list
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return []


def get_price(code, start_date='2010-01-01', end_date=None, adjust='qfq'):
    """
    获取股票历史K线数据
    
    参数:
        code: 股票代码 (不带市场前缀)
        start_date: 开始日期
        end_date: 结束日期
        adjust: 复权类型 qfq=前复权, hfq=后复权, 不填=不复权
    """
    if not AKSHARE_AVAILABLE:
        return None
    
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    else:
        end_date = end_date.replace('-', '')
    
    start_date_fmt = start_date.replace('-', '')
    
    try:
        df = ak.stock_zh_a_hist(
            symbol=code,
            period='daily',
            start_date=start_date_fmt,
            end_date=end_date,
            adjust=adjust
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


def get_price_weekly(code, start_date='2010-01-01', end_date=None):
    """获取周K线数据"""
    if not AKSHARE_AVAILABLE:
        return None
    
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    else:
        end_date = end_date.replace('-', '')
    
    start_date_fmt = start_date.replace('-', '')
    
    try:
        df = ak.stock_zh_a_hist(
            symbol=code,
            period='weekly',
            start_date=start_date_fmt,
            end_date=end_date,
            adjust='qfq'
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
        })
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        df = df.sort_index()
        
        return df
    except Exception as e:
        print(f"获取 {code} 周K数据失败: {e}")
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
    if not AKSHARE_AVAILABLE:
        print("akshare 未安装，无法下载")
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
        time.sleep(0.5)
    
    print("\n" + "=" * 50)
    print(f"下载完成! 成功: {success_count}, 失败: {fail_count}")
    print(f"数据保存目录: {DATA_DIR}")


def download_index_data(start_date='2010-01-01'):
    """下载主要指数数据"""
    indices = [
        {'code': 'sh000001', 'name': '上证指数'},
        {'code': 'sz399001', 'name': '深证成指'},
        {'code': 'sz399006', 'name': '创业板指'},
        {'code': 'sh000016', 'name': '上证50'},
        {'code': 'sh000300', 'name': '沪深300'},
        {'code': 'sh000905', 'name': '中证500'},
        {'code': 'sh000852', 'name': '中证1000'},
    ]
    
    print("正在下载指数数据...")
    for idx in indices:
        try:
            df = ak.stock_zh_index_daily(symbol=idx['code'])
            if df is not None and len(df) > 0:
                start_date_fmt = start_date.replace('-', '')
                df = df[df['date'] >= start_date_fmt]
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
                df = df.sort_index()
                
                code_num = idx['code'][2:]
                file_path = os.path.join(DATA_DIR, f"index_{code_num}.csv")
                df.to_csv(file_path, encoding='utf-8')
                print(f"  {idx['name']}: {len(df)} 条记录")
        except Exception as e:
            print(f"  {idx['name']} 下载失败: {e}")
        time.sleep(0.3)


def get_stock_info(code):
    """获取股票基本信息"""
    if not AKSHARE_AVAILABLE:
        return None
    
    try:
        df = ak.stock_individual_info_em(symbol=code)
        return df
    except Exception as e:
        print(f"获取股票信息失败: {e}")
        return None


def get_financial_report(code, report_type='balance'):
    """
    获取财务报表
    
    参数:
        code: 股票代码
        report_type: balance=资产负债表, income=利润表, cash=现金流量表
    """
    if not AKSHARE_AVAILABLE:
        return None
    
    try:
        if report_type == 'balance':
            df = ak.stock_balance_sheet_by_report_em(symbol=code)
        elif report_type == 'income':
            df = ak.stock_profit_sheet_by_report_em(symbol=code)
        elif report_type == 'cash':
            df = ak.stock_cash_flow_sheet_by_report_em(symbol=code)
        else:
            return None
        return df
    except Exception as e:
        print(f"获取财务报表失败: {e}")
        return None


def get_realtime_quote():
    """获取A股实时行情"""
    if not AKSHARE_AVAILABLE:
        return None
    
    try:
        df = ak.stock_zh_a_spot_em()
        return df
    except Exception as e:
        print(f"获取实时行情失败: {e}")
        return None


if __name__ == "__main__":
    if not AKSHARE_AVAILABLE:
        print("\n请先安装 akshare: pip install akshare")
        exit(1)
    
    print("=" * 50)
    print("AKShare A股数据下载工具")
    print("数据源: 多个财经网站聚合")
    print("=" * 50)
    
    print("\n请选择下载模式:")
    print("1. 下载指数数据")
    print("2. 下载单只股票 (日线)")
    print("3. 下载单只股票 (周线)")
    print("4. 批量下载所有A股 (测试前10只)")
    print("5. 批量下载所有A股 (完整)")
    print("6. 获取股票基本信息")
    print("7. 获取财务报表")
    print("8. 获取实时行情")
    
    choice = input("\n请输入选项 (1-8): ").strip()
    
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
        print(f"正在下载 {code} {name} 周K线...")
        df = get_price_weekly(code, start_date)
        if df is not None:
            file_path = os.path.join(DATA_DIR, f"{code}_weekly.csv")
            df.to_csv(file_path, encoding='utf-8')
            print(f"保存成功: {file_path} ({len(df)} 条记录)")
    elif choice == '4':
        download_all_stocks(start_date, max_stocks=10)
    elif choice == '5':
        confirm = input("确认下载全部A股数据? (y/n): ").strip().lower()
        if confirm == 'y':
            download_all_stocks(start_date)
    elif choice == '6':
        code = input("请输入股票代码 (如 600519): ").strip()
        df = get_stock_info(code)
        if df is not None:
            print(df)
    elif choice == '7':
        code = input("请输入股票代码 (如 600519): ").strip()
        print("\n报表类型:")
        print("1. 资产负债表")
        print("2. 利润表")
        print("3. 现金流量表")
        report_choice = input("请选择 (1-3): ").strip()
        report_map = {'1': 'balance', '2': 'income', '3': 'cash'}
        report_type = report_map.get(report_choice, 'balance')
        df = get_financial_report(code, report_type)
        if df is not None:
            print(df.head(10))
    elif choice == '8':
        df = get_realtime_quote()
        if df is not None:
            print(df.head(20))
    else:
        print("无效选项")
