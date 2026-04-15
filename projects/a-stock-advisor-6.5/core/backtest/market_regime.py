"""
市场环境感知回测器

强制按市场环境（牛市/熊市/震荡）分别回测，验证策略鲁棒性。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import date
from enum import Enum
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """市场环境"""
    BULL = "bull"               # 牛市
    BEAR = "bear"               # 熊市
    SIDEWAYS = "sideways"       # 震荡市
    CRISIS = "crisis"           # 危机
    RECOVERY = "recovery"       # 复苏


@dataclass
class MarketPeriod:
    """市场时期"""
    regime: MarketRegime
    start_date: date
    end_date: date
    cumulative_return: float
    volatility: float
    max_drawdown: float
    trading_days: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'regime': self.regime.value,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'cumulative_return': self.cumulative_return,
            'volatility': self.volatility,
            'max_drawdown': self.max_drawdown,
            'trading_days': self.trading_days
        }


@dataclass
class RegimeBacktestResult:
    """市场环境回测结果"""
    regime: MarketRegime
    period: MarketPeriod
    backtest_metrics: Dict[str, float]
    passed: bool
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'regime': self.regime.value,
            'period': self.period.to_dict(),
            'backtest_metrics': self.backtest_metrics,
            'passed': self.passed,
            'warnings': self.warnings
        }


@dataclass
class MarketAwareBacktestSummary:
    """市场环境感知回测汇总"""
    total_periods: int
    passed_periods: int
    pass_rate: float
    regime_results: Dict[MarketRegime, List[RegimeBacktestResult]]
    consistency_score: float
    overall_passed: bool
    warnings: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_periods': self.total_periods,
            'passed_periods': self.passed_periods,
            'pass_rate': self.pass_rate,
            'regime_results': {
                regime.value: [r.to_dict() for r in results]
                for regime, results in self.regime_results.items()
            },
            'consistency_score': self.consistency_score,
            'overall_passed': self.overall_passed,
            'warnings': self.warnings
        }


class MarketRegimeClassifier:
    """市场环境分类器"""
    
    def __init__(
        self,
        bull_threshold: float = 0.20,
        bear_threshold: float = -0.20,
        volatility_threshold: float = 0.02,
        lookback_window: int = 60
    ):
        """
        初始化市场环境分类器
        
        Args:
            bull_threshold: 牛市阈值
            bear_threshold: 熊市阈值
            volatility_threshold: 波动率阈值
            lookback_window: 回看窗口
        """
        self.bull_threshold = bull_threshold
        self.bear_threshold = bear_threshold
        self.volatility_threshold = volatility_threshold
        self.lookback_window = lookback_window
    
    def classify_regime(
        self,
        index_returns: pd.Series,
        volatility: Optional[float] = None
    ) -> MarketRegime:
        """
        分类市场环境
        
        Args:
            index_returns: 指数收益率序列
            volatility: 波动率（可选）
            
        Returns:
            MarketRegime: 市场环境
        """
        cumulative_return = (1 + index_returns).prod() - 1
        
        if volatility is None:
            volatility = index_returns.std() * np.sqrt(252)
        
        if cumulative_return >= self.bull_threshold:
            return MarketRegime.BULL
        elif cumulative_return <= self.bear_threshold:
            if volatility > self.volatility_threshold * 2:
                return MarketRegime.CRISIS
            else:
                return MarketRegime.BEAR
        else:
            if volatility > self.volatility_threshold * 1.5:
                return MarketRegime.CRISIS
            elif cumulative_return > 0:
                return MarketRegime.RECOVERY
            else:
                return MarketRegime.SIDEWAYS
    
    def identify_market_periods(
        self,
        index_data: pd.DataFrame,
        date_col: str = "date",
        return_col: str = "pct_chg",
        min_period_days: int = 20
    ) -> List[MarketPeriod]:
        """
        识别市场时期
        
        Args:
            index_data: 指数数据
            date_col: 日期列名
            return_col: 收益率列名
            min_period_days: 最小时期天数
            
        Returns:
            List[MarketPeriod]: 市场时期列表
        """
        index_data = index_data.copy()
        index_data[date_col] = pd.to_datetime(index_data[date_col])
        index_data = index_data.sort_values(date_col)
        
        if return_col in index_data.columns:
            if index_data[return_col].abs().max() > 1:
                index_data[return_col] = index_data[return_col] / 100
        
        index_data['rolling_return'] = index_data[return_col].rolling(
            window=self.lookback_window, min_periods=self.lookback_window // 2
        ).apply(lambda x: (1 + x).prod() - 1)
        
        index_data['rolling_volatility'] = index_data[return_col].rolling(
            window=self.lookback_window, min_periods=self.lookback_window // 2
        ).std() * np.sqrt(252)
        
        index_data['regime'] = index_data.apply(
            lambda row: self.classify_regime(
                pd.Series([row['rolling_return']]),
                row['rolling_volatility']
            ) if pd.notna(row['rolling_return']) else None,
            axis=1
        )
        
        periods = []
        current_regime = None
        period_start = None
        period_returns = []
        
        for idx, row in index_data.iterrows():
            if pd.isna(row['regime']):
                continue
            
            if current_regime is None:
                current_regime = row['regime']
                period_start = row[date_col].date()
                period_returns = [row[return_col] if pd.notna(row[return_col]) else 0]
            elif row['regime'] != current_regime:
                if len(period_returns) >= min_period_days:
                    period_end = index_data.loc[idx, date_col].date()
                    
                    cumulative_return = (1 + pd.Series(period_returns)).prod() - 1
                    volatility = pd.Series(period_returns).std() * np.sqrt(252)
                    
                    cummax = (1 + pd.Series(period_returns)).cumprod()
                    max_drawdown = (cummax / cummax.cummax() - 1).min()
                    
                    periods.append(MarketPeriod(
                        regime=current_regime,
                        start_date=period_start,
                        end_date=period_end,
                        cumulative_return=cumulative_return,
                        volatility=volatility,
                        max_drawdown=max_drawdown,
                        trading_days=len(period_returns)
                    ))
                
                current_regime = row['regime']
                period_start = row[date_col].date()
                period_returns = [row[return_col] if pd.notna(row[return_col]) else 0]
            else:
                period_returns.append(row[return_col] if pd.notna(row[return_col]) else 0)
        
        if current_regime is not None and len(period_returns) >= min_period_days:
            period_end = index_data.iloc[-1][date_col].date()
            
            cumulative_return = (1 + pd.Series(period_returns)).prod() - 1
            volatility = pd.Series(period_returns).std() * np.sqrt(252)
            
            cummax = (1 + pd.Series(period_returns)).cumprod()
            max_drawdown = (cummax / cummax.cummax() - 1).min()
            
            periods.append(MarketPeriod(
                regime=current_regime,
                start_date=period_start,
                end_date=period_end,
                cumulative_return=cumulative_return,
                volatility=volatility,
                max_drawdown=max_drawdown,
                trading_days=len(period_returns)
            ))
        
        logger.info(f"识别到 {len(periods)} 个市场时期")
        return periods


class MarketAwareBacktester:
    """
    市场环境感知回测器
    
    强制按市场环境分别回测。
    """
    
    def __init__(
        self,
        classifier: Optional[MarketRegimeClassifier] = None,
        min_ic_threshold: float = 0.02,
        min_sharpe_threshold: float = 0.5,
        consistency_threshold: float = 0.7
    ):
        """
        初始化市场环境感知回测器
        
        Args:
            classifier: 市场环境分类器
            min_ic_threshold: 最小IC阈值
            min_sharpe_threshold: 最小夏普阈值
            consistency_threshold: 一致性阈值
        """
        self.classifier = classifier or MarketRegimeClassifier()
        self.min_ic_threshold = min_ic_threshold
        self.min_sharpe_threshold = min_sharpe_threshold
        self.consistency_threshold = consistency_threshold
    
    def run_regime_aware_backtest(
        self,
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        index_data: pd.DataFrame,
        backtest_func: callable,
        date_col: str = "date",
        factor_col: str = "factor_value",
        return_col: str = "forward_return",
        stock_col: str = "stock_code"
    ) -> MarketAwareBacktestSummary:
        """
        执行市场环境感知回测
        
        Args:
            factor_df: 因子数据
            return_df: 收益数据
            index_data: 指数数据
            backtest_func: 回测函数
            date_col: 日期列名
            factor_col: 因子列名
            return_col: 收益列名
            stock_col: 股票代码列名
            
        Returns:
            MarketAwareBacktestSummary: 回测汇总
        """
        periods = self.classifier.identify_market_periods(index_data, date_col)
        
        if not periods:
            return MarketAwareBacktestSummary(
                total_periods=0,
                passed_periods=0,
                pass_rate=0.0,
                regime_results={},
                consistency_score=0.0,
                overall_passed=False,
                warnings=["无法识别市场时期"]
            )
        
        regime_results: Dict[MarketRegime, List[RegimeBacktestResult]] = {}
        
        for period in periods:
            period_factor = factor_df[
                (factor_df[date_col] >= period.start_date) &
                (factor_df[date_col] <= period.end_date)
            ]
            period_return = return_df[
                (return_df[date_col] >= period.start_date) &
                (return_df[date_col] <= period.end_date)
            ]
            
            if len(period_factor) == 0 or len(period_return) == 0:
                continue
            
            try:
                backtest_metrics = backtest_func(period_factor, period_return)
                
                ic = backtest_metrics.get('ic_mean', 0.0)
                sharpe = backtest_metrics.get('sharpe_ratio', 0.0)
                
                passed = (
                    abs(ic) >= self.min_ic_threshold and
                    sharpe >= self.min_sharpe_threshold
                )
                
                warnings = []
                if abs(ic) < self.min_ic_threshold:
                    warnings.append(f"IC不足: {abs(ic):.4f} < {self.min_ic_threshold}")
                if sharpe < self.min_sharpe_threshold:
                    warnings.append(f"夏普不足: {sharpe:.2f} < {self.min_sharpe_threshold}")
                
                result = RegimeBacktestResult(
                    regime=period.regime,
                    period=period,
                    backtest_metrics=backtest_metrics,
                    passed=passed,
                    warnings=warnings
                )
                
                if period.regime not in regime_results:
                    regime_results[period.regime] = []
                regime_results[period.regime].append(result)
                
            except Exception as e:
                logger.error(f"时期 {period.start_date} ~ {period.end_date} 回测失败: {e}")
                continue
        
        total_periods = sum(len(results) for results in regime_results.values())
        passed_periods = sum(sum(1 for r in results if r.passed) for results in regime_results.values())
        pass_rate = passed_periods / total_periods if total_periods > 0 else 0.0
        
        consistency_scores = []
        for regime, results in regime_results.items():
            if len(results) > 1:
                ics = [r.backtest_metrics.get('ic_mean', 0) for r in results]
                ic_consistency = 1 - (np.std(ics) / (np.mean(np.abs(ics)) + 1e-6))
                consistency_scores.append(max(0, ic_consistency))
        
        consistency_score = np.mean(consistency_scores) if consistency_scores else 0.0
        
        overall_passed = pass_rate >= self.consistency_threshold and consistency_score >= 0.5
        
        warnings = []
        if pass_rate < self.consistency_threshold:
            warnings.append(f"通过率不足: {pass_rate:.1%} < {self.consistency_threshold:.1%}")
        if consistency_score < 0.5:
            warnings.append(f"一致性不足: {consistency_score:.2f} < 0.5")
        
        return MarketAwareBacktestSummary(
            total_periods=total_periods,
            passed_periods=passed_periods,
            pass_rate=pass_rate,
            regime_results=regime_results,
            consistency_score=consistency_score,
            overall_passed=overall_passed,
            warnings=warnings
        )


def create_market_aware_backtester(
    min_ic_threshold: float = 0.02,
    min_sharpe_threshold: float = 0.5
) -> MarketAwareBacktester:
    """创建市场环境感知回测器"""
    return MarketAwareBacktester(
        min_ic_threshold=min_ic_threshold,
        min_sharpe_threshold=min_sharpe_threshold
    )
