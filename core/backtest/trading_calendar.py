"""
交易日历模块

提供A股交易日历功能，包括交易日判断、节假日处理等。
"""

from dataclasses import dataclass
from typing import Optional, List, Set, Dict, Any
from datetime import datetime, date, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)

try:
    from exchange_calendars import get_calendar
    HAS_EXCHANGE_CALENDARS = True
except ImportError:
    HAS_EXCHANGE_CALENDARS = False
    logger.warning("exchange_calendars未安装，将使用内置简化日历")


class MarketType(Enum):
    """市场类型"""
    SSE = "SSE"
    SZSE = "SZSE"
    A_SHARE = "A_SHARE"


@dataclass
class TradingSession:
    """交易时段"""
    name: str
    start_time: str
    end_time: str
    
    def is_in_session(self, time: datetime) -> bool:
        """检查时间是否在交易时段内"""
        time_str = time.strftime("%H:%M")
        return self.start_time <= time_str <= self.end_time


class TradingCalendar:
    """
    交易日历
    
    提供交易日判断、节假日处理等功能。
    """
    
    SSE_MORNING = TradingSession("上午", "09:30", "11:30")
    SSE_AFTERNOON = TradingSession("下午", "13:00", "15:00")
    
    A_SHARE_HOLIDAYS_2024 = {
        date(2024, 1, 1), date(2024, 2, 9), date(2024, 2, 10),
        date(2024, 2, 11), date(2024, 2, 12), date(2024, 2, 13),
        date(2024, 2, 14), date(2024, 2, 15), date(2024, 2, 16),
        date(2024, 2, 17), date(2024, 4, 4), date(2024, 4, 5),
        date(2024, 4, 6), date(2024, 5, 1), date(2024, 5, 2),
        date(2024, 5, 3), date(2024, 5, 4), date(2024, 5, 5),
        date(2024, 6, 8), date(2024, 6, 9), date(2024, 6, 10),
        date(2024, 9, 15), date(2024, 9, 16), date(2024, 9, 17),
        date(2024, 10, 1), date(2024, 10, 2), date(2024, 10, 3),
        date(2024, 10, 4), date(2024, 10, 5), date(2024, 10, 6),
        date(2024, 10, 7),
    }
    
    A_SHARE_HOLIDAYS_2025 = {
        date(2025, 1, 1), date(2025, 1, 28), date(2025, 1, 29),
        date(2025, 1, 30), date(2025, 1, 31), date(2025, 2, 1),
        date(2025, 2, 2), date(2025, 2, 3), date(2025, 2, 4),
        date(2025, 4, 4), date(2025, 4, 5), date(2025, 4, 6),
        date(2025, 5, 1), date(2025, 5, 2), date(2025, 5, 3),
        date(2025, 5, 4), date(2025, 5, 5), date(2025, 5, 31),
        date(2025, 6, 1), date(2025, 6, 2), date(2025, 10, 1),
        date(2025, 10, 2), date(2025, 10, 3), date(2025, 10, 4),
        date(2025, 10, 5), date(2025, 10, 6), date(2025, 10, 7),
        date(2025, 10, 8),
    }
    
    A_SHARE_HOLIDAYS_2026 = {
        date(2026, 1, 1), date(2026, 1, 28), date(2026, 1, 29),
        date(2026, 1, 30), date(2026, 1, 31), date(2026, 2, 1),
        date(2026, 2, 2), date(2026, 2, 3), date(2026, 2, 4),
        date(2026, 4, 4), date(2026, 4, 5), date(2026, 4, 6),
        date(2026, 5, 1), date(2026, 5, 2), date(2026, 5, 3),
        date(2026, 5, 4), date(2026, 5, 5), date(2026, 5, 31),
        date(2026, 6, 1), date(2026, 6, 2), date(2026, 10, 1),
        date(2026, 10, 2), date(2026, 10, 3), date(2026, 10, 4),
        date(2026, 10, 5), date(2026, 10, 6), date(2026, 10, 7),
        date(2026, 10, 8),
    }
    
    def __init__(
        self,
        market: MarketType = MarketType.A_SHARE,
        custom_holidays: Optional[Set[date]] = None,
        custom_trading_days: Optional[Set[date]] = None
    ):
        """
        初始化交易日历
        
        Args:
            market: 市场类型
            custom_holidays: 自定义节假日
            custom_trading_days: 自定义交易日（用于调休）
        """
        self.market = market
        self._custom_holidays = custom_holidays or set()
        self._custom_trading_days = custom_trading_days or set()
        
        self._holidays: Set[date] = set()
        self._trading_days: Set[date] = set()
        
        self._init_calendar()
    
    def _init_calendar(self):
        """初始化日历"""
        if HAS_EXCHANGE_CALENDARS:
            try:
                calendar_code = {
                    MarketType.SSE: "XSHG",
                    MarketType.SZSE: "XSHE",
                    MarketType.A_SHARE: "XSHG"
                }[self.market]
                
                self._ec_calendar = get_calendar(calendar_code)
                self._use_exchange_calendars = True
                logger.info(f"使用exchange_calendars日历: {calendar_code}")
                return
            except Exception as e:
                logger.warning(f"exchange_calendars初始化失败: {e}，使用内置日历")
        
        self._use_exchange_calendars = False
        self._init_builtin_calendar()
    
    def _init_builtin_calendar(self):
        """初始化内置日历"""
        self._holidays = (
            self.A_SHARE_HOLIDAYS_2024 | 
            self.A_SHARE_HOLIDAYS_2025 |
            self.A_SHARE_HOLIDAYS_2026 |
            self._custom_holidays
        )
        
        self._trading_days = self._custom_trading_days.copy()
    
    def is_trading_day(self, dt: date) -> bool:
        """
        判断是否为交易日
        
        Args:
            dt: 日期
            
        Returns:
            bool: 是否为交易日
        """
        if self._use_exchange_calendars:
            try:
                return self._ec_calendar.is_session(dt)
            except Exception as e:
                # 如果exchange_calendars日期越界，回退到内置日历
                logger.warning(f"exchange_calendars日期检查失败: {e}，回退到内置日历")
                self._use_exchange_calendars = False
                self._init_builtin_calendar()
        
        if dt in self._trading_days:
            return True
        
        if dt in self._holidays:
            return False
        
        weekday = dt.weekday()
        return weekday < 5
    
    def is_holiday(self, dt: date) -> bool:
        """
        判断是否为节假日
        
        Args:
            dt: 日期
            
        Returns:
            bool: 是否为节假日
        """
        return not self.is_trading_day(dt)
    
    def is_trading_time(self, dt: datetime) -> bool:
        """
        判断是否为交易时间
        
        Args:
            dt: 日期时间
            
        Returns:
            bool: 是否为交易时间
        """
        if not self.is_trading_day(dt.date()):
            return False
        
        time = dt.time()
        
        morning_start = datetime.strptime("09:30", "%H:%M").time()
        morning_end = datetime.strptime("11:30", "%H:%M").time()
        afternoon_start = datetime.strptime("13:00", "%H:%M").time()
        afternoon_end = datetime.strptime("15:00", "%H:%M").time()
        
        return (
            (morning_start <= time <= morning_end) or
            (afternoon_start <= time <= afternoon_end)
        )
    
    def get_next_trading_day(self, dt: date) -> date:
        """
        获取下一个交易日
        
        Args:
            dt: 当前日期
            
        Returns:
            date: 下一个交易日
        """
        next_day = dt + timedelta(days=1)
        max_days = 30
        count = 0
        
        while not self.is_trading_day(next_day) and count < max_days:
            next_day += timedelta(days=1)
            count += 1
        
        return next_day
    
    def get_previous_trading_day(self, dt: date) -> date:
        """
        获取上一个交易日
        
        Args:
            dt: 当前日期
            
        Returns:
            date: 上一个交易日
        """
        prev_day = dt - timedelta(days=1)
        max_days = 30
        count = 0
        
        while not self.is_trading_day(prev_day) and count < max_days:
            prev_day -= timedelta(days=1)
            count += 1
        
        return prev_day
    
    def get_trading_days(
        self,
        start: date,
        end: date
    ) -> List[date]:
        """
        获取日期范围内的所有交易日
        
        Args:
            start: 开始日期
            end: 结束日期
            
        Returns:
            List[date]: 交易日列表
        """
        if self._use_exchange_calendars:
            try:
                sessions = self._ec_calendar.sessions_in_range(start, end)
                return [s.date() for s in sessions]
            except Exception as e:
                # 如果exchange_calendars日期越界，回退到内置日历
                logger.warning(f"exchange_calendars日期范围检查失败: {e}，回退到内置日历")
                self._use_exchange_calendars = False
                self._init_builtin_calendar()
        
        trading_days = []
        current = start
        
        while current <= end:
            if self.is_trading_day(current):
                trading_days.append(current)
            current += timedelta(days=1)
        
        return trading_days
    
    def get_trading_days_count(
        self,
        start: date,
        end: date
    ) -> int:
        """
        获取日期范围内的交易日数量
        
        Args:
            start: 开始日期
            end: 结束日期
            
        Returns:
            int: 交易日数量
        """
        return len(self.get_trading_days(start, end))
    
    def get_holidays(
        self,
        start: date,
        end: date
    ) -> List[date]:
        """
        获取日期范围内的所有节假日
        
        Args:
            start: 开始日期
            end: 结束日期
            
        Returns:
            List[date]: 节假日列表
        """
        holidays = []
        current = start
        
        while current <= end:
            if self.is_holiday(current):
                holidays.append(current)
            current += timedelta(days=1)
        
        return holidays
    
    def add_holiday(self, dt: date):
        """添加节假日"""
        self._holidays.add(dt)
        self._trading_days.discard(dt)
    
    def add_trading_day(self, dt: date):
        """添加交易日（用于调休）"""
        self._trading_days.add(dt)
        self._holidays.discard(dt)
    
    def get_trading_sessions(self, dt: date) -> List[TradingSession]:
        """
        获取指定日期的交易时段
        
        Args:
            dt: 日期
            
        Returns:
            List[TradingSession]: 交易时段列表
        """
        if not self.is_trading_day(dt):
            return []
        
        return [self.SSE_MORNING, self.SSE_AFTERNOON]
    
    def get_market_open_time(self, dt: date) -> Optional[datetime]:
        """获取开盘时间"""
        if not self.is_trading_day(dt):
            return None
        return datetime.combine(dt, datetime.strptime("09:30", "%H:%M").time())
    
    def get_market_close_time(self, dt: date) -> Optional[datetime]:
        """获取收盘时间"""
        if not self.is_trading_day(dt):
            return None
        return datetime.combine(dt, datetime.strptime("15:00", "%H:%M").time())
    
    def get_info(self, dt: date) -> Dict[str, Any]:
        """
        获取日期信息
        
        Args:
            dt: 日期
            
        Returns:
            Dict: 日期信息
        """
        return {
            'date': dt.isoformat(),
            'is_trading_day': self.is_trading_day(dt),
            'is_holiday': self.is_holiday(dt),
            'weekday': dt.weekday(),
            'weekday_name': ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][dt.weekday()],
            'sessions': [s.name for s in self.get_trading_sessions(dt)]
        }


