"""
数据更新器

每日收盘后增量更新数据，检测数据缺口，更新元数据索引。
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field

import pandas as pd

from ..infrastructure.logging import get_logger
from ..infrastructure.exceptions import DataException, DataFetchException
from ..data.storage import get_data_storage, DataStorage
from ..data.fetcher import get_data_fetcher, MultiSourceFetcher as DataFetcher
from ..data.metadata import MetadataManager


@dataclass
class UpdateResult:
    """数据更新结果"""
    success: bool
    stocks_updated: int = 0
    stocks_failed: int = 0
    total_rows_added: int = 0
    missing_dates: List[str] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "stocks_updated": self.stocks_updated,
            "stocks_failed": self.stocks_failed,
            "total_rows_added": self.total_rows_added,
            "missing_dates": self.missing_dates,
            "error_messages": self.error_messages,
            "duration_seconds": self.duration_seconds,
            "details": self.details
        }


@dataclass
class StockUpdateInfo:
    """股票更新信息"""
    stock_code: str
    last_date: Optional[str]
    missing_dates: List[str]
    rows_added: int = 0
    success: bool = False
    error_message: Optional[str] = None


class DailyDataUpdater:
    """
    数据更新器
    
    每日收盘后增量更新数据：
    1. 获取交易日历
    2. 检测缺失日期
    3. 增量下载数据
    4. 数据清洗
    5. 更新主数据
    6. 更新元数据
    """
    
    def __init__(
        self,
        storage: Optional[DataStorage] = None,
        fetcher: Optional[DataFetcher] = None,
        metadata_manager: Optional[MetadataManager] = None,
        lookback_days: int = 365,
        logger_name: str = "daily.data_updater"
    ):
        """
        初始化数据更新器
        
        Args:
            storage: 数据存储实例
            fetcher: 数据获取器实例
            metadata_manager: 元数据管理器实例
            lookback_days: 回溯天数
            logger_name: 日志名称
        """
        self.storage = storage or get_data_storage()
        self.fetcher = fetcher or get_data_fetcher()
        self.metadata_manager = metadata_manager or MetadataManager()
        self.lookback_days = lookback_days
        self.logger = get_logger(logger_name)
    
    def update(
        self,
        stock_codes: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        force_full: bool = False
    ) -> UpdateResult:
        """
        执行数据更新
        
        Args:
            stock_codes: 要更新的股票代码列表（None则更新全部）
            start_date: 开始日期（None则自动检测）
            end_date: 结束日期（None则使用今天）
            force_full: 是否强制全量更新
            
        Returns:
            UpdateResult: 更新结果
        """
        import time
        start_time = time.time()
        
        self.logger.info("开始数据更新")
        
        end_date = end_date or datetime.now().strftime('%Y-%m-%d')
        
        if stock_codes is None:
            stock_codes = self._get_stock_list()
        
        if not stock_codes:
            self.logger.warning("没有需要更新的股票")
            return UpdateResult(
                success=True,
                details={"message": "没有需要更新的股票"}
            )
        
        results: List[StockUpdateInfo] = []
        total_rows = 0
        
        for stock_code in stock_codes:
            info = self._update_single_stock(
                stock_code,
                start_date,
                end_date,
                force_full
            )
            results.append(info)
            total_rows += info.rows_added
        
        duration = time.time() - start_time
        
        success_count = sum(1 for r in results if r.success)
        failed_count = len(results) - success_count
        all_missing = []
        for r in results:
            all_missing.extend(r.missing_dates)
        
        success = failed_count == 0
        
        self.logger.info(
            f"数据更新完成: 成功={success_count}, 失败={failed_count}, "
            f"新增行数={total_rows}, 耗时={duration:.2f}秒"
        )
        
        return UpdateResult(
            success=success,
            stocks_updated=success_count,
            stocks_failed=failed_count,
            total_rows_added=total_rows,
            missing_dates=list(set(all_missing)),
            error_messages=[r.error_message for r in results if r.error_message],
            duration_seconds=duration,
            details={
                "stocks": {r.stock_code: {
                    "success": r.success,
                    "rows_added": r.rows_added,
                    "missing_dates": r.missing_dates
                } for r in results}
            }
        )
    
    def _update_single_stock(
        self,
        stock_code: str,
        start_date: Optional[str],
        end_date: str,
        force_full: bool
    ) -> StockUpdateInfo:
        """
        更新单只股票数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            force_full: 是否强制全量更新
            
        Returns:
            StockUpdateInfo: 更新信息
        """
        info = StockUpdateInfo(
            stock_code=stock_code,
            last_date=None,
            missing_dates=[]
        )
        
        try:
            existing_data = self.storage.stock_storage.load_stock_data(stock_code)
            
            if existing_data is not None and len(existing_data) > 0 and not force_full:
                existing_data['date'] = pd.to_datetime(existing_data['date'])
                info.last_date = existing_data['date'].max().strftime('%Y-%m-%d')
                
                if start_date is None:
                    next_day = existing_data['date'].max() + timedelta(days=1)
                    start_date = next_day.strftime('%Y-%m-%d')
            else:
                if start_date is None:
                    start_date = (datetime.now() - timedelta(days=self.lookback_days)).strftime('%Y-%m-%d')
            
            if start_date > end_date:
                self.logger.info(f"股票 {stock_code} 数据已是最新")
                info.success = True
                return info
            
            info.missing_dates = self._get_missing_dates(info.last_date, end_date)
            
            if not info.missing_dates:
                info.success = True
                return info
            
            self.logger.info(
                f"更新股票 {stock_code}: {start_date} 到 {end_date}, "
                f"缺失日期数: {len(info.missing_dates)}"
            )
            
            result = self.fetcher.fetch_daily_data(stock_code, start_date, end_date)
            
            if not result.success:
                raise DataFetchException(
                    f"获取数据失败: {result.error_message}",
                    source=result.source
                )
            
            new_data = result.data
            
            if existing_data is not None and len(existing_data) > 0:
                existing_data['date'] = existing_data['date'].dt.strftime('%Y-%m-%d')
                combined = pd.concat([existing_data, new_data], ignore_index=True)
                combined = combined.drop_duplicates(subset=['date'], keep='last')
                combined = combined.sort_values('date')
            else:
                combined = new_data
            
            save_result = self.storage.stock_storage.save_stock_data(combined, stock_code)
            
            if not save_result.success:
                raise DataException(f"保存数据失败: {save_result.error_message}")
            
            info.rows_added = len(new_data)
            info.success = True
            
            self._update_metadata(stock_code, combined)
            
            self.logger.info(f"股票 {stock_code} 更新成功，新增 {info.rows_added} 行")
            
        except Exception as e:
            info.error_message = str(e)
            self.logger.error(f"更新股票 {stock_code} 失败: {e}")
        
        return info
    
    def _get_stock_list(self) -> List[str]:
        """
        获取股票列表
        
        Returns:
            List[str]: 股票代码列表
        """
        existing_stocks = self.storage.stock_storage.list_stocks()
        
        if existing_stocks:
            return existing_stocks
        
        result = self.fetcher.fetch_stock_list()
        
        if result.success and result.data is not None:
            return result.data['stock_code'].tolist()
        
        self.logger.warning("无法获取股票列表")
        return []
    
    def _get_missing_dates(
        self,
        last_date: Optional[str],
        end_date: str
    ) -> List[str]:
        """
        获取缺失日期列表
        
        Args:
            last_date: 最后日期
            end_date: 结束日期
            
        Returns:
            List[str]: 缺失日期列表
        """
        if last_date is None:
            start = datetime.now() - timedelta(days=self.lookback_days)
        else:
            start = datetime.strptime(last_date, '%Y-%m-%d') + timedelta(days=1)
        
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        trading_days = self._get_trading_days(start, end)
        
        return [d.strftime('%Y-%m-%d') for d in trading_days]
    
    def _get_trading_days(
        self,
        start: datetime,
        end: datetime
    ) -> List[datetime]:
        """
        获取交易日列表
        
        Args:
            start: 开始日期
            end: 结束日期
            
        Returns:
            List[datetime]: 交易日列表
        """
        trading_days = []
        current = start
        
        while current <= end:
            if current.weekday() < 5:
                trading_days.append(current)
            current += timedelta(days=1)
        
        return trading_days
    
    def _update_metadata(self, stock_code: str, data: pd.DataFrame):
        """
        更新元数据
        
        Args:
            stock_code: 股票代码
            data: 股票数据
        """
        try:
            if 'date' in data.columns:
                data['date'] = pd.to_datetime(data['date'])
                start_date = data['date'].min().strftime('%Y-%m-%d')
                end_date = data['date'].max().strftime('%Y-%m-%d')
            else:
                start_date = None
                end_date = None
            
            self.metadata_manager.update_stock_metadata(
                stock_code,
                {
                    "start_date": start_date,
                    "end_date": end_date,
                    "rows": len(data),
                    "last_update": datetime.now().isoformat()
                }
            )
        except Exception as e:
            self.logger.warning(f"更新元数据失败 {stock_code}: {e}")
    
    def check_data_freshness(
        self,
        stock_codes: Optional[List[str]] = None,
        max_age_hours: int = 24
    ) -> Dict[str, bool]:
        """
        检查数据新鲜度
        
        Args:
            stock_codes: 股票代码列表
            max_age_hours: 最大允许的小时数
            
        Returns:
            Dict[str, bool]: 各股票数据是否新鲜
        """
        if stock_codes is None:
            stock_codes = self.storage.stock_storage.list_stocks()
        
        freshness = {}
        now = datetime.now()
        
        for code in stock_codes:
            info = self.storage.stock_storage.get_data_info(code)
            
            if not info.get('exists', False):
                freshness[code] = False
                continue
            
            end_date_str = info.get('end_date')
            if not end_date_str:
                freshness[code] = False
                continue
            
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                age_hours = (now - end_date).total_seconds() / 3600
                freshness[code] = age_hours <= max_age_hours
            except ValueError:
                freshness[code] = False
        
        return freshness
    
    def get_update_status(self) -> Dict[str, Any]:
        """
        获取更新状态
        
        Returns:
            Dict: 更新状态信息
        """
        stocks = self.storage.stock_storage.list_stocks()
        
        status = {
            "total_stocks": len(stocks),
            "stocks": {},
            "last_update": None
        }
        
        latest_update = None
        
        for code in stocks:
            info = self.storage.stock_storage.get_data_info(code)
            status["stocks"][code] = {
                "exists": info.get('exists', False),
                "rows": info.get('rows', 0),
                "start_date": info.get('start_date'),
                "end_date": info.get('end_date')
            }
            
            if info.get('end_date'):
                try:
                    end_date = datetime.strptime(info['end_date'], '%Y-%m-%d')
                    if latest_update is None or end_date > latest_update:
                        latest_update = end_date
                except ValueError:
                    pass
        
        if latest_update:
            status["last_update"] = latest_update.strftime('%Y-%m-%d')
        
        return status
    
    def update_financial_data(
        self,
        stock_codes: Optional[List[str]] = None
    ) -> UpdateResult:
        """
        更新财务数据
        
        Args:
            stock_codes: 股票代码列表（None则更新全部）
            
        Returns:
            UpdateResult: 更新结果
        """
        import time
        start_time = time.time()
        
        self.logger.info("开始更新财务数据")
        
        if stock_codes is None:
            stock_codes = self.storage.stock_storage.list_stocks()
        
        if not stock_codes:
            return UpdateResult(
                success=True,
                details={"message": "没有需要更新的股票"}
            )
        
        success_count = 0
        failed_count = 0
        total_rows = 0

        for stock_code in stock_codes:  # 移除数量限制（原限制：避免API限制）
            try:
                df = self.fetcher.get_fundamental(stock_codes=[stock_code])
                
                if df is not None and len(df) > 0:
                    result = self.storage.save_financial_data(df, stock_code)
                    if result.success:
                        success_count += 1
                        total_rows += result.rows_stored
                    else:
                        failed_count += 1
                        self.logger.warning(f"保存财务数据失败 {stock_code}: {result.error_message}")
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                self.logger.error(f"更新财务数据失败 {stock_code}: {e}")
        
        duration = time.time() - start_time
        
        self.logger.info(
            f"财务数据更新完成: 成功={success_count}, 失败={failed_count}, "
            f"新增行数={total_rows}, 耗时={duration:.2f}秒"
        )
        
        return UpdateResult(
            success=failed_count == 0,
            stocks_updated=success_count,
            stocks_failed=failed_count,
            total_rows_added=total_rows,
            duration_seconds=duration
        )
    
    def update_northbound_data(self) -> UpdateResult:
        """
        更新北向资金数据
        
        Returns:
            UpdateResult: 更新结果
        """
        import time
        start_time = time.time()
        
        self.logger.info("开始更新北向资金数据")
        
        total_rows = 0
        error_messages = []
        
        try:
            df_holding = self.fetcher.get_northbound_holding()
            if df_holding is not None and len(df_holding) > 0:
                result = self.storage.save_northbound_holding(df_holding)
                if result.success:
                    total_rows += result.rows_stored
                    self.logger.info(f"北向资金持股数据更新成功: {result.rows_stored}行")
                else:
                    error_messages.append(f"保存北向资金持股数据失败: {result.error_message}")
        except Exception as e:
            error_messages.append(f"获取北向资金持股数据失败: {str(e)}")
        
        try:
            df_flow = self.fetcher.get_northbound_flow()
            if df_flow is not None and len(df_flow) > 0:
                result = self.storage.save_northbound_flow(df_flow)
                if result.success:
                    total_rows += result.rows_stored
                    self.logger.info(f"北向资金净流入数据更新成功: {result.rows_stored}行")
                else:
                    error_messages.append(f"保存北向资金净流入数据失败: {result.error_message}")
        except Exception as e:
            error_messages.append(f"获取北向资金净流入数据失败: {str(e)}")
        
        duration = time.time() - start_time
        
        success = len(error_messages) == 0
        
        self.logger.info(
            f"北向资金数据更新完成: 成功={success}, "
            f"新增行数={total_rows}, 耗时={duration:.2f}秒"
        )
        
        return UpdateResult(
            success=success,
            total_rows_added=total_rows,
            error_messages=error_messages,
            duration_seconds=duration
        )
