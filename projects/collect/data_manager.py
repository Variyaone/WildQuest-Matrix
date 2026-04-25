"""
A股数据管理器
功能:
1. 多数据源协调 - 统一收集指令，不同数据源互相配合/分工/替补
2. 断点续传 - 记录下载进度，支持中断后继续
3. 数据审查、清理、保存 - 统一的数据处理流程
4. 数据更新机制 - 增量更新
"""

import os
import json
import time
import hashlib
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DataSource(Enum):
    ASHARE = "ashare"
    EFINANCE = "efinance"
    AKSHARE = "akshare"
    YFINANCE = "yfinance"


class DataStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class StockInfo:
    code: str
    name: str
    market: str
    list_date: Optional[str] = None
    delist_date: Optional[str] = None


@dataclass
class DownloadProgress:
    code: str
    status: str
    source: str
    start_date: str
    end_date: str
    record_count: int
    last_update: str
    error_msg: str = ""
    checksum: str = ""


class DataValidator:
    """数据验证器"""
    
    @staticmethod
    def validate_ohlc(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """验证OHLC数据完整性"""
        errors = []
        
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"缺少列: {col}")
        
        if len(df) == 0:
            errors.append("数据为空")
            return False, errors
        
        if 'high' in df.columns and 'low' in df.columns:
            invalid_rows = df[df['high'] < df['low']]
            if len(invalid_rows) > 0:
                errors.append(f"存在 {len(invalid_rows)} 条最高价<最低价的异常数据")
        
        for col in ['open', 'high', 'low', 'close']:
            if col in df.columns:
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    errors.append(f"{col} 列有 {null_count} 个空值")
        
        for col in ['open', 'high', 'low', 'close']:
            if col in df.columns:
                neg_count = (df[col] <= 0).sum()
                if neg_count > 0:
                    errors.append(f"{col} 列有 {neg_count} 个非正值")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def check_missing_dates(df: pd.DataFrame, start_date: str, end_date: str) -> List[str]:
        """检查缺失的交易日"""
        if df is None or len(df) == 0:
            return []
        
        df = df.sort_index()
        existing_dates = set(df.index.strftime('%Y-%m-%d').tolist())
        
        all_dates = pd.date_range(start=start_date, end=end_date, freq='B')
        expected_dates = set(d.strftime('%Y-%m-%d') for d in all_dates)
        
        missing = expected_dates - existing_dates
        return sorted(list(missing))


class DataCleaner:
    """数据清理器"""
    
    @staticmethod
    def clean_ohlc(df: pd.DataFrame) -> pd.DataFrame:
        """清理OHLC数据"""
        if df is None or len(df) == 0:
            return df
        
        df = df.copy()
        
        df = df.drop_duplicates()
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        if all(col in df.columns for col in ['high', 'low']):
            mask = df['high'] < df['low']
            if mask.any():
                df.loc[mask, ['high', 'low']] = df.loc[mask, ['low', 'high']].values
        
        df = df.sort_index()
        
        return df
    
    @staticmethod
    def fill_missing_values(df: pd.DataFrame, method: str = 'ffill') -> pd.DataFrame:
        """填充缺失值"""
        if df is None or len(df) == 0:
            return df
        
        df = df.copy()
        
        if method == 'ffill':
            df = df.ffill()
        elif method == 'bfill':
            df = df.bfill()
        elif method == 'interpolate':
            df = df.interpolate(method='linear')
        
        return df