class TradingCalendarManager:
    """
    交易日历管理器
    
    管理多个市场的交易日历。
    """
    
    _calendars: Dict[str, TradingCalendar] = {}
    
    @classmethod
    def get(cls, market: str = "A_SHARE") -> TradingCalendar:
        """
        获取交易日历
        
        Args:
            market: 市场代码
            
        Returns:
            TradingCalendar: 交易日历
        """
        if market not in cls._calendars:
            market_type = MarketType(market) if market in [m.value for m in MarketType] else MarketType.A_SHARE
            cls._calendars[market] = TradingCalendar(market_type)
        return cls._calendars[market]
    
    @classmethod
    def register(cls, name: str, calendar: TradingCalendar):
        """注册交易日历"""
        cls._calendars[name] = calendar
    
    @classmethod
    def list_calendars(cls) -> List[str]:
        """列出所有已注册的日历"""
        return list(cls._calendars.keys())


def get_trading_calendar(market: str = "A_SHARE") -> TradingCalendar:
    """
    获取交易日历的便捷函数
    
    Args:
        market: 市场代码
        
    Returns:
        TradingCalendar: 交易日历
    """
    return TradingCalendarManager.get(market)


def is_trading_day(dt: date, market: str = "A_SHARE") -> bool:
    """
    判断是否为交易日的便捷函数
    
    Args:
        dt: 日期
        market: 市场代码
        
    Returns:
        bool: 是否为交易日
    """
    return get_trading_calendar(market).is_trading_day(dt)


def get_next_trading_day(dt: date, market: str = "A_SHARE") -> date:
    """
    获取下一个交易日的便捷函数
    
    Args:
        dt: 当前日期
        market: 市场代码
        
    Returns:
        date: 下一个交易日
    """
    return get_trading_calendar(market).get_next_trading_day(dt)


def get_trading_days(start: date, end: date, market: str = "A_SHARE") -> List[date]:
    """
    获取交易日列表的便捷函数
    
    Args:
        start: 开始日期
        end: 结束日期
        market: 市场代码
        
    Returns:
        List[date]: 交易日列表
    """
    return get_trading_calendar(market).get_trading_days(start, end)
