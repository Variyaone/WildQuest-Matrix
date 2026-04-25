"""
滚动回测框架（Walk-Forward Analysis）

解决时间窗口偏差，验证策略参数稳定性和样本外表现。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import date
from enum import Enum
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class WalkForwardMode(Enum):
    """滚动模式"""
    ANCHORED = "anchored"          # 锚定模式：训练窗口起点固定
    ROLLING = "rolling"             # 滚动模式：训练窗口随时间滚动
    EXPANDING = "expanding"         # 扩展模式：训练窗口逐渐扩大


@dataclass
class WalkForwardWindow:
    """滚动窗口"""
    window_id: int
    train_start: date
    train_end: date
    test_start: date
    test_end: date
    train_dates: List[date]
    test_dates: List[date]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'window_id': self.window_id,
            'train_start': self.train_start.isoformat(),
            'train_end': self.train_end.isoformat(),
            'test_start': self.test_start.isoformat(),
            'test_end': self.test_end.isoformat(),
            'train_days': len(self.train_dates),
            'test_days': len(self.test_dates)
        }


@dataclass
class WalkForwardResult:
    """滚动回测结果"""
    window: WalkForwardWindow
    train_metrics: Dict[str, float]
    test_metrics: Dict[str, float]
    params: Dict[str, Any]
    train_ic: float
    test_ic: float
    ic_decay: float
    train_sharpe: float
    test_sharpe: float
    sharpe_decay: float
    is_stable: bool
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'window': self.window.to_dict(),
            'train_metrics': self.train_metrics,
            'test_metrics': self.test_metrics,
            'params': self.params,
            'train_ic': self.train_ic,
            'test_ic': self.test_ic,
            'ic_decay': self.ic_decay,
            'train_sharpe': self.train_sharpe,
            'test_sharpe': self.test_sharpe,
            'sharpe_decay': self.sharpe_decay,
            'is_stable': self.is_stable,
            'warnings': self.warnings
        }


@dataclass
class WalkForwardSummary:
    """滚动回测汇总"""
    total_windows: int
    stable_windows: int
    stability_ratio: float
    avg_train_ic: float
    avg_test_ic: float
    avg_ic_decay: float
    avg_train_sharpe: float
    avg_test_sharpe: float
    avg_sharpe_decay: float
    ic_consistency: float
    sharpe_consistency: float
    overall_passed: bool
    window_results: List[WalkForwardResult]
    warnings: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_windows': self.total_windows,
            'stable_windows': self.stable_windows,
            'stability_ratio': self.stability_ratio,
            'avg_train_ic': self.avg_train_ic,
            'avg_test_ic': self.avg_test_ic,
            'avg_ic_decay': self.avg_ic_decay,
            'avg_train_sharpe': self.avg_train_sharpe,
            'avg_test_sharpe': self.avg_test_sharpe,
            'avg_sharpe_decay': self.avg_sharpe_decay,
            'ic_consistency': self.ic_consistency,
            'sharpe_consistency': self.sharpe_consistency,
            'overall_passed': self.overall_passed,
            'window_results': [r.to_dict() for r in self.window_results],
            'warnings': self.warnings
        }


class WalkForwardBacktester:
    """
    滚动回测器
    
    执行Walk-Forward分析，验证策略稳定性。
    """
    
    def __init__(
        self,
        train_window: int = 252,
        test_window: int = 63,
        step_size: int = 21,
        mode: WalkForwardMode = WalkForwardMode.ROLLING,
        ic_decay_threshold: float = 0.3,
        sharpe_decay_threshold: float = 0.4,
        min_stability_ratio: float = 0.6
    ):
        """
        初始化滚动回测器
        
        Args:
            train_window: 训练窗口（交易日）
            test_window: 测试窗口（交易日）
            step_size: 滚动步长（交易日）
            mode: 滚动模式
            ic_decay_threshold: IC衰减阈值
            sharpe_decay_threshold: 夏普衰减阈值
            min_stability_ratio: 最小稳定性比例
        """
        self.train_window = train_window
        self.test_window = test_window
        self.step_size = step_size
        self.mode = mode
        self.ic_decay_threshold = ic_decay_threshold
        self.sharpe_decay_threshold = sharpe_decay_threshold
        self.min_stability_ratio = min_stability_ratio
    
    def generate_windows(
        self,
        dates: List[date]
    ) -> List[WalkForwardWindow]:
        """
        生成滚动窗口
        
        Args:
            dates: 日期列表
            
        Returns:
            List[WalkForwardWindow]: 窗口列表
        """
        if len(dates) < self.train_window + self.test_window:
            logger.warning(f"日期数量不足: {len(dates)} < {self.train_window + self.test_window}")
            return []
        
        windows = []
        window_id = 0
        
        if self.mode == WalkForwardMode.ROLLING:
            start_idx = 0
            while start_idx + self.train_window + self.test_window <= len(dates):
                train_start_idx = start_idx
                train_end_idx = start_idx + self.train_window
                test_start_idx = train_end_idx
                test_end_idx = test_start_idx + self.test_window
                
                window = WalkForwardWindow(
                    window_id=window_id,
                    train_start=dates[train_start_idx],
                    train_end=dates[train_end_idx - 1],
                    test_start=dates[test_start_idx],
                    test_end=dates[test_end_idx - 1],
                    train_dates=dates[train_start_idx:train_end_idx],
                    test_dates=dates[test_start_idx:test_end_idx]
                )
                windows.append(window)
                
                window_id += 1
                start_idx += self.step_size
        
        elif self.mode == WalkForwardMode.ANCHORED:
            start_idx = self.train_window
            while start_idx + self.test_window <= len(dates):
                train_start_idx = 0
                train_end_idx = start_idx
                test_start_idx = start_idx
                test_end_idx = start_idx + self.test_window
                
                window = WalkForwardWindow(
                    window_id=window_id,
                    train_start=dates[train_start_idx],
                    train_end=dates[train_end_idx - 1],
                    test_start=dates[test_start_idx],
                    test_end=dates[test_end_idx - 1],
                    train_dates=dates[train_start_idx:train_end_idx],
                    test_dates=dates[test_start_idx:test_end_idx]
                )
                windows.append(window)
                
                window_id += 1
                start_idx += self.step_size
        
        elif self.mode == WalkForwardMode.EXPANDING:
            start_idx = self.train_window
            while start_idx + self.test_window <= len(dates):
                train_start_idx = 0
                train_end_idx = start_idx
                test_start_idx = start_idx
                test_end_idx = start_idx + self.test_window
                
                window = WalkForwardWindow(
                    window_id=window_id,
                    train_start=dates[train_start_idx],
                    train_end=dates[train_end_idx - 1],
                    test_start=dates[test_start_idx],
                    test_end=dates[test_end_idx - 1],
                    train_dates=dates[train_start_idx:train_end_idx],
                    test_dates=dates[test_start_idx:test_end_idx]
                )
                windows.append(window)
                
                window_id += 1
                start_idx += self.step_size
        
        logger.info(f"生成 {len(windows)} 个滚动窗口")
        return windows
    
    def run_walk_forward(
        self,
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        backtest_func: Callable,
        optimize_func: Optional[Callable] = None,
        date_col: str = "date",
        factor_col: str = "factor_value",
        return_col: str = "forward_return",
        stock_col: str = "stock_code"
    ) -> WalkForwardSummary:
        """
        执行滚动回测
        
        Args:
            factor_df: 因子数据
            return_df: 收益数据
            backtest_func: 回测函数
            optimize_func: 参数优化函数（可选）
            date_col: 日期列名
            factor_col: 因子列名
            return_col: 收益列名
            stock_col: 股票代码列名
            
        Returns:
            WalkForwardSummary: 滚动回测汇总
        """
        dates = sorted(factor_df[date_col].unique())
        windows = self.generate_windows(dates)
        
        if not windows:
            return WalkForwardSummary(
                total_windows=0,
                stable_windows=0,
                stability_ratio=0.0,
                avg_train_ic=0.0,
                avg_test_ic=0.0,
                avg_ic_decay=0.0,
                avg_train_sharpe=0.0,
                avg_test_sharpe=0.0,
                avg_sharpe_decay=0.0,
                ic_consistency=0.0,
                sharpe_consistency=0.0,
                overall_passed=False,
                window_results=[],
                warnings=["无法生成滚动窗口：数据不足"]
            )
        
        window_results: List[WalkForwardResult] = []
        
        for window in windows:
            logger.info(f"处理窗口 {window.window_id + 1}/{len(windows)}")
            
            train_factor = factor_df[factor_df[date_col].isin(window.train_dates)]
            train_return = return_df[return_df[date_col].isin(window.train_dates)]
            
            test_factor = factor_df[factor_df[date_col].isin(window.test_dates)]
            test_return = return_df[return_df[date_col].isin(window.test_dates)]
            
            params = {}
            if optimize_func is not None:
                try:
                    params = optimize_func(train_factor, train_return)
                except Exception as e:
                    logger.warning(f"窗口 {window.window_id} 参数优化失败: {e}")
            
            try:
                train_result = backtest_func(
                    train_factor, train_return, params
                )
                test_result = backtest_func(
                    test_factor, test_return, params
                )
                
                train_ic = train_result.get('ic_mean', 0.0)
                test_ic = test_result.get('ic_mean', 0.0)
                train_sharpe = train_result.get('sharpe_ratio', 0.0)
                test_sharpe = test_result.get('sharpe_ratio', 0.0)
                
                ic_decay = abs(train_ic - test_ic) / abs(train_ic) if abs(train_ic) > 1e-6 else 0.0
                sharpe_decay = abs(train_sharpe - test_sharpe) / abs(train_sharpe) if abs(train_sharpe) > 1e-6 else 0.0
                
                is_stable = (
                    ic_decay < self.ic_decay_threshold and
                    sharpe_decay < self.sharpe_decay_threshold and
                    test_ic * train_ic > 0
                )
                
                warnings = []
                if ic_decay >= self.ic_decay_threshold:
                    warnings.append(f"IC衰减过大: {ic_decay:.1%}")
                if sharpe_decay >= self.sharpe_decay_threshold:
                    warnings.append(f"夏普衰减过大: {sharpe_decay:.1%}")
                if test_ic * train_ic < 0:
                    warnings.append("训练集和测试集IC方向相反")
                
                window_result = WalkForwardResult(
                    window=window,
                    train_metrics=train_result,
                    test_metrics=test_result,
                    params=params,
                    train_ic=train_ic,
                    test_ic=test_ic,
                    ic_decay=ic_decay,
                    train_sharpe=train_sharpe,
                    test_sharpe=test_sharpe,
                    sharpe_decay=sharpe_decay,
                    is_stable=is_stable,
                    warnings=warnings
                )
                
                window_results.append(window_result)
                
            except Exception as e:
                logger.error(f"窗口 {window.window_id} 回测失败: {e}")
                continue
        
        if not window_results:
            return WalkForwardSummary(
                total_windows=len(windows),
                stable_windows=0,
                stability_ratio=0.0,
                avg_train_ic=0.0,
                avg_test_ic=0.0,
                avg_ic_decay=0.0,
                avg_train_sharpe=0.0,
                avg_test_sharpe=0.0,
                avg_sharpe_decay=0.0,
                ic_consistency=0.0,
                sharpe_consistency=0.0,
                overall_passed=False,
                window_results=[],
                warnings=["所有窗口回测失败"]
            )
        
        stable_windows = sum(1 for r in window_results if r.is_stable)
        stability_ratio = stable_windows / len(window_results)
        
        train_ics = [r.train_ic for r in window_results]
        test_ics = [r.test_ic for r in window_results]
        ic_decays = [r.ic_decay for r in window_results]
        
        train_sharpes = [r.train_sharpe for r in window_results]
        test_sharpes = [r.test_sharpe for r in window_results]
        sharpe_decays = [r.sharpe_decay for r in window_results]
        
        ic_consistency = sum(1 for r in window_results if r.train_ic * r.test_ic > 0) / len(window_results)
        sharpe_consistency = sum(1 for r in window_results if r.train_sharpe * r.test_sharpe > 0) / len(window_results)
        
        overall_passed = stability_ratio >= self.min_stability_ratio
        
        warnings = []
        if stability_ratio < self.min_stability_ratio:
            warnings.append(f"稳定性比例不足: {stability_ratio:.1%} < {self.min_stability_ratio:.1%}")
        if np.mean(ic_decays) > self.ic_decay_threshold:
            warnings.append(f"平均IC衰减过大: {np.mean(ic_decays):.1%}")
        if np.mean(sharpe_decays) > self.sharpe_decay_threshold:
            warnings.append(f"平均夏普衰减过大: {np.mean(sharpe_decays):.1%}")
        
        summary = WalkForwardSummary(
            total_windows=len(window_results),
            stable_windows=stable_windows,
            stability_ratio=stability_ratio,
            avg_train_ic=np.mean(train_ics),
            avg_test_ic=np.mean(test_ics),
            avg_ic_decay=np.mean(ic_decays),
            avg_train_sharpe=np.mean(train_sharpes),
            avg_test_sharpe=np.mean(test_sharpes),
            avg_sharpe_decay=np.mean(sharpe_decays),
            ic_consistency=ic_consistency,
            sharpe_consistency=sharpe_consistency,
            overall_passed=overall_passed,
            window_results=window_results,
            warnings=warnings
        )
        
        logger.info(
            f"滚动回测完成: {stable_windows}/{len(window_results)} 窗口稳定, "
            f"稳定性 {stability_ratio:.1%}, {'通过' if overall_passed else '未通过'}"
        )
        
        return summary
    
    def validate_parameter_stability(
        self,
        window_results: List[WalkForwardResult]
    ) -> Dict[str, Any]:
        """
        验证参数稳定性
        
        Args:
            window_results: 窗口结果列表
            
        Returns:
            Dict: 参数稳定性分析结果
        """
        if not window_results:
            return {'stable': False, 'message': '无窗口结果'}
        
        all_params = [r.params for r in window_results if r.params]
        
        if not all_params:
            return {'stable': True, 'message': '无参数需要验证'}
        
        param_keys = set()
        for params in all_params:
            param_keys.update(params.keys())
        
        stability_report = {}
        
        for key in param_keys:
            values = [p.get(key) for p in all_params if key in p]
            
            if not values:
                continue
            
            if isinstance(values[0], (int, float)):
                mean_val = np.mean(values)
                std_val = np.std(values)
                cv = std_val / abs(mean_val) if abs(mean_val) > 1e-6 else 0.0
                
                stability_report[key] = {
                    'type': 'numeric',
                    'mean': mean_val,
                    'std': std_val,
                    'cv': cv,
                    'stable': cv < 0.3,
                    'values': values
                }
            else:
                unique_values = set(values)
                stability_report[key] = {
                    'type': 'categorical',
                    'unique_count': len(unique_values),
                    'stable': len(unique_values) <= 3,
                    'values': values
                }
        
        stable_params = sum(1 for r in stability_report.values() if r['stable'])
        total_params = len(stability_report)
        
        return {
            'stable': stable_params == total_params,
            'stable_params': stable_params,
            'total_params': total_params,
            'stability_ratio': stable_params / total_params if total_params > 0 else 1.0,
            'details': stability_report
        }


def create_walk_forward_backtester(
    train_window: int = 252,
    test_window: int = 63,
    step_size: int = 21,
    mode: str = "rolling"
) -> WalkForwardBacktester:
    """创建滚动回测器"""
    mode_enum = WalkForwardMode(mode)
    return WalkForwardBacktester(
        train_window=train_window,
        test_window=test_window,
        step_size=step_size,
        mode=mode_enum
    )