class DataSourceAdapter:
    """数据源适配器 - 统一不同数据源的接口"""
    
    def __init__(self):
        self.sources = {}
        self._init_sources()
    
    def _init_sources(self):
        """初始化数据源"""
        try:
            from download_ashare import get_price as ashare_get_price
            self.sources[DataSource.ASHARE] = {
                'get_price': ashare_get_price,
                'available': True,
                'priority': 1,
                'name': '新浪+腾讯'
            }
        except:
            self.sources[DataSource.ASHARE] = {'available': False, 'priority': 1}
        
        try:
            import efinance as ef
            self.sources[DataSource.EFINANCE] = {
                'get_price': lambda code, start, end=None: self._efinance_get_price(ef, code, start, end),
                'available': True,
                'priority': 2,
                'name': '东方财富'
            }
        except:
            self.sources[DataSource.EFINANCE] = {'available': False, 'priority': 2}
        
        try:
            import akshare as ak
            self.sources[DataSource.AKSHARE] = {
                'get_price': lambda code, start, end=None: self._akshare_get_price(ak, code, start, end),
                'available': True,
                'priority': 3,
                'name': 'AKShare'
            }
        except:
            self.sources[DataSource.AKSHARE] = {'available': False, 'priority': 3}
        
        try:
            import yfinance as yf
            self.sources[DataSource.YFINANCE] = {
                'get_price': lambda code, start, end=None: self._yfinance_get_price(yf, code, start, end),
                'available': True,
                'priority': 4,
                'name': '雅虎财经'
            }
        except:
            self.sources[DataSource.YFINANCE] = {'available': False, 'priority': 4}
    
    def _efinance_get_price(self, ef, code: str, start_date: str, end_date: str = None):
        """efinance数据获取"""
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        else:
            end_date = end_date.replace('-', '')
        
        try:
            df = ef.stock.get_quote_history(
                code,
                beg=start_date.replace('-', ''),
                end=end_date,
                klt=101,
                fqt=1
            )
            if df is None or len(df) == 0:
                return None
            
            df = df.rename(columns={
                '日期': 'date', '开盘': 'open', '收盘': 'close',
                '最高': 'high', '最低': 'low', '成交量': 'volume'
            })
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            df = df[['open', 'high', 'low', 'close', 'volume']].sort_index()
            return df
        except Exception as e:
            logger.error(f"efinance获取失败: {e}")
            return None
    
    def _akshare_get_price(self, ak, code: str, start_date: str, end_date: str = None):
        """akshare数据获取"""
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        else:
            end_date = end_date.replace('-', '')
        
        try:
            df = ak.stock_zh_a_hist(
                symbol=code,
                period='daily',
                start_date=start_date.replace('-', ''),
                end_date=end_date,
                adjust='qfq'
            )
            if df is None or len(df) == 0:
                return None
            
            df = df.rename(columns={
                '日期': 'date', '开盘': 'open', '收盘': 'close',
                '最高': 'high', '最低': 'low', '成交量': 'volume'
            })
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            df = df[['open', 'high', 'low', 'close', 'volume']].sort_index()
            return df
        except Exception as e:
            logger.error(f"akshare获取失败: {e}")
            return None
    
    def _yfinance_get_price(self, yf, code: str, start_date: str, end_date: str = None):
        """yfinance数据获取"""
        try:
            if code.startswith('6'):
                symbol = f"{code}.SS"
            else:
                symbol = f"{code}.SZ"
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            
            if df is None or len(df) == 0:
                return None
            
            df = df.rename(columns={
                'Open': 'open', 'High': 'high', 'Low': 'low',
                'Close': 'close', 'Volume': 'volume'
            })
            df = df[['open', 'high', 'low', 'close', 'volume']].sort_index()
            return df
        except Exception as e:
            logger.error(f"yfinance获取失败: {e}")
            return None
    
    def get_available_sources(self) -> List[DataSource]:
        """获取可用数据源列表(按优先级排序)"""
        available = [s for s, info in self.sources.items() if info.get('available', False)]
        return sorted(available, key=lambda x: self.sources[x]['priority'])
    
    def fetch_data(self, code: str, start_date: str, end_date: str = None,
                   preferred_source: DataSource = None) -> Tuple[Optional[pd.DataFrame], DataSource]:
        """
        从数据源获取数据，支持自动切换
        
        返回: (数据, 使用的数据源)
        """
        sources_to_try = self.get_available_sources()
        
        if preferred_source and preferred_source in sources_to_try:
            sources_to_try.remove(preferred_source)
            sources_to_try.insert(0, preferred_source)
        
        for source in sources_to_try:
            source_info = self.sources.get(source)
            if not source_info or not source_info.get('available'):
                continue
            
            try:
                logger.info(f"尝试从 {source_info['name']} 获取 {code}")
                df = source_info['get_price'](code, start_date, end_date)
                
                if df is not None and len(df) > 0:
                    logger.info(f"成功从 {source_info['name']} 获取 {code}: {len(df)} 条记录")
                    return df, source
            except Exception as e:
                logger.warning(f"{source_info['name']} 获取失败: {e}")
                continue
        
        logger.error(f"所有数据源都无法获取 {code}")
        return None, None


