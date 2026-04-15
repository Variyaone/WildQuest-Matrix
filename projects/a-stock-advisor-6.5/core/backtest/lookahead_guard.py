"""
未来函数检测机制

防止回测中使用未来数据（Look-Ahead Bias）。
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Set
from datetime import datetime, date
from enum import Enum
import pandas as pd
import numpy as np
import logging
import inspect
import traceback

logger = logging.getLogger(__name__)


class LookAheadBiasError(Exception):
    """未来函数错误"""
    pass


class DataAccessType(Enum):
    """数据访问类型"""
    CURRENT = "current"
    HISTORY = "history"
    FUTURE = "future"


@dataclass
class DataAccessRecord:
    """数据访问记录"""
    access_time: datetime
    bar_time: datetime
    data_time: datetime
    access_type: DataAccessType
    stock_code: Optional[str] = None
    field: Optional[str] = None
    stack_trace: Optional[str] = None
    source_location: Optional[str] = None


@dataclass
class LookAheadViolation:
    """未来函数违规"""
    bar_time: datetime
    data_time: datetime
    time_diff: int
    stock_code: Optional[str] = None
    field: Optional[str] = None
    stack_trace: Optional[str] = None
    source_location: Optional[str] = None
    severity: str = "ERROR"


class LookAheadGuard:
    """
    未来函数检测器
    
    检测并防止回测中使用未来数据。
    """
    
    def __init__(
        self,
        strict_mode: bool = True,
        allowed_future_bars: int = 0,
        log_access: bool = True,
        raise_on_violation: bool = False
    ):
        """
        初始化未来函数检测器
        
        Args:
            strict_mode: 严格模式，任何未来数据访问都会报错
            allowed_future_bars: 允许的未来bar数（用于某些特殊情况）
            log_access: 是否记录所有数据访问
            raise_on_violation: 发现违规时是否抛出异常
        """
        self.strict_mode = strict_mode
        self.allowed_future_bars = allowed_future_bars
        self.log_access = log_access
        self.raise_on_violation = raise_on_violation
        
        self._current_bar_time: Optional[datetime] = None
        self._access_records: List[DataAccessRecord] = []
        self._violations: List[LookAheadViolation] = []
        self._protected_fields: Set[str] = {
            'open', 'high', 'low', 'close', 'volume', 'amount',
            'vwap', 'turnover', 'pct_chg', 'change',
            'bid', 'ask', 'bid_volume', 'ask_volume'
        }
        self._enabled: bool = True
        self._data_snapshot: Dict[str, Any] = {}
    
    def enable(self):
        """启用检测"""
        self._enabled = True
    
    def disable(self):
        """禁用检测"""
        self._enabled = False
    
    def set_bar_time(self, bar_time: datetime):
        """
        设置当前bar时间
        
        Args:
            bar_time: 当前bar时间
        """
        self._current_bar_time = bar_time
    
    def get_current_bar_time(self) -> Optional[datetime]:
        """获取当前bar时间"""
        return self._current_bar_time
    
    def register_data_snapshot(self, data: pd.DataFrame, time_column: str = 'date'):
        """
        注册数据快照，用于检测
        
        Args:
            data: 数据DataFrame
            time_column: 时间列名
        """
        if time_column in data.columns:
            self._data_snapshot = {
                'data': data,
                'time_column': time_column,
                'min_time': data[time_column].min(),
                'max_time': data[time_column].max()
            }
    
    def check_data_access(
        self,
        data_time: datetime,
        stock_code: Optional[str] = None,
        field: Optional[str] = None
    ) -> bool:
        """
        检查数据访问是否合法
        
        Args:
            data_time: 被访问数据的时间
            stock_code: 股票代码
            field: 字段名
            
        Returns:
            bool: 是否合法
        """
        if not self._enabled:
            return True
        
        if self._current_bar_time is None:
            return True
        
        access_type = self._determine_access_type(data_time)
        
        if self.log_access:
            record = DataAccessRecord(
                access_time=datetime.now(),
                bar_time=self._current_bar_time,
                data_time=data_time,
                access_type=access_type,
                stock_code=stock_code,
                field=field,
                stack_trace=self._get_stack_trace(),
                source_location=self._get_source_location()
            )
            self._access_records.append(record)
        
        if access_type == DataAccessType.FUTURE:
            time_diff = (data_time - self._current_bar_time).days
            
            if time_diff > self.allowed_future_bars:
                violation = LookAheadViolation(
                    bar_time=self._current_bar_time,
                    data_time=data_time,
                    time_diff=time_diff,
                    stock_code=stock_code,
                    field=field,
                    stack_trace=self._get_stack_trace(),
                    source_location=self._get_source_location(),
                    severity="ERROR" if self.strict_mode else "WARNING"
                )
                self._violations.append(violation)
                
                logger.error(
                    f"检测到未来函数！当前bar: {self._current_bar_time}, "
                    f"访问数据时间: {data_time}, 时间差: {time_diff}天, "
                    f"股票: {stock_code}, 字段: {field}"
                )
                
                if self.raise_on_violation:
                    raise LookAheadBiasError(
                        f"检测到未来函数！当前bar时间: {self._current_bar_time}, "
                        f"访问数据时间: {data_time}, 时间差: {time_diff}天"
                    )
                
                return False
        
        return True
    
    def check_dataframe_access(
        self,
        df: pd.DataFrame,
        time_column: str = 'date',
        stock_column: str = 'stock_code'
    ) -> bool:
        """
        检查DataFrame访问是否合法
        
        Args:
            df: 被访问的DataFrame
            time_column: 时间列名
            stock_column: 股票代码列名
            
        Returns:
            bool: 是否合法
        """
        if not self._enabled or self._current_bar_time is None:
            return True
        
        if time_column not in df.columns:
            return True
        
        future_data = df[df[time_column] > self._current_bar_time]
        
        if len(future_data) > 0:
            logger.warning(
                f"DataFrame包含未来数据！当前bar: {self._current_bar_time}, "
                f"未来数据条数: {len(future_data)}"
            )
            return False
        
        return True
    
    def filter_future_data(
        self,
        df: pd.DataFrame,
        time_column: str = 'date'
    ) -> pd.DataFrame:
        """
        过滤掉未来数据
        
        Args:
            df: 原始DataFrame
            time_column: 时间列名
            
        Returns:
            pd.DataFrame: 过滤后的DataFrame
        """
        if not self._enabled or self._current_bar_time is None:
            return df
        
        if time_column not in df.columns:
            return df
        
        return df[df[time_column] <= self._current_bar_time].copy()
    
    def _determine_access_type(self, data_time: datetime) -> DataAccessType:
        """确定数据访问类型"""
        if self._current_bar_time is None:
            return DataAccessType.CURRENT
        
        if data_time < self._current_bar_time:
            return DataAccessType.HISTORY
        elif data_time > self._current_bar_time:
            return DataAccessType.FUTURE
        else:
            return DataAccessType.CURRENT
    
    def _get_stack_trace(self) -> str:
        """获取调用栈"""
        return ''.join(traceback.format_stack()[-5:-1])
    
    def _get_source_location(self) -> str:
        """获取源码位置"""
        for frame_info in inspect.stack()[2:]:
            if 'site-packages' not in frame_info.filename and \
               'lookahead_guard' not in frame_info.filename:
                return f"{frame_info.filename}:{frame_info.lineno}"
        return "unknown"
    
    def get_violations(self) -> List[LookAheadViolation]:
        """获取所有违规记录"""
        return self._violations.copy()
    
    def get_access_records(self) -> List[DataAccessRecord]:
        """获取所有访问记录"""
        return self._access_records.copy()
    
    def has_violations(self) -> bool:
        """是否存在违规"""
        return len(self._violations) > 0
    
    def clear_records(self):
        """清除记录"""
        self._access_records.clear()
        self._violations.clear()
    
    def get_report(self) -> Dict[str, Any]:
        """生成检测报告"""
        return {
            'enabled': self._enabled,
            'current_bar_time': self._current_bar_time.isoformat() if self._current_bar_time else None,
            'total_accesses': len(self._access_records),
            'total_violations': len(self._violations),
            'violations': [
                {
                    'bar_time': v.bar_time.isoformat(),
                    'data_time': v.data_time.isoformat(),
                    'time_diff': v.time_diff,
                    'stock_code': v.stock_code,
                    'field': v.field,
                    'source_location': v.source_location,
                    'severity': v.severity
                }
                for v in self._violations
            ],
            'access_summary': {
                'history': len([r for r in self._access_records if r.access_type == DataAccessType.HISTORY]),
                'current': len([r for r in self._access_records if r.access_type == DataAccessType.CURRENT]),
                'future': len([r for r in self._access_records if r.access_type == DataAccessType.FUTURE])
            }
        }


class DataAccessor:
    """
    安全数据访问器
    
    包装数据访问，自动进行未来函数检测。
    """
    
    def __init__(
        self,
        data: pd.DataFrame,
        guard: LookAheadGuard,
        time_column: str = 'date',
        stock_column: str = 'stock_code'
    ):
        """
        初始化数据访问器
        
        Args:
            data: 数据DataFrame
            guard: 未来函数检测器
            time_column: 时间列名
            stock_column: 股票代码列名
        """
        self._data = data
        self._guard = guard
        self._time_column = time_column
        self._stock_column = stock_column
    
    def current(
        self,
        stock_code: Optional[str] = None,
        fields: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        获取当前bar数据
        
        Args:
            stock_code: 股票代码（可选，None表示所有股票）
            fields: 字段列表（可选）
            
        Returns:
            pd.DataFrame: 当前数据
        """
        current_time = self._guard.get_current_bar_time()
        if current_time is None:
            raise ValueError("未设置当前bar时间")
        
        mask = self._data[self._time_column] == current_time
        
        if stock_code is not None:
            mask &= (self._data[self._stock_column] == stock_code)
        
        result = self._data[mask]
        
        if fields is not None:
            available_fields = [f for f in fields if f in result.columns]
            if self._time_column not in available_fields:
                available_fields.append(self._time_column)
            if self._stock_column not in available_fields:
                available_fields.append(self._stock_column)
            result = result[available_fields]
        
        self._guard.check_data_access(current_time, stock_code)
        
        return result.copy()
    
    def history(
        self,
        bars: int,
        stock_code: Optional[str] = None,
        fields: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        获取历史数据
        
        Args:
            bars: 历史bar数
            stock_code: 股票代码
            fields: 字段列表
            
        Returns:
            pd.DataFrame: 历史数据
        """
        current_time = self._guard.get_current_bar_time()
        if current_time is None:
            raise ValueError("未设置当前bar时间")
        
        mask = self._data[self._time_column] <= current_time
        
        if stock_code is not None:
            mask &= (self._data[self._stock_column] == stock_code)
        
        filtered = self._data[mask].sort_values(self._time_column, ascending=False)
        
        if stock_code is not None:
            filtered = filtered.groupby(self._stock_column).head(bars)
        else:
            unique_times = filtered[self._time_column].unique()[:bars]
            filtered = filtered[filtered[self._time_column].isin(unique_times)]
        
        if fields is not None:
            available_fields = [f for f in fields if f in filtered.columns]
            if self._time_column not in available_fields:
                available_fields.append(self._time_column)
            if self._stock_column not in available_fields:
                available_fields.append(self._stock_column)
            filtered = filtered[available_fields]
        
        for data_time in filtered[self._time_column].unique():
            self._guard.check_data_access(data_time, stock_code)
        
        return filtered.sort_values(self._time_column).copy()
    
    def can_access(
        self,
        data_time: datetime,
        stock_code: Optional[str] = None
    ) -> bool:
        """
        检查是否可以访问指定时间的数据
        
        Args:
            data_time: 数据时间
            stock_code: 股票代码
            
        Returns:
            bool: 是否可以访问
        """
        return self._guard.check_data_access(data_time, stock_code)


class LookAheadValidator:
    """
    未来函数验证器
    
    用于验证策略是否存在未来函数问题。
    """
    
    def __init__(self):
        self._guard = LookAheadGuard(
            strict_mode=True,
            log_access=True,
            raise_on_violation=False
        )
    
    def validate_strategy(
        self,
        strategy_func: callable,
        data: pd.DataFrame,
        sample_dates: Optional[List[datetime]] = None,
        time_column: str = 'date'
    ) -> Dict[str, Any]:
        """
        验证策略是否存在未来函数
        
        Args:
            strategy_func: 策略函数
            data: 数据
            sample_dates: 抽样日期列表
            time_column: 时间列名
            
        Returns:
            Dict: 验证结果
        """
        if sample_dates is None:
            unique_dates = sorted(data[time_column].unique())
            sample_size = min(10, len(unique_dates))
            sample_dates = unique_dates[:sample_size]
        
        accessor = DataAccessor(data, self._guard, time_column)
        
        all_violations = []
        
        for test_date in sample_dates:
            self._guard.clear_records()
            self._guard.set_bar_time(test_date)
            
            try:
                test_data = self._guard.filter_future_data(data, time_column)
                
                result = strategy_func(
                    date=test_date,
                    data=test_data[test_data[time_column] == test_date],
                    accessor=accessor
                )
                
                if self._guard.has_violations():
                    all_violations.extend([
                        {
                            'test_date': test_date.isoformat() if hasattr(test_date, 'isoformat') else str(test_date),
                            **v.__dict__
                        }
                        for v in self._guard.get_violations()
                    ])
            
            except Exception as e:
                logger.warning(f"策略验证时发生错误: {e}")
        
        return {
            'valid': len(all_violations) == 0,
            'total_violations': len(all_violations),
            'violations': all_violations,
            'sample_dates_tested': len(sample_dates),
            'report': self._guard.get_report()
        }
    
    @staticmethod
    def quick_check(
        data: pd.DataFrame,
        time_column: str = 'date'
    ) -> Dict[str, Any]:
        """
        快速检查数据是否按时间排序
        
        Args:
            data: 数据
            time_column: 时间列名
            
        Returns:
            Dict: 检查结果
        """
        if time_column not in data.columns:
            return {
                'valid': True,
                'message': '时间列不存在，跳过检查'
            }
        
        times = data[time_column].values
        
        is_sorted = all(times[i] <= times[i+1] for i in range(len(times)-1))
        
        duplicates = data[data.duplicated(subset=[time_column], keep=False)]
        has_duplicates = len(duplicates) > 0
        
        return {
            'valid': is_sorted,
            'is_sorted': is_sorted,
            'has_duplicates': has_duplicates,
            'duplicate_count': len(duplicates),
            'message': '数据已按时间排序' if is_sorted else '数据未按时间排序，可能存在未来函数风险'
        }
