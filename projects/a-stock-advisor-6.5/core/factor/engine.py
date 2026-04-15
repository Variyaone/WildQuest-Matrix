"""
因子计算引擎模块

高效计算因子值，支持公式表达式解析、插件式因子扩展、批量并行计算和增量更新。
"""

import re
import ast
import operator
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import functools

import pandas as pd
import numpy as np

from .registry import FactorMetadata, get_factor_registry
from ..infrastructure.exceptions import FactorException


@dataclass
class FactorComputeResult:
    """因子计算结果"""
    success: bool
    factor_id: str
    data: Optional[pd.DataFrame] = None
    error_message: Optional[str] = None
    compute_time: float = 0.0
    stock_count: int = 0
    date_count: int = 0


class OperatorRegistry:
    """
    算子注册表
    
    管理所有可用的计算算子。
    """
    
    def __init__(self):
        """初始化算子注册表"""
        self._operators: Dict[str, Callable] = {}
        self._register_builtin_operators()
    
    def _register_builtin_operators(self):
        """注册内置算子"""
        self.register("ts_mean", lambda x, window: x.rolling(window=window).mean())
        self.register("ts_std", lambda x, window: x.rolling(window=window).std())
        self.register("ts_sum", lambda x, window: x.rolling(window=window).sum())
        self.register("ts_max", lambda x, window: x.rolling(window=window).max())
        self.register("ts_min", lambda x, window: x.rolling(window=window).min())
        self.register("ts_rank", lambda x, window: x.rolling(window=window).rank(pct=True))
        self.register("ts_delta", lambda x, window: x.diff(window))
        self.register("ts_pct_change", lambda x, window: x.pct_change(window))
        self.register("ts_corr", lambda x, y, window: x.rolling(window=window).corr(y))
        self.register("ts_cov", lambda x, y, window: x.rolling(window=window).cov(y))
        
        self.register("MA", lambda x, window: x.rolling(window=window).mean())
        self.register("STD", lambda x, window: x.rolling(window=window).std())
        
        self.register("cs_rank", lambda x: x.rank(pct=True))
        self.register("cs_zscore", lambda x: (x - x.mean()) / x.std())
        self.register("cs_demean", lambda x: x - x.mean())
        self.register("cs_scale", lambda x: x / x.abs().sum())
        
        self.register("delay", lambda x, window: x.shift(window))
        self.register("abs", np.abs)
        self.register("log", np.log)
        self.register("log1p", np.log1p)
        self.register("sqrt", np.sqrt)
        self.register("square", np.square)
        self.register("sign", np.sign)
        
        self.register("max", np.maximum)
        self.register("min", np.minimum)
        self.register("sum", np.nansum)
        self.register("mean", np.nanmean)
        self.register("std", np.nanstd)
        
        self.register("delta", lambda x, window: x.diff(window))
        self.register("sma", lambda x, n, m=1: x.ewm(alpha=m/n, adjust=False).mean() if m > 0 else x.rolling(window=n).mean())
        self.register("ema", lambda x, window: x.ewm(span=window, adjust=False).mean())
        
        def if_else_impl(cond, x, y):
            if isinstance(cond, pd.Series):
                return pd.Series(np.where(cond.values, x.values if isinstance(x, pd.Series) else x, y.values if isinstance(y, pd.Series) else y), index=cond.index)
            return np.where(cond, x, y)
        self.register("if_else", if_else_impl)
        
        self.register("returns", lambda x: x.pct_change())
        self.register("rank", lambda x: x.rank(pct=True))
        self.register("scale", lambda x: (x - x.min()) / (x.max() - x.min()) if x.max() != x.min() else x * 0)
        self.register("power", np.power)
        self.register("ref", lambda x, window: x.shift(window))
        
        self.register("adv", lambda volume, window: volume.rolling(window=window).mean())
        self.register("ts_argmax", lambda x, window: x.rolling(window=window).apply(lambda arr: arr.argmax() if len(arr) > 0 else 0, raw=True))
        self.register("ts_argmin", lambda x, window: x.rolling(window=window).apply(lambda arr: arr.argmin() if len(arr) > 0 else 0, raw=True))
        self.register("ts_product", lambda x, window: x.rolling(window=window).apply(lambda arr: arr.prod(), raw=True))
        self.register("ts_av_diff", lambda x, window: x - x.rolling(window=window).mean())
        self.register("ts_rank", lambda x, window: x.rolling(window=window).rank(pct=True))
        
        def decay_linear_impl(x, window):
            weights = np.arange(1, window + 1)
            return x.rolling(window=window).apply(lambda arr: (arr * weights).sum() / weights.sum() if len(arr) == window else np.nan, raw=True)
        self.register("decay_linear", decay_linear_impl)
        
        def wma_impl(x, window):
            weights = np.arange(1, window + 1)
            return x.rolling(window=window).apply(lambda arr: (arr * weights).sum() / weights.sum() if len(arr) == window else np.nan, raw=True)
        self.register("wma", wma_impl)
        
        def reg_beta_impl(y, x, window):
            def calc_beta(arr_y, arr_x):
                if len(arr_y) < 2:
                    return np.nan
                x_mean = arr_x.mean()
                y_mean = arr_y.mean()
                numerator = ((arr_x - x_mean) * (arr_y - y_mean)).sum()
                denominator = ((arr_x - x_mean) ** 2).sum()
                return numerator / denominator if denominator != 0 else np.nan
            return pd.Series([calc_beta(y.iloc[i-window+1:i+1].values, x.iloc[i-window+1:i+1].values) if i >= window-1 else np.nan for i in range(len(y))], index=y.index)
        self.register("reg_beta", reg_beta_impl)
        
        def reg_resi_impl(y, x, window):
            def calc_resi(arr_y, arr_x):
                if len(arr_y) < 2:
                    return np.nan
                x_mean = arr_x.mean()
                y_mean = arr_y.mean()
                numerator = ((arr_x - x_mean) * (arr_y - y_mean)).sum()
                denominator = ((arr_x - x_mean) ** 2).sum()
                beta = numerator / denominator if denominator != 0 else 0
                alpha = y_mean - beta * x_mean
                return arr_y[-1] - (alpha + beta * arr_x[-1])
            return pd.Series([calc_resi(y.iloc[i-window+1:i+1].values, x.iloc[i-window+1:i+1].values) if i >= window-1 else np.nan for i in range(len(y))], index=y.index)
        self.register("reg_resi", reg_resi_impl)
        
        self.register("sequence", lambda n: pd.Series(range(1, n + 1)))
        
        def min_impl(*args):
            if len(args) == 1:
                return args[0].min() if hasattr(args[0], 'min') else args[0]
            return np.minimum(*args)
        self.register("min", min_impl)
        
        def ts_skewness_impl(x, window):
            return x.rolling(window=window).skew()
        self.register("ts_skewness", ts_skewness_impl)
        
        def ts_kurtosis_impl(x, window):
            return x.rolling(window=window).kurt()
        self.register("ts_kurtosis", ts_kurtosis_impl)
        
        def ts_percentile_impl(x, window, percentile=50):
            return x.rolling(window=window).apply(lambda arr: np.percentile(arr, percentile), raw=True)
        self.register("ts_percentile", ts_percentile_impl)
        
        def signpower_impl(x, n):
            return np.sign(x) * np.power(np.abs(x), n)
        self.register("signpower", signpower_impl)
        
        def covariance_impl(x, y, window):
            return x.rolling(window=window).cov(y)
        self.register("covariance", covariance_impl)
        
        self.register("SMA", lambda x, window: x.rolling(window=window).mean())
        self.register("EMA", lambda x, window: x.ewm(span=window, adjust=False).mean())
        
        def RSI_impl(x, window=14):
            delta = x.diff()
            gain = delta.where(delta > 0, 0)
            loss = (-delta).where(delta < 0, 0)
            avg_gain = gain.rolling(window=window).mean()
            avg_loss = loss.rolling(window=window).mean()
            rs = avg_gain / avg_loss.replace(0, np.nan)
            return 100 - (100 / (1 + rs))
        self.register("RSI", RSI_impl)
        
        def MACD_impl(x, fast=12, slow=26, signal=9):
            ema_fast = x.ewm(span=fast, adjust=False).mean()
            ema_slow = x.ewm(span=slow, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal, adjust=False).mean()
            return macd_line
        self.register("MACD", MACD_impl)
        
        def MACD_SIGNAL_impl(x, fast=12, slow=26, signal=9):
            ema_fast = x.ewm(span=fast, adjust=False).mean()
            ema_slow = x.ewm(span=slow, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            return macd_line.ewm(span=signal, adjust=False).mean()
        self.register("MACD_SIGNAL", MACD_SIGNAL_impl)
        
        def MACD_HIST_impl(x, fast=12, slow=26, signal=9):
            ema_fast = x.ewm(span=fast, adjust=False).mean()
            ema_slow = x.ewm(span=slow, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal, adjust=False).mean()
            return macd_line - signal_line
        self.register("MACD_HIST", MACD_HIST_impl)
        
        def ATR_impl(high, low, close, window=14):
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            return tr.rolling(window=window).mean()
        self.register("ATR", ATR_impl)
        
        def ADX_impl(high, low, close, window=14):
            tr = ATR_impl(high, low, close, 1)
            plus_dm = high.diff()
            minus_dm = -low.diff()
            plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
            minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
            plus_di = 100 * (plus_dm.rolling(window=window).mean() / tr.rolling(window=window).mean())
            minus_di = 100 * (minus_dm.rolling(window=window).mean() / tr.rolling(window=window).mean())
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)
            return dx.rolling(window=window).mean()
        self.register("ADX", ADX_impl)
        self.register("ADXR", lambda high, low, close, window=14: ADX_impl(high, low, close, window).rolling(window=window).mean())
        
        def CCI_impl(high, low, close, window=20):
            tp = (high + low + close) / 3
            sma = tp.rolling(window=window).mean()
            mad = tp.rolling(window=window).apply(lambda x: np.abs(x - x.mean()).mean())
            return (tp - sma) / (0.015 * mad.replace(0, np.nan))
        self.register("CCI", CCI_impl)
        
        def OBV_impl(close, volume):
            direction = np.sign(close.diff())
            direction.iloc[0] = 1
            return (volume * direction).cumsum()
        self.register("OBV", OBV_impl)
        
        def MFI_impl(high, low, close, volume, window=14):
            tp = (high + low + close) / 3
            mf = tp * volume
            positive_mf = mf.where(tp > tp.shift(1), 0)
            negative_mf = mf.where(tp < tp.shift(1), 0)
            positive_sum = positive_mf.rolling(window=window).sum()
            negative_sum = negative_mf.rolling(window=window).sum()
            mfr = positive_sum / negative_sum.replace(0, np.nan)
            return 100 - (100 / (1 + mfr))
        self.register("MFI", MFI_impl)
        
        self.register("WILLR", lambda high, low, close, window=14: -100 * (high.rolling(window=window).max() - close) / (high.rolling(window=window).max() - low.rolling(window=window).min()).replace(0, np.nan))
        
        def STOCH_K_impl(high, low, close, window=14):
            lowest_low = low.rolling(window=window).min()
            highest_high = high.rolling(window=window).max()
            return 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
        self.register("STOCH_K", STOCH_K_impl)
        
        def STOCH_D_impl(high, low, close, window=14, smooth=3):
            k = STOCH_K_impl(high, low, close, window)
            return k.rolling(window=smooth).mean()
        self.register("STOCH_D", STOCH_D_impl)
        
        def STOCHRSI_K_impl(x, window=14, smooth_k=3, smooth_d=3):
            rsi = RSI_impl(x, window)
            lowest_rsi = rsi.rolling(window=smooth_k).min()
            highest_rsi = rsi.rolling(window=smooth_k).max()
            stoch = 100 * (rsi - lowest_rsi) / (highest_rsi - lowest_rsi).replace(0, np.nan)
            return stoch.rolling(window=smooth_k).mean()
        self.register("STOCHRSI_K", STOCHRSI_K_impl)
        
        def STOCHRSI_D_impl(x, window=14, smooth_k=3, smooth_d=3):
            k = STOCHRSI_K_impl(x, window, smooth_k, smooth_d)
            return k.rolling(window=smooth_d).mean()
        self.register("STOCHRSI_D", STOCHRSI_D_impl)
        
        def BBANDS_UPPER_impl(x, window=20, num_std=2):
            sma = x.rolling(window=window).mean()
            std = x.rolling(window=window).std()
            return sma + num_std * std
        self.register("BBANDS_UPPER", BBANDS_UPPER_impl)
        
        def BBANDS_MIDDLE_impl(x, window=20):
            return x.rolling(window=window).mean()
        self.register("BBANDS_MIDDLE", BBANDS_MIDDLE_impl)
        
        def BBANDS_LOWER_impl(x, window=20, num_std=2):
            sma = x.rolling(window=window).mean()
            std = x.rolling(window=window).std()
            return sma - num_std * std
        self.register("BBANDS_LOWER", BBANDS_LOWER_impl)
        
        self.register("DEMA", lambda x, window: x.ewm(span=window, adjust=False).mean() * 2 - x.ewm(span=window*2, adjust=False).mean())
        self.register("TEMA", lambda x, window: 3 * x.ewm(span=window, adjust=False).mean() - 3 * x.ewm(span=window*2, adjust=False).mean() + x.ewm(span=window*3, adjust=False).mean())
        self.register("TRIX", lambda x, window: x.ewm(span=window, adjust=False).mean().ewm(span=window, adjust=False).mean().ewm(span=window, adjust=False).mean().pct_change() * 100)
        self.register("ROC", lambda x, window: (x / x.shift(window) - 1) * 100)
        self.register("ROCP", lambda x, window: (x - x.shift(window)) / x.shift(window))
        self.register("MOM", lambda x, window: x - x.shift(window))
        self.register("APO", lambda x, fast=12, slow=26: x.ewm(span=fast, adjust=False).mean() - x.ewm(span=slow, adjust=False).mean())
        self.register("PPO", lambda x, fast=12, slow=26: (x.ewm(span=fast, adjust=False).mean() - x.ewm(span=slow, adjust=False).mean()) / x.ewm(span=slow, adjust=False).mean() * 100)
        self.register("NATR", lambda high, low, close, window=14: ATR_impl(high, low, close, window) / close * 100)
        
        def PLUS_DI_impl(high, low, close, window=14):
            plus_dm = high.diff()
            minus_dm = -low.diff()
            plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
            tr = ATR_impl(high, low, close, 1)
            return 100 * plus_dm.rolling(window=window).mean() / tr.rolling(window=window).mean()
        self.register("PLUS_DI", PLUS_DI_impl)
        
        def MINUS_DI_impl(high, low, close, window=14):
            plus_dm = high.diff()
            minus_dm = -low.diff()
            minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
            tr = ATR_impl(high, low, close, 1)
            return 100 * minus_dm.rolling(window=window).mean() / tr.rolling(window=window).mean()
        self.register("MINUS_DI", MINUS_DI_impl)
        
        def DX_impl(high, low, close, window=14):
            plus_di = PLUS_DI_impl(high, low, close, window)
            minus_di = MINUS_DI_impl(high, low, close, window)
            return 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)
        self.register("DX", DX_impl)
        
        def AD_impl(high, low, close, volume):
            clv = ((close - low) - (high - close)) / (high - low).replace(0, np.nan)
            return volume * clv
        self.register("AD", AD_impl)
        
        def ADOSC_impl(high, low, close, volume, fast=3, slow=10):
            ad = AD_impl(high, low, close, volume)
            return ad.ewm(span=fast, adjust=False).mean() - ad.ewm(span=slow, adjust=False).mean()
        self.register("ADOSC", ADOSC_impl)
        
        def AROON_UP_impl(high, window=14):
            return high.rolling(window=window).apply(lambda x: (window - 1 - x.argmax()) / (window - 1) * 100, raw=True)
        self.register("AROON_UP", AROON_UP_impl)
        
        def AROON_DOWN_impl(low, window=14):
            return low.rolling(window=window).apply(lambda x: (window - 1 - x.argmin()) / (window - 1) * 100, raw=True)
        self.register("AROON_DOWN", AROON_DOWN_impl)
        
        def AROONOSC_impl(high, low, window=14):
            aroon_up = AROON_UP_impl(high, window)
            aroon_down = AROON_DOWN_impl(low, window)
            return aroon_up - aroon_down
        self.register("AROONOSC", AROONOSC_impl)
        
        def BOP_impl(open_price, high, low, close):
            return (close - open_price) / (high - low).replace(0, np.nan)
        self.register("BOP", BOP_impl)
        
        def ULTOSC_impl(high, low, close, period1=7, period2=14, period3=28):
            bp = close - low.rolling(window=period1).min()
            tr = high.rolling(window=period1).max() - low.rolling(window=period1).min()
            avg1 = bp.rolling(window=period1).sum() / tr.rolling(window=period1).sum()
            bp2 = close - low.rolling(window=period2).min()
            tr2 = high.rolling(window=period2).max() - low.rolling(window=period2).min()
            avg2 = bp2.rolling(window=period2).sum() / tr2.rolling(window=period2).sum()
            bp3 = close - low.rolling(window=period3).min()
            tr3 = high.rolling(window=period3).max() - low.rolling(window=period3).min()
            avg3 = bp3.rolling(window=period3).sum() / tr3.rolling(window=period3).sum()
            return 100 * (4 * avg1 + 2 * avg2 + avg3) / 7
        self.register("ULTOSC", ULTOSC_impl)
        
        def HT_TRENDLINE_impl(x):
            return x.ewm(span=10, adjust=False).mean()
        self.register("HT_TRENDLINE", HT_TRENDLINE_impl)
        
        def HT_TRENDMODE_impl(x):
            sma = x.rolling(window=30).mean()
            return (x > sma).astype(int)
        self.register("HT_TRENDMODE", HT_TRENDMODE_impl)
        
        def KAMA_impl(x, window=10, fast=2, slow=30):
            change = abs(x - x.shift(window))
            volatility = abs(x - x.shift(1)).rolling(window=window).sum()
            er = change / volatility.replace(0, np.nan)
            fast_sc = 2 / (fast + 1)
            slow_sc = 2 / (slow + 1)
            sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
            kama = x.copy()
            for i in range(window, len(x)):
                kama.iloc[i] = kama.iloc[i-1] + sc.iloc[i] * (x.iloc[i] - kama.iloc[i-1])
            return kama
        self.register("KAMA", KAMA_impl)
        
    def register(self, name: str, func: Callable):
        """
        注册算子
        
        Args:
            name: 算子名称
            func: 算子函数
        """
        self._operators[name] = func
    
    def get(self, name: str) -> Optional[Callable]:
        """获取算子"""
        return self._operators.get(name)
    
    def list_operators(self) -> List[str]:
        """列出所有算子"""
        return list(self._operators.keys())