class StockDataManager:
    """股票数据管理器"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        self.stock_dir = os.path.join(data_dir, "stocks")
        self.progress_file = os.path.join(data_dir, "progress.json")
        self.stock_list_file = os.path.join(data_dir, "stock_list.json")
        self.metadata_file = os.path.join(data_dir, "metadata.json")
        
        os.makedirs(self.stock_dir, exist_ok=True)
        
        self.adapter = DataSourceAdapter()
        self.validator = DataValidator()
        self.cleaner = DataCleaner()
        
        self.progress: Dict[str, DownloadProgress] = {}
        self.stock_list: List[StockInfo] = []
        self.metadata: Dict = {}
        
        self._load_state()
    
    def _load_state(self):
        """加载状态"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.progress = {k: DownloadProgress(**v) for k, v in data.items()}
            except:
                self.progress = {}
        
        if os.path.exists(self.stock_list_file):
            try:
                with open(self.stock_list_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.stock_list = [StockInfo(**s) for s in data]
            except:
                self.stock_list = []
        
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            except:
                self.metadata = {}
    
    def _save_state(self):
        """保存状态"""
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump({k: asdict(v) for k, v in self.progress.items()}, f, ensure_ascii=False, indent=2)
        
        with open(self.stock_list_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(s) for s in self.stock_list], f, ensure_ascii=False, indent=2)
        
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
    
    def _get_file_path(self, code: str) -> str:
        """获取股票数据文件路径"""
        return os.path.join(self.stock_dir, f"{code}.csv")
    
    def _calculate_checksum(self, df: pd.DataFrame) -> str:
        """计算数据校验和"""
        return hashlib.md5(pd.util.hash_pandas_object(df).values).hexdigest()
    
    def load_existing_data(self, code: str) -> Optional[pd.DataFrame]:
        """加载已有数据"""
        file_path = self._get_file_path(code)
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                return df
            except:
                return None
        return None
    
    def get_data_status(self, code: str) -> Optional[DownloadProgress]:
        """获取数据状态"""
        return self.progress.get(code)
    
    def scan_existing_data(self) -> Dict[str, dict]:
        """扫描已有数据，返回状态报告"""
        report = {}
        
        for file_name in os.listdir(self.stock_dir):
            if not file_name.endswith('.csv'):
                continue
            
            code = file_name.replace('.csv', '')
            file_path = self._get_file_path(code)
            
            try:
                df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                
                is_valid, errors = self.validator.validate_ohlc(df)
                
                report[code] = {
                    'record_count': len(df),
                    'date_range': f"{df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}",
                    'is_valid': is_valid,
                    'errors': errors,
                    'file_size': os.path.getsize(file_path),
                    'last_modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                }
            except Exception as e:
                report[code] = {
                    'record_count': 0,
                    'is_valid': False,
                    'errors': [str(e)]
                }
        
        return report
    
    def download_stock(self, code: str, name: str = "", start_date: str = "2010-01-01",
                       end_date: str = None, force: bool = False) -> bool:
        """
        下载单只股票数据
        
        参数:
            code: 股票代码
            name: 股票名称
            start_date: 开始日期
            end_date: 结束日期
            force: 是否强制重新下载
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        existing_progress = self.progress.get(code)
        
        if not force and existing_progress:
            if existing_progress.status == DataStatus.COMPLETED.value:
                existing_df = self.load_existing_data(code)
                if existing_df is not None and len(existing_df) > 0:
                    last_date = existing_df.index[-1].strftime('%Y-%m-%d')
                    if last_date >= (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'):
                        logger.info(f"{code} 数据已是最新，跳过")
                        return True
                    start_date = (existing_df.index[-1] + timedelta(days=1)).strftime('%Y-%m-%d')
        
        progress = DownloadProgress(
            code=code,
            status=DataStatus.DOWNLOADING.value,
            source="",
            start_date=start_date,
            end_date=end_date,
            record_count=0,
            last_update=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        self.progress[code] = progress
        self._save_state()
        
        df, source = self.adapter.fetch_data(code, start_date, end_date)
        
        if df is None or len(df) == 0:
            progress.status = DataStatus.FAILED.value
            progress.error_msg = "无法获取数据"
            self._save_state()
            return False
        
        df = self.cleaner.clean_ohlc(df)
        
        is_valid, errors = self.validator.validate_ohlc(df)
        if not is_valid:
            logger.warning(f"{code} 数据验证发现问题: {errors}")
        
        existing_df = self.load_existing_data(code)
        if existing_df is not None and len(existing_df) > 0 and not force:
            df = pd.concat([existing_df, df])
            df = df[~df.index.duplicated(keep='last')]
            df = df.sort_index()
        
        file_path = self._get_file_path(code)
        df.to_csv(file_path, encoding='utf-8')
        
        progress.status = DataStatus.COMPLETED.value
        progress.source = source.value if source else ""
        progress.record_count = len(df)
        progress.checksum = self._calculate_checksum(df)
        progress.last_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self._save_state()
        
        logger.info(f"{code} {name} 下载完成: {len(df)} 条记录")
        return True
    
    def download_batch(self, stock_list: List[Dict], start_date: str = "2010-01-01",
                       max_workers: int = 1, delay: float = 0.5) -> Dict:
        """
        批量下载股票数据
        
        参数:
            stock_list: 股票列表 [{'code': '600519', 'name': '贵州茅台'}, ...]
            start_date: 开始日期
            max_workers: 并发数(暂不支持多线程)
            delay: 请求间隔(秒)
        """
        total = len(stock_list)
        success_count = 0
        fail_count = 0
        skip_count = 0
        failed_stocks = []
        
        logger.info(f"开始批量下载 {total} 只股票")
        
        for i, stock in enumerate(stock_list):
            code = stock['code']
            name = stock.get('name', '')
            
            logger.info(f"[{i+1}/{total}] 处理 {code} {name}")
            
            progress = self.progress.get(code)
            if progress and progress.status == DataStatus.COMPLETED.value:
                existing_df = self.load_existing_data(code)
                if existing_df is not None:
                    last_date = existing_df.index[-1].strftime('%Y-%m-%d')
                    today = datetime.now().strftime('%Y-%m-%d')
                    if last_date >= today or last_date >= (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'):
                        logger.info(f"  跳过(数据已是最新)")
                        skip_count += 1
                        continue
            
            success = self.download_stock(code, name, start_date)
            if success:
                success_count += 1
            else:
                fail_count += 1
                failed_stocks.append(code)
            
            time.sleep(delay)
        
        result = {
            'total': total,
            'success': success_count,
            'failed': fail_count,
            'skipped': skip_count,
            'failed_stocks': failed_stocks
        }
        
        logger.info(f"批量下载完成: 成功={success_count}, 失败={fail_count}, 跳过={skip_count}")
        return result
    
    def update_all(self, days: int = 30) -> Dict:
        """
        更新所有已有数据
        
        参数:
            days: 检查最近N天的数据
        """
        updated = []
        failed = []
        
        for code in os.listdir(self.stock_dir):
            if not code.endswith('.csv'):
                continue
            
            code = code.replace('.csv', '')
            
            existing_df = self.load_existing_data(code)
            if existing_df is None or len(existing_df) == 0:
                continue
            
            last_date = existing_df.index[-1]
            today = datetime.now()
            
            if (today - last_date.to_pydatetime()).days <= 1:
                continue
            
            start_date = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')
            
            logger.info(f"更新 {code}: 从 {start_date}")
            
            success = self.download_stock(code, "", start_date)
            if success:
                updated.append(code)
            else:
                failed.append(code)
        
        return {'updated': updated, 'failed': failed}
    
    def check_data_quality(self, code: str = None) -> Dict:
        """
        检查数据质量
        
        参数:
            code: 股票代码，为None时检查所有
        """
        if code:
            codes = [code]
        else:
            codes = [f.replace('.csv', '') for f in os.listdir(self.stock_dir) if f.endswith('.csv')]
        
        report = {
            'total': len(codes),
            'valid': 0,
            'invalid': 0,
            'issues': {}
        }
        
        for c in codes:
            df = self.load_existing_data(c)
            if df is None:
                report['invalid'] += 1
                report['issues'][c] = ['无法加载数据']
                continue
            
            is_valid, errors = self.validator.validate_ohlc(df)
            
            if is_valid:
                report['valid'] += 1
            else:
                report['invalid'] += 1
                report['issues'][c] = errors
        
        return report
    
    def fill_missing_data(self, code: str, start_date: str, end_date: str) -> bool:
        """
        补充缺失的数据
        
        参数:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
        """
        existing_df = self.load_existing_data(code)
        
        missing_dates = self.validator.check_missing_dates(existing_df, start_date, end_date)
        
        if not missing_dates:
            logger.info(f"{code} 无缺失数据")
            return True
        
        logger.info(f"{code} 缺失 {len(missing_dates)} 个交易日")
        
        df, source = self.adapter.fetch_data(code, start_date, end_date)
        
        if df is None:
            return False
        
        if existing_df is not None:
            df = pd.concat([existing_df, df])
            df = df[~df.index.duplicated(keep='last')]
            df = df.sort_index()
        
        file_path = self._get_file_path(code)
        df.to_csv(file_path, encoding='utf-8')
        
        return True
    
    def get_summary(self) -> Dict:
        """获取数据概览"""
        total_stocks = len([f for f in os.listdir(self.stock_dir) if f.endswith('.csv')])
        total_size = sum(os.path.getsize(os.path.join(self.stock_dir, f)) 
                        for f in os.listdir(self.stock_dir) if f.endswith('.csv'))
        
        completed = sum(1 for p in self.progress.values() if p.status == DataStatus.COMPLETED.value)
        failed = sum(1 for p in self.progress.values() if p.status == DataStatus.FAILED.value)
        
        return {
            'total_stocks': total_stocks,
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'completed': completed,
            'failed': failed,
            'data_dir': self.data_dir,
            'available_sources': [s.value for s in self.adapter.get_available_sources()]
        }


def main():
    """主函数"""
    print("=" * 60)
    print("A股数据管理器")
    print("=" * 60)
    
    manager = StockDataManager()
    
    print("\n当前状态:")
    summary = manager.get_summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")
    
    print("\n请选择操作:")
    print("1. 下载单只股票")
    print("2. 批量下载股票")
    print("3. 更新所有数据")
    print("4. 检查数据质量")
    print("5. 扫描已有数据")
    print("6. 补充缺失数据")
    
    choice = input("\n请输入选项: ").strip()
    
    if choice == '1':
        code = input("股票代码: ").strip()
        name = input("股票名称: ").strip()
        start = input("开始日期 (默认2010-01-01): ").strip() or "2010-01-01"
        manager.download_stock(code, name, start)
    
    elif choice == '2':
        print("\n输入股票列表 (格式: 代码,名称 每行一只，空行结束):")
        stocks = []
        while True:
            line = input().strip()
            if not line:
                break
            parts = line.split(',')
            stocks.append({'code': parts[0].strip(), 'name': parts[1].strip() if len(parts) > 1 else ''})
        
        if stocks:
            manager.download_batch(stocks)
    
    elif choice == '3':
        result = manager.update_all()
        print(f"更新完成: {len(result['updated'])} 只成功, {len(result['failed'])} 只失败")
    
    elif choice == '4':
        report = manager.check_data_quality()
        print(f"\n数据质量报告:")
        print(f"  总计: {report['total']}")
        print(f"  有效: {report['valid']}")
        print(f"  无效: {report['invalid']}")
        if report['issues']:
            print("\n问题详情:")
            for code, errors in list(report['issues'].items())[:10]:
                print(f"  {code}: {errors}")
    
    elif choice == '5':
        report = manager.scan_existing_data()
        print(f"\n已有数据扫描结果 ({len(report)} 只):")
        for code, info in list(report.items())[:10]:
            status = "✓" if info['is_valid'] else "✗"
            print(f"  {status} {code}: {info['record_count']} 条, {info['date_range']}")
    
    elif choice == '6':
        code = input("股票代码: ").strip()
        start = input("开始日期: ").strip()
        end = input("结束日期: ").strip()
        manager.fill_missing_data(code, start, end)


if __name__ == "__main__":
    main()
