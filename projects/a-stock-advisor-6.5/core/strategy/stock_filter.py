"""
股票池过滤器

过滤无效股票，提高Alpha生成效率
"""

from typing import List, Optional
import pandas as pd
from datetime import datetime, timedelta

from ..data import get_data_fetcher
from ..infrastructure.logging import get_logger

logger = get_logger("strategy.stock_filter")


def classify_stock_type(stock_code: str) -> str:
    """
    根据股票代码识别证券类型
    
    Args:
        stock_code: 股票代码
        
    Returns:
        证券类型
    """
    code_num = stock_code.split('.')[1][:3] if '.' in stock_code else stock_code[:3]
    
    try:
        num = int(code_num)
        
        if 600 <= num <= 687:
            return '沪市主板'
        elif 688 <= num <= 689:
            return '科创板'
        elif num <= 2:
            return '深市主板'
        elif 300 <= num <= 301:
            return '创业板'
        elif 159 <= num < 160:
            return '深市ETF'
        elif 510 <= num < 520:
            return '沪市ETF'
        elif 110 <= num < 120:
            return '沪市债券'
        elif 128 <= num < 129:
            return '深市债券'
        elif 113 <= num < 114:
            return '沪市可转债'
        elif 123 <= num < 124:
            return '深市可转债'
        else:
            return '其他'
    except:
        return '其他'


def filter_real_stocks(stock_codes: List[str]) -> List[str]:
    """
    过滤出真正的股票（排除ETF、债券等）
    
    Args:
        stock_codes: 股票代码列表
        
    Returns:
        只包含真实股票的列表
    """
    stock_types = ['沪市主板', '深市主板', '科创板', '创业板']
    
    real_stocks = []
    for code in stock_codes:
        stock_type = classify_stock_type(code)
        if stock_type in stock_types:
            real_stocks.append(code)
    
    logger.info(f"证券类型过滤: {len(stock_codes)} → {len(real_stocks)} 只真实股票")
    
    return real_stocks


class StockPoolFilter:
    """股票池过滤器"""
    
    def __init__(
        self,
        min_market_cap: Optional[float] = None,
        min_price: Optional[float] = None,
        exclude_st: bool = True,
        exclude_suspended: bool = True,
        require_recent_data: bool = True,
        recent_data_days: int = 30
    ):
        """
        初始化股票池过滤器
        
        Args:
            min_market_cap: 最小市值（万元）
            min_price: 最小股价
            exclude_st: 是否排除ST股票
            exclude_suspended: 是否排除停牌股票
            require_recent_data: 是否要求近期有交易数据
            recent_data_days: 近期数据天数
        """
        self.min_market_cap = min_market_cap
        self.min_price = min_price
        self.exclude_st = exclude_st
        self.exclude_suspended = exclude_suspended
        self.require_recent_data = require_recent_data
        self.recent_data_days = recent_data_days
        
        self._fetcher = get_data_fetcher()
    
    def filter(self, stock_codes: List[str], silent: bool = False) -> List[str]:
        """
        过滤股票池
        
        Args:
            stock_codes: 原始股票代码列表
            silent: 是否静默模式（不输出错误信息）
            
        Returns:
            过滤后的股票代码列表
        """
        if not stock_codes:
            return []
        
        valid_stocks = []
        
        if self.require_recent_data:
            valid_stocks = self._filter_by_recent_data(stock_codes, silent)
        else:
            valid_stocks = stock_codes
        
        if self.exclude_st:
            valid_stocks = [s for s in valid_stocks if not self._is_st_stock(s)]
        
        logger.info(f"股票池过滤: {len(stock_codes)} → {len(valid_stocks)}")
        
        return valid_stocks
    
    def _filter_by_recent_data(self, stock_codes: List[str], silent: bool) -> List[str]:
        """过滤有近期数据的股票"""
        valid_stocks = []
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=self.recent_data_days)).strftime('%Y-%m-%d')
        
        for code in stock_codes:
            try:
                data = self._fetcher.get_history(code, start=start_date, end=end_date)
                if data is not None and not data.empty:
                    valid_stocks.append(code)
            except Exception:
                if not silent:
                    pass
        
        return valid_stocks
    
    def _is_st_stock(self, stock_code: str) -> bool:
        """判断是否为ST股票"""
        return 'ST' in stock_code.upper() or '*ST' in stock_code.upper()


def filter_stock_pool(
    stock_codes: List[str],
    silent: bool = False,
    quick_mode: bool = True
) -> List[str]:
    """
    快速过滤股票池
    
    Args:
        stock_codes: 股票代码列表
        silent: 是否静默模式
        quick_mode: 是否快速模式（只检查部分股票）
        
    Returns:
        过滤后的股票代码列表
    """
    if quick_mode and len(stock_codes) > 100:
        test_sample = stock_codes[:100]
        
        fetcher = get_data_fetcher()
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        valid_count = 0
        for code in test_sample:
            try:
                data = fetcher.get_history(code, start=start_date, end=end_date)
                if data is not None and not data.empty:
                    valid_count += 1
            except Exception:
                pass
        
        valid_ratio = valid_count / len(test_sample)
        
        estimated_valid = int(len(stock_codes) * valid_ratio)
        
        logger.info(f"快速过滤: 采样{len(test_sample)}只, 有效率{valid_ratio:.1%}, 预估有效{estimated_valid}只")
        
        return stock_codes[:estimated_valid]
    else:
        stock_filter = StockPoolFilter(require_recent_data=True)
        return stock_filter.filter(stock_codes, silent)
