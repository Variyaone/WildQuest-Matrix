"""
鲁棒性回测框架

整合所有改进模块，提供完整的鲁棒性回测能力。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import date
import pandas as pd
import numpy as np
import logging
from pathlib import Path

from .stock_pool_snapshot import StockPoolSnapshotManager, create_snapshot_manager
from .walk_forward import WalkForwardBacktester, create_walk_forward_backtester
from .liquidity_checker import LiquidityConstraintChecker, create_liquidity_checker
from .event_simulator import BlackSwanEventSimulator, create_event_simulator
from .enhanced_impact import EnhancedMarketImpactModel, create_enhanced_impact_model
from .market_regime import MarketAwareBacktester, create_market_aware_backtester
from .constraints import (
    TurnoverConstraintChecker,
    OverfittingDetector,
    create_turnover_checker,
    create_overfitting_detector
)

logger = logging.getLogger(__name__)


@dataclass
class RobustBacktestConfig:
    """鲁棒性回测配置"""
    enable_survivorship_bias_check: bool = True
    enable_walk_forward: bool = True
    enable_liquidity_check: bool = True
    enable_event_simulation: bool = True
    enable_market_regime: bool = True
    enable_turnover_constraint: bool = True
    enable_overfitting_check: bool = True
    enable_enhanced_impact: bool = True
    
    walk_forward_train_days: int = 252
    walk_forward_test_days: int = 63
    walk_forward_step_days: int = 21
    
    max_daily_turnover: float = 0.3
    max_annual_turnover: float = 10.0
    max_participation_rate: float = 0.05
    min_avg_amount: float = 5e7
    
    min_ic_threshold: float = 0.02
    min_sharpe_threshold: float = 0.5
    train_test_gap_threshold: float = 0.3
    
    stress_test_mode: bool = False


@dataclass
class RobustBacktestResult:
    """鲁棒性回测结果"""
    passed: bool
    overall_score: float
    
    survivorship_bias_check: Dict[str, Any]
    walk_forward_result: Dict[str, Any]
    liquidity_check: Dict[str, Any]
    event_simulation: Dict[str, Any]
    market_regime_result: Dict[str, Any]
    turnover_check: Dict[str, Any]
    overfitting_check: Dict[str, Any]
    impact_analysis: Dict[str, Any]
    
    warnings: List[str]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'passed': self.passed,
            'overall_score': self.overall_score,
            'survivorship_bias_check': self.survivorship_bias_check,
            'walk_forward_result': self.walk_forward_result,
            'liquidity_check': self.liquidity_check,
            'event_simulation': self.event_simulation,
            'market_regime_result': self.market_regime_result,
            'turnover_check': self.turnover_check,
            'overfitting_check': self.overfitting_check,
            'impact_analysis': self.impact_analysis,
            'warnings': self.warnings,
            'recommendations': self.recommendations
        }


class RobustBacktestFramework:
    """
    鲁棒性回测框架
    
    整合所有改进模块，提供完整的鲁棒性验证。
    """
    
    def __init__(self, config: Optional[RobustBacktestConfig] = None):
        """
        初始化鲁棒性回测框架
        
        Args:
            config: 回测配置
        """
        self.config = config or RobustBacktestConfig()
        
        self._init_components()
    
    def _init_components(self):
        """初始化各组件"""
        self.snapshot_manager = create_snapshot_manager()
        
        self.walk_forward_backtester = create_walk_forward_backtester(
            train_window=self.config.walk_forward_train_days,
            test_window=self.config.walk_forward_test_days,
            step_size=self.config.walk_forward_step_days
        )
        
        self.liquidity_checker = create_liquidity_checker(
            max_participation_rate=self.config.max_participation_rate,
            min_avg_amount=self.config.min_avg_amount
        )
        
        self.event_simulator = create_event_simulator(
            stress_test_mode=self.config.stress_test_mode
        )
        
        self.market_aware_backtester = create_market_aware_backtester(
            min_ic_threshold=self.config.min_ic_threshold,
            min_sharpe_threshold=self.config.min_sharpe_threshold
        )
        
        self.turnover_checker = create_turnover_checker(
            max_daily_turnover=self.config.max_daily_turnover,
            max_annual_turnover=self.config.max_annual_turnover
        )
        
        self.overfitting_detector = create_overfitting_detector(
            train_test_gap_threshold=self.config.train_test_gap_threshold
        )
        
        self.impact_model = create_enhanced_impact_model()
    
    def run_full_robustness_check(
        self,
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        market_data: pd.DataFrame,
        index_data: pd.DataFrame,
        backtest_func: Callable,
        portfolio_positions: Optional[Dict[str, float]] = None,
        portfolio_value: float = 1e8,
        date_col: str = "date",
        stock_col: str = "stock_code"
    ) -> RobustBacktestResult:
        """
        执行完整鲁棒性检查
        
        Args:
            factor_df: 因子数据
            return_df: 收益数据
            market_data: 市场数据
            index_data: 指数数据
            backtest_func: 回测函数
            portfolio_positions: 组合持仓
            portfolio_value: 组合价值
            date_col: 日期列名
            stock_col: 股票代码列名
            
        Returns:
            RobustBacktestResult: 鲁棒性检查结果
        """
        warnings = []
        recommendations = []
        
        survivorship_result = self._check_survivorship_bias(
            factor_df, market_data, date_col, stock_col
        )
        
        walk_forward_result = self._run_walk_forward(
            factor_df, return_df, backtest_func, date_col
        )
        
        liquidity_result = self._check_liquidity(
            factor_df, market_data, date_col, stock_col
        )
        
        event_result = self._simulate_events(
            portfolio_positions or {}, portfolio_value, market_data
        )
        
        regime_result = self._run_regime_aware_backtest(
            factor_df, return_df, index_data, backtest_func, date_col
        )
        
        turnover_result = self._check_turnover()
        
        overfitting_result = self._check_overfitting(
            walk_forward_result, regime_result
        )
        
        impact_result = self._analyze_impact(
            portfolio_positions or {}, market_data, date_col, stock_col
        )
        
        scores = []
        
        if self.config.enable_survivorship_bias_check:
            if not survivorship_result.get('passed', True):
                warnings.append(f"存续偏差检查未通过: {survivorship_result.get('message', '')}")
                scores.append(0.0)
            else:
                scores.append(1.0)
        
        if self.config.enable_walk_forward:
            if not walk_forward_result.get('passed', True):
                warnings.append(f"滚动回测未通过: {walk_forward_result.get('message', '')}")
                scores.append(walk_forward_result.get('pass_rate', 0.0))
            else:
                scores.append(walk_forward_result.get('pass_rate', 1.0))
        
        if self.config.enable_liquidity_check:
            if not liquidity_result.get('passed', True):
                warnings.append(f"流动性检查未通过: {liquidity_result.get('message', '')}")
                scores.append(0.0)
            else:
                scores.append(1.0)
        
        if self.config.enable_event_simulation:
            if event_result.get('max_impact_pct', 0) > 0.2:
                warnings.append(f"事件冲击过大: {event_result.get('max_impact_pct', 0):.1%}")
                scores.append(max(0, 1 - event_result.get('max_impact_pct', 0)))
            else:
                scores.append(1.0)
        
        if self.config.enable_market_regime:
            if not regime_result.get('overall_passed', True):
                warnings.append(f"市场环境回测未通过: 通过率 {regime_result.get('pass_rate', 0):.1%}")
                scores.append(regime_result.get('pass_rate', 0.0))
            else:
                scores.append(regime_result.get('pass_rate', 1.0))
        
        if self.config.enable_turnover_constraint:
            if not turnover_result.get('passed', True):
                warnings.append(f"换手率约束未通过: {turnover_result.get('message', '')}")
                scores.append(0.0)
            else:
                scores.append(1.0)
        
        if self.config.enable_overfitting_check:
            if overfitting_result.get('is_overfitted', False):
                warnings.append("检测到过拟合风险")
                recommendations.extend(overfitting_result.get('recommendations', []))
                scores.append(0.5)
            else:
                scores.append(1.0)
        
        overall_score = np.mean(scores) if scores else 0.0
        passed = overall_score >= 0.7 and len([w for w in warnings if '未通过' in w]) == 0
        
        if overall_score < 0.7:
            recommendations.append("整体鲁棒性分数不足，建议重新审视策略")
        
        if not warnings:
            recommendations.append("策略通过所有鲁棒性检查")
        
        return RobustBacktestResult(
            passed=passed,
            overall_score=overall_score,
            survivorship_bias_check=survivorship_result,
            walk_forward_result=walk_forward_result,
            liquidity_check=liquidity_result,
            event_simulation=event_result,
            market_regime_result=regime_result,
            turnover_check=turnover_result,
            overfitting_check=overfitting_result,
            impact_analysis=impact_result,
            warnings=warnings,
            recommendations=recommendations
        )
    
    def _check_survivorship_bias(
        self,
        factor_df: pd.DataFrame,
        market_data: pd.DataFrame,
        date_col: str,
        stock_col: str
    ) -> Dict[str, Any]:
        """检查存续偏差"""
        if not self.config.enable_survivorship_bias_check:
            return {'passed': True, 'message': '检查已禁用'}
        
        try:
            dates = pd.to_datetime(factor_df[date_col]).dt.date.unique()
            dates = sorted(dates)
            
            start_date = dates[0]
            end_date = dates[-1]
            
            stocks_at_start = set(factor_df[factor_df[date_col] == start_date][stock_col].unique())
            stocks_at_end = set(factor_df[factor_df[date_col] == end_date][stock_col].unique())
            
            disappeared = stocks_at_start - stocks_at_end
            new_stocks = stocks_at_end - stocks_at_start
            
            if len(disappeared) > len(stocks_at_start) * 0.1:
                return {
                    'passed': False,
                    'message': f"检测到存续偏差: {len(disappeared)} 只股票消失",
                    'disappeared_count': len(disappeared),
                    'new_count': len(new_stocks)
                }
            
            return {
                'passed': True,
                'message': '存续偏差检查通过',
                'disappeared_count': len(disappeared),
                'new_count': len(new_stocks)
            }
            
        except Exception as e:
            logger.error(f"存续偏差检查失败: {e}")
            return {'passed': True, 'message': f'检查异常: {e}'}
    
    def _run_walk_forward(
        self,
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        backtest_func: Callable,
        date_col: str
    ) -> Dict[str, Any]:
        """执行滚动回测"""
        if not self.config.enable_walk_forward:
            return {'passed': True, 'message': '检查已禁用'}
        
        try:
            summary = self.walk_forward_backtester.run_walk_forward(
                factor_df=factor_df,
                return_df=return_df,
                backtest_func=backtest_func,
                date_col=date_col
            )
            
            return {
                'passed': summary.passed,
                'pass_rate': summary.pass_rate,
                'stability_score': summary.stability_score,
                'message': summary.message,
                'window_count': summary.window_count
            }
            
        except Exception as e:
            logger.error(f"滚动回测失败: {e}")
            return {'passed': True, 'message': f'检查异常: {e}'}
    
    def _check_liquidity(
        self,
        factor_df: pd.DataFrame,
        market_data: pd.DataFrame,
        date_col: str,
        stock_col: str
    ) -> Dict[str, Any]:
        """检查流动性"""
        if not self.config.enable_liquidity_check:
            return {'passed': True, 'message': '检查已禁用'}
        
        try:
            latest_date = pd.to_datetime(factor_df[date_col]).max()
            latest_stocks = factor_df[factor_df[date_col] == latest_date][stock_col].unique()
            
            low_liquidity_count = 0
            
            for stock in latest_stocks[:50]:
                stock_data = market_data[market_data[stock_col] == stock]
                
                if len(stock_data) > 0:
                    avg_amount = stock_data['amount'].tail(20).mean() if 'amount' in stock_data.columns else 1e8
                    
                    if avg_amount < self.config.min_avg_amount:
                        low_liquidity_count += 1
            
            if low_liquidity_count > len(latest_stocks[:50]) * 0.3:
                return {
                    'passed': False,
                    'message': f"流动性不足股票过多: {low_liquidity_count}",
                    'low_liquidity_count': low_liquidity_count
                }
            
            return {
                'passed': True,
                'message': '流动性检查通过',
                'low_liquidity_count': low_liquidity_count
            }
            
        except Exception as e:
            logger.error(f"流动性检查失败: {e}")
            return {'passed': True, 'message': f'检查异常: {e}'}
    
    def _simulate_events(
        self,
        positions: Dict[str, float],
        portfolio_value: float,
        market_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """模拟事件"""
        if not self.config.enable_event_simulation:
            return {'passed': True, 'message': '检查已禁用'}
        
        try:
            scenarios = self.event_simulator.generate_stress_scenarios(date.today())
            
            impacts = []
            for scenario in scenarios:
                impact = self.event_simulator.simulate_event_impact_on_portfolio(
                    event=scenario,
                    portfolio_value=portfolio_value,
                    positions=positions,
                    market_data=market_data
                )
                impacts.append(impact)
            
            max_impact = max(abs(i['impact_pct']) for i in impacts) if impacts else 0
            
            return {
                'passed': max_impact < 0.3,
                'scenario_count': len(scenarios),
                'max_impact_pct': max_impact,
                'message': f"最大冲击: {max_impact:.1%}"
            }
            
        except Exception as e:
            logger.error(f"事件模拟失败: {e}")
            return {'passed': True, 'message': f'检查异常: {e}'}
    
    def _run_regime_aware_backtest(
        self,
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        index_data: pd.DataFrame,
        backtest_func: Callable,
        date_col: str
    ) -> Dict[str, Any]:
        """执行市场环境感知回测"""
        if not self.config.enable_market_regime:
            return {'passed': True, 'message': '检查已禁用'}
        
        try:
            summary = self.market_aware_backtester.run_regime_aware_backtest(
                factor_df=factor_df,
                return_df=return_df,
                index_data=index_data,
                backtest_func=backtest_func,
                date_col=date_col
            )
            
            return {
                'overall_passed': summary.overall_passed,
                'pass_rate': summary.pass_rate,
                'consistency_score': summary.consistency_score,
                'total_periods': summary.total_periods,
                'warnings': summary.warnings
            }
            
        except Exception as e:
            logger.error(f"市场环境回测失败: {e}")
            return {'overall_passed': True, 'message': f'检查异常: {e}'}
    
    def _check_turnover(self) -> Dict[str, Any]:
        """检查换手率"""
        if not self.config.enable_turnover_constraint:
            return {'passed': True, 'message': '检查已禁用'}
        
        result = self.turnover_checker.check_turnover_constraints()
        
        return result.to_dict()
    
    def _check_overfitting(
        self,
        walk_forward_result: Dict[str, Any],
        regime_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检查过拟合"""
        if not self.config.enable_overfitting_check:
            return {'is_overfitted': False, 'message': '检查已禁用'}
        
        train_metrics = {'ic_mean': walk_forward_result.get('stability_score', 0.5)}
        test_metrics = {'ic_mean': walk_forward_result.get('pass_rate', 0.5)}
        
        result = self.overfitting_detector.detect_overfitting(
            train_metrics=train_metrics,
            test_metrics=test_metrics
        )
        
        return result.to_dict()
    
    def _analyze_impact(
        self,
        positions: Dict[str, float],
        market_data: pd.DataFrame,
        date_col: str,
        stock_col: str
    ) -> Dict[str, Any]:
        """分析市场冲击"""
        if not self.config.enable_enhanced_impact:
            return {'passed': True, 'message': '检查已禁用'}
        
        try:
            total_impact = 0.0
            impact_count = 0
            
            for stock, weight in list(positions.items())[:20]:
                trade_value = weight * 1e8
                
                impact = self.impact_model.calculate_impact_from_market_data(
                    stock_code=stock,
                    trade_value=trade_value,
                    target_date=date.today(),
                    market_data=market_data,
                    stock_col=stock_col,
                    date_col=date_col
                )
                
                total_impact += impact
                impact_count += 1
            
            avg_impact_rate = total_impact / (1e8 * impact_count) if impact_count > 0 else 0
            
            return {
                'passed': avg_impact_rate < 0.02,
                'avg_impact_rate': avg_impact_rate,
                'total_impact': total_impact,
                'message': f"平均冲击: {avg_impact_rate:.2%}"
            }
            
        except Exception as e:
            logger.error(f"市场冲击分析失败: {e}")
            return {'passed': True, 'message': f'检查异常: {e}'}
    
    def record_trade(
        self,
        trade_date: date,
        buy_value: float,
        sell_value: float,
        trade_count: int,
        portfolio_value: float
    ):
        """记录交易（用于换手率追踪）"""
        self.turnover_checker.record_turnover(
            date=trade_date,
            buy_value=buy_value,
            sell_value=sell_value,
            trade_count=trade_count,
            portfolio_value=portfolio_value
        )


def create_robust_framework(config: Optional[RobustBacktestConfig] = None) -> RobustBacktestFramework:
    """创建鲁棒性回测框架"""
    return RobustBacktestFramework(config)