class FormulaParser:
    """
    公式解析器
    
    解析因子公式表达式，支持变量、算子和数学运算。
    """
    
    def __init__(self, operator_registry: OperatorRegistry):
        """
        初始化公式解析器
        
        Args:
            operator_registry: 算子注册表
        """
        self.operators = operator_registry
        self._cache: Dict[str, Any] = {}
    
    def parse(self, formula: str) -> ast.AST:
        """
        解析公式
        
        Args:
            formula: 公式字符串
            
        Returns:
            AST: 抽象语法树
        """
        if formula in self._cache:
            return self._cache[formula]
        
        try:
            tree = ast.parse(formula, mode='eval')
            self._cache[formula] = tree
            return tree
        except SyntaxError as e:
            raise FactorException(f"公式语法错误: {formula}", details={"error": str(e)})
    
    def extract_variables(self, formula: str) -> List[str]:
        """
        提取公式中的变量名
        
        Args:
            formula: 公式字符串
            
        Returns:
            List[str]: 变量名列表
        """
        tree = self.parse(formula)
        variables = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if not self.operators.get(node.id):
                    variables.add(node.id)
        
        return sorted(list(variables))
    
    def validate_formula(self, formula: str) -> bool:
        """
        验证公式有效性
        
        Args:
            formula: 公式字符串
            
        Returns:
            bool: 是否有效
        """
        try:
            self.parse(formula)
            return True
        except Exception:
            return False


class FactorComputeContext:
    """
    因子计算上下文
    
    管理计算过程中的数据和变量。
    """
    
    def __init__(self, data: Dict[str, Any]):
        """
        初始化计算上下文
        
        Args:
            data: 数据字典，键为数据名，值为Series或DataFrame
        """
        self._data = data
        self._cache: Dict[str, Any] = {}
    
    def get(self, name: str) -> Optional[Any]:
        """获取数据"""
        if name in self._cache:
            return self._cache[name]
        
        data = self._data.get(name)
        if data is not None:
            if isinstance(data, pd.Series):
                return data
            if isinstance(data, pd.DataFrame):
                if name in data.columns:
                    return data[name]
                if name.lower() in [c.lower() for c in data.columns]:
                    for c in data.columns:
                        if c.lower() == name.lower():
                            return data[c]
        
        return data
    
    def set(self, name: str, value: Any):
        """设置数据"""
        self._cache[name] = value
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()


class FactorEngine:
    """
    因子计算引擎
    
    支持公式表达式解析、插件式因子扩展、批量并行计算和增量更新。
    """
    
    def __init__(
        self, 
        n_workers: int = 4,
        use_multiprocessing: bool = False
    ):
        """
        初始化因子计算引擎
        
        Args:
            n_workers: 工作进程/线程数
            use_multiprocessing: 是否使用多进程
        """
        self.n_workers = n_workers
        self.use_multiprocessing = use_multiprocessing
        self.operator_registry = OperatorRegistry()
        self.formula_parser = FormulaParser(self.operator_registry)
        self._registry = get_factor_registry()
        self._custom_factors: Dict[str, Callable] = {}
    
    def register_custom_factor(self, factor_id: str, compute_func: Callable):
        """
        注册自定义因子计算函数
        
        Args:
            factor_id: 因子ID
            compute_func: 计算函数
        """
        self._custom_factors[factor_id] = compute_func
    
    def register_operator(self, name: str, func: Callable):
        """
        注册自定义算子
        
        Args:
            name: 算子名称
            func: 算子函数
        """
        self.operator_registry.register(name, func)
    
    def compute_single(
        self,
        factor: Union[str, FactorMetadata],
        data: Dict[str, pd.DataFrame],
        **kwargs
    ) -> FactorComputeResult:
        """
        计算单个因子
        
        Args:
            factor: 因子ID或因子元数据
            data: 计算所需的数据字典
            **kwargs: 额外参数，可包含:
                - stock_code: 股票代码
                - date_series: 日期序列
                - original_df: 原始DataFrame
            
        Returns:
            FactorComputeResult: 计算结果
        """
        start_time = datetime.now()
        
        if isinstance(factor, str):
            factor_meta = self._registry.get(factor)
            if factor_meta is None:
                return FactorComputeResult(
                    success=False,
                    factor_id=factor,
                    error_message=f"因子不存在: {factor}"
                )
        else:
            factor_meta = factor
        
        factor_id = factor_meta.id
        
        try:
            if factor_id in self._custom_factors:
                result_df = self._custom_factors[factor_id](data, **kwargs)
            else:
                result_df = self._compute_by_formula(factor_meta, data, **kwargs)
            
            compute_time = (datetime.now() - start_time).total_seconds()
            
            stock_count = 0
            date_count = 0
            if result_df is not None and len(result_df) > 0:
                if 'stock_code' in result_df.columns:
                    stock_count = result_df['stock_code'].nunique()
                if 'date' in result_df.columns:
                    date_count = result_df['date'].nunique()
            
            return FactorComputeResult(
                success=True,
                factor_id=factor_id,
                data=result_df,
                compute_time=compute_time,
                stock_count=stock_count,
                date_count=date_count
            )
            
        except Exception as e:
            return FactorComputeResult(
                success=False,
                factor_id=factor_id,
                error_message=str(e)
            )
    
    def _compute_by_formula(
        self,
        factor: FactorMetadata,
        data: Dict[str, pd.DataFrame],
        **kwargs
    ) -> pd.DataFrame:
        """
        通过公式计算因子
        
        Args:
            factor: 因子元数据
            data: 数据字典
            **kwargs: 额外参数
            
        Returns:
            pd.DataFrame: 因子值DataFrame
        """
        formula = factor.formula
        params = {**factor.parameters, **kwargs}
        
        variables = self.formula_parser.extract_variables(formula)
        
        missing_vars = [v for v in variables if v not in data]
        if missing_vars:
            raise FactorException(
                f"缺少必要数据: {missing_vars}",
                factor_id=factor.id
            )
        
        context = FactorComputeContext(data)
        
        result = self._evaluate_formula(formula, context, params)
        
        sample_series = list(data.values())[0] if data else None
        
        if isinstance(result, pd.Series):
            result = result.to_frame('factor_value')
        
        if isinstance(result, np.ndarray):
            result = pd.DataFrame({'factor_value': result})
        
        if isinstance(result, pd.DataFrame):
            stock_code = kwargs.get('stock_code')
            date_series = kwargs.get('date_series')
            original_df = kwargs.get('original_df')
            
            if 'stock_code' not in result.columns:
                if stock_code is not None:
                    result['stock_code'] = stock_code
                elif original_df is not None and 'stock_code' in original_df.columns:
                    result['stock_code'] = original_df['stock_code'].values[:len(result)]
            
            if 'date' not in result.columns:
                if date_series is not None:
                    result['date'] = date_series.values[:len(result)]
                elif original_df is not None and 'date' in original_df.columns:
                    result['date'] = original_df['date'].values[:len(result)]
        
        return result
    
    def _evaluate_formula(
        self,
        formula: str,
        context: FactorComputeContext,
        params: Dict[str, Any]
    ) -> Any:
        """
        评估公式表达式
        
        Args:
            formula: 公式字符串
            context: 计算上下文
            params: 参数字典
            
        Returns:
            Any: 计算结果
        """
        # 检查是否是分号分隔的多行表达式
        if ';' in formula and '=' in formula:
            # 使用exec执行多行语句
            import pandas as pd
            import numpy as np
            
            # 获取df变量
            df = context.get('df')
            if df is None:
                # 尝试从data中构建df
                data_dict = {}
                for key, val in context._data.items():
                    data_dict[key] = val
                if data_dict:
                    df = pd.DataFrame(data_dict)
            
            if df is None:
                raise FactorException("无法获取DataFrame上下文")
            
            # 执行多行语句
            local_vars = {'df': df, 'pd': pd, 'np': np}
            exec(formula, local_vars, local_vars)
            
            # 返回最后一个表达式的结果
            # 假设最后一个语句是 df['factor_name']
            last_expr = formula.split(';')[-1].strip()
            if last_expr.startswith("df['"):
                factor_name = last_expr.split("'")[1]
                return df[factor_name]
            
            return None
        
        # 标准表达式解析
        tree = self.formula_parser.parse(formula)
        return self._eval_node(tree.body, context, params)
    
    def _eval_node(self, node: ast.AST, context: FactorComputeContext, params: Dict[str, Any]) -> Any:
        """递归评估AST节点"""
        if isinstance(node, ast.Constant):
            return node.value
        
        elif isinstance(node, ast.Num):
            return node.n
        
        elif isinstance(node, ast.Str):
            return node.s
        
        elif isinstance(node, ast.Name):
            name = node.id
            
            if name in params:
                return params[name]
            
            data_val = context.get(name)
            if data_val is not None:
                return data_val
            
            op_func = self.operator_registry.get(name)
            if op_func:
                return op_func
            
            return None
        
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, context, params)
            right = self._eval_node(node.right, context, params)
            
            ops = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.FloorDiv: operator.floordiv,
                ast.Mod: operator.mod,
                ast.Pow: operator.pow,
            }
            
            op_func = ops.get(type(node.op))
            if op_func:
                return op_func(left, right)
            raise FactorException(f"不支持的二元运算: {type(node.op)}")
        
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand, context, params)
            
            if isinstance(node.op, ast.USub):
                return -operand
            elif isinstance(node.op, ast.UAdd):
                return +operand
            elif isinstance(node.op, ast.Not):
                return not operand
            
            raise FactorException(f"不支持的一元运算: {type(node.op)}")
        
        elif isinstance(node, ast.Compare):
            left = self._eval_node(node.left, context, params)
            
            result = True
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, context, params)
                
                ops = {
                    ast.Eq: lambda a, b: a == b,
                    ast.NotEq: lambda a, b: a != b,
                    ast.Lt: lambda a, b: a < b,
                    ast.LtE: lambda a, b: a <= b,
                    ast.Gt: lambda a, b: a > b,
                    ast.GtE: lambda a, b: a >= b,
                }
                
                op_func = ops.get(type(op))
                if op_func:
                    if isinstance(result, bool) and result:
                        result = op_func(left, right)
                    else:
                        result = result & op_func(left, right) if isinstance(result, pd.Series) else op_func(left, right)
                left = right
            
            return result
        
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                obj = self._eval_node(node.func.value, context, params)
                method_name = node.func.attr
                method = getattr(obj, method_name, None)
                if method is None:
                    raise FactorException(f"对象没有方法: {method_name}")
                args = [self._eval_node(arg, context, params) for arg in node.args]
                kwargs = {
                    kw.arg: self._eval_node(kw.value, context, params)
                    for kw in node.keywords
                }
                return method(*args, **kwargs)
            
            func_name = node.func.id if isinstance(node.func, ast.Name) else None
            
            if func_name is None:
                raise FactorException(f"不支持的函数调用")
            
            func = self.operator_registry.get(func_name)
            if func is None:
                raise FactorException(f"未知算子: {func_name}")
            
            args = [self._eval_node(arg, context, params) for arg in node.args]
            kwargs = {
                kw.arg: self._eval_node(kw.value, context, params)
                for kw in node.keywords
            }
            
            return func(*args, **kwargs)
        
        elif isinstance(node, ast.Subscript):
            value = self._eval_node(node.value, context, params)
            slice_val = self._eval_node(node.slice, context, params)
            return value[slice_val]
        
        elif isinstance(node, ast.Attribute):
            value = self._eval_node(node.value, context, params)
            return getattr(value, node.attr)
        
        elif isinstance(node, ast.Index):
            return self._eval_node(node.value, context, params)
        
        elif isinstance(node, ast.Lambda):
            # 对于Lambda表达式，使用eval来执行
            import pandas as pd
            import numpy as np
            lambda_code = ast.unparse(node)
            return eval(lambda_code, {'pd': pd, 'np': np}, {})
        
        else:
            raise FactorException(f"不支持的AST节点类型: {type(node)}")
    
    def compute_batch(
        self,
        factor_ids: List[str],
        data: Dict[str, pd.DataFrame],
        parallel: bool = True
    ) -> Dict[str, FactorComputeResult]:
        """
        批量计算因子
        
        Args:
            factor_ids: 因子ID列表
            data: 数据字典
            parallel: 是否并行计算
            
        Returns:
            Dict[str, FactorComputeResult]: 计算结果字典
        """
        results = {}
        
        if parallel and len(factor_ids) > 1:
            executor_class = ProcessPoolExecutor if self.use_multiprocessing else ThreadPoolExecutor
            
            with executor_class(max_workers=self.n_workers) as executor:
                futures = {
                    executor.submit(self.compute_single, fid, data): fid
                    for fid in factor_ids
                }
                
                for future in futures:
                    fid = futures[future]
                    try:
                        results[fid] = future.result()
                    except Exception as e:
                        results[fid] = FactorComputeResult(
                            success=False,
                            factor_id=fid,
                            error_message=str(e)
                        )
        else:
            for fid in factor_ids:
                results[fid] = self.compute_single(fid, data)
        
        return results
    
    def compute_incremental(
        self,
        factor_id: str,
        data: Dict[str, pd.DataFrame],
        previous_data: Optional[pd.DataFrame] = None,
        lookback: int = 252
    ) -> FactorComputeResult:
        """
        增量计算因子
        
        Args:
            factor_id: 因子ID
            data: 新数据
            previous_data: 历史因子数据
            lookback: 回看天数
            
        Returns:
            FactorComputeResult: 计算结果
        """
        factor_meta = self._registry.get(factor_id)
        if factor_meta is None:
            return FactorComputeResult(
                success=False,
                factor_id=factor_id,
                error_message=f"因子不存在: {factor_id}"
            )
        
        result = self.compute_single(factor_meta, data)
        
        if result.success and previous_data is not None and result.data is not None:
            combined = pd.concat([previous_data, result.data], ignore_index=True)
            
            if 'date' in combined.columns:
                combined['date'] = pd.to_datetime(combined['date'])
                combined = combined.sort_values('date')
                
                unique_dates = combined['date'].unique()
                if len(unique_dates) > lookback:
                    cutoff_date = unique_dates[-lookback]
                    combined = combined[combined['date'] >= cutoff_date]
            
            result.data = combined
        
        return result
    
    def get_required_data(self, factor_id: str) -> List[str]:
        """
        获取因子计算所需的数据字段
        
        Args:
            factor_id: 因子ID
            
        Returns:
            List[str]: 数据字段列表
        """
        factor = self._registry.get(factor_id)
        if factor is None:
            return []
        
        return self.formula_parser.extract_variables(factor.formula)
    
    def validate_factor_data(self, factor_id: str, data: Dict[str, pd.DataFrame]) -> bool:
        """
        验证数据是否满足因子计算需求
        
        Args:
            factor_id: 因子ID
            data: 数据字典
            
        Returns:
            bool: 是否满足
        """
        required = self.get_required_data(factor_id)
        return all(field in data for field in required)


_default_engine: Optional[FactorEngine] = None


def get_factor_engine(n_workers: int = 4, use_multiprocessing: bool = False) -> FactorEngine:
    """获取全局因子计算引擎实例"""
    global _default_engine
    if _default_engine is None:
        _default_engine = FactorEngine(n_workers, use_multiprocessing)
    return _default_engine


def reset_factor_engine():
    """重置全局因子计算引擎"""
    global _default_engine
    _default_engine = None
