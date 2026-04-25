"""
AI增强信号生成器

将AI信号整合到现有信号生成流程，支持：
1. 传统因子信号 + AI信号融合
2. 信号加权与集成
3. 自动选择最佳信号源
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import pandas as pd
import numpy as np

from ..signal import (
    SignalGenerator,
    SignalGenerationResult,
    GeneratedSignal,
    get_signal_generator,
    get_signal_registry
)
from ..factor import get_factor_engine, get_factor_registry
from ..infrastructure.logging import get_logger

logger = get_logger("signal.ai_enhanced")


class SignalSourceType(Enum):
    """信号来源类型"""
    TRADITIONAL = "traditional"
    AI = "ai"
    ML = "ml"
    ENSEMBLE = "ensemble"


@dataclass
class EnhancedSignalConfig:
    """增强信号配置"""
    enable_ai_signal: bool = True
    enable_ml_signal: bool = True
    enable_traditional_signal: bool = True
    ensemble_method: str = "weighted_average"
    ai_weight: float = 0.4
    ml_weight: float = 0.3
    traditional_weight: float = 0.3
    min_signal_confidence: float = 0.5
    signal_agreement_threshold: float = 0.6


@dataclass
class SignalEnsembleResult:
    """信号集成结果"""
    success: bool
    signals: Dict[str, float] = field(default_factory=dict)
    sources: Dict[str, Dict[str, float]] = field(default_factory=dict)
    confidence: float = 0.0
    agreement_score: float = 0.0
    method: str = "ensemble"
    error_message: Optional[str] = None


class AISignalIntegrator:
    """
    AI信号整合器
    
    整合传统信号、ML信号和AI深度学习信号
    """
    
    def __init__(self, config: EnhancedSignalConfig = None):
        self.config = config or EnhancedSignalConfig()
        self._traditional_generator = get_signal_generator()
        self._factor_registry = get_factor_registry()
        self._signal_registry = get_signal_registry()
        
        self._ai_generators = {}
        self._ml_generators = {}
        
        self._load_generators()
    
    def _load_generators(self):
        """加载已训练的生成器"""
        try:
            from ..signal import get_ml_signal_generator
            self._ml_generators['default'] = get_ml_signal_generator()
        except Exception as e:
            logger.warning(f"加载ML信号生成器失败: {e}")
        
        try:
            from ..signal import create_ai_signal_generator
            model_path = os.path.join("models", "ai_signals", "lstm_signal.pt")
            if os.path.exists(model_path):
                self._ai_generators['lstm'] = create_ai_signal_generator(agent_path=model_path)
        except Exception as e:
            logger.warning(f"加载AI信号生成器失败: {e}")
    
    def generate_traditional_signals(
        self,
        factor_values: pd.DataFrame,
        date: str
    ) -> Dict[str, float]:
        """生成传统因子信号"""
        if not self.config.enable_traditional_signal:
            return {}
        
        try:
            result = self._traditional_generator.generate(
                factor_values=factor_values,
                date=date
            )
            
            if result.success:
                return {s.stock_code: s.strength for s in result.signals}
        except Exception as e:
            logger.error(f"传统信号生成失败: {e}")
        
        return {}
    
    def generate_ai_signals(
        self,
        factor_values: pd.DataFrame,
        market_data: pd.DataFrame = None,
        date: str = None
    ) -> Dict[str, float]:
        """生成AI深度学习信号"""
        if not self.config.enable_ai_signal or not self._ai_generators:
            return {}
        
        all_signals = {}
        
        for name, generator in self._ai_generators.items():
            try:
                result = generator.generate(
                    factor_values=factor_values,
                    market_data=market_data,
                    date=date
                )
                
                if result.success:
                    for stock, score in result.scores.items():
                        if stock not in all_signals:
                            all_signals[stock] = []
                        all_signals[stock].append(score)
            except Exception as e:
                logger.warning(f"AI信号生成失败 [{name}]: {e}")
        
        averaged_signals = {}
        for stock, scores in all_signals.items():
            averaged_signals[stock] = np.mean(scores)
        
        return averaged_signals
    
    def generate_ml_signals(
        self,
        factor_values: pd.DataFrame,
        date: str = None
    ) -> Dict[str, float]:
        """生成ML机器学习信号"""
        if not self.config.enable_ml_signal or not self._ml_generators:
            return {}
        
        all_signals = {}
        
        for name, generator in self._ml_generators.items():
            try:
                trained_models = getattr(generator, '_trained_models', {})
                
                for signal_id in trained_models:
                    result = generator.generate_signal(signal_id, factor_values)
                    
                    if result.success:
                        for stock, score in result.scores.items():
                            if stock not in all_signals:
                                all_signals[stock] = []
                            all_signals[stock].append(score)
            except Exception as e:
                logger.warning(f"ML信号生成失败 [{name}]: {e}")
        
        averaged_signals = {}
        for stock, scores in all_signals.items():
            averaged_signals[stock] = np.mean(scores)
        
        return averaged_signals
    
    def ensemble_signals(
        self,
        traditional: Dict[str, float],
        ai: Dict[str, float],
        ml: Dict[str, float]
    ) -> SignalEnsembleResult:
        """集成多源信号"""
        all_stocks = set(traditional.keys()) | set(ai.keys()) | set(ml.keys())
        
        if not all_stocks:
            return SignalEnsembleResult(
                success=False,
                error_message="没有可用的信号"
            )
        
        method = self.config.ensemble_method
        
        if method == "weighted_average":
            signals = self._weighted_average_ensemble(all_stocks, traditional, ai, ml)
        elif method == "rank_average":
            signals = self._rank_average_ensemble(all_stocks, traditional, ai, ml)
        elif method == "voting":
            signals = self._voting_ensemble(all_stocks, traditional, ai, ml)
        else:
            signals = self._weighted_average_ensemble(all_stocks, traditional, ai, ml)
        
        agreement_score = self._calculate_agreement(traditional, ai, ml)
        
        return SignalEnsembleResult(
            success=True,
            signals=signals,
            sources={
                "traditional": traditional,
                "ai": ai,
                "ml": ml
            },
            confidence=self._calculate_confidence(signals, agreement_score),
            agreement_score=agreement_score,
            method=method
        )
    
    def _weighted_average_ensemble(
        self,
        all_stocks: set,
        traditional: Dict[str, float],
        ai: Dict[str, float],
        ml: Dict[str, float]
    ) -> Dict[str, float]:
        """加权平均集成"""
        signals = {}
        
        w_t = self.config.traditional_weight
        w_a = self.config.ai_weight
        w_m = self.config.ml_weight
        
        total_weight = w_t + w_a + w_m
        if total_weight > 0:
            w_t, w_a, w_m = w_t / total_weight, w_a / total_weight, w_m / total_weight
        
        for stock in all_stocks:
            t_score = traditional.get(stock, 0)
            a_score = ai.get(stock, 0)
            m_score = ml.get(stock, 0)
            
            available_weights = []
            scores = []
            
            if stock in traditional:
                available_weights.append(w_t)
                scores.append(t_score)
            if stock in ai:
                available_weights.append(w_a)
                scores.append(a_score)
            if stock in ml:
                available_weights.append(w_m)
                scores.append(m_score)
            
            if available_weights:
                norm_weights = [w / sum(available_weights) for w in available_weights]
                signals[stock] = sum(s * w for s, w in zip(scores, norm_weights))
        
        return signals
    
    def _rank_average_ensemble(
        self,
        all_stocks: set,
        traditional: Dict[str, float],
        ai: Dict[str, float],
        ml: Dict[str, float]
    ) -> Dict[str, float]:
        """排序平均集成"""
        def to_ranks(scores: Dict[str, float]) -> Dict[str, float]:
            if not scores:
                return {}
            sorted_stocks = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
            n = len(sorted_stocks)
            return {s: (n - i) / n for i, s in enumerate(sorted_stocks)}
        
        t_ranks = to_ranks(traditional)
        a_ranks = to_ranks(ai)
        m_ranks = to_ranks(ml)
        
        signals = {}
        for stock in all_stocks:
            ranks = []
            if stock in t_ranks:
                ranks.append(t_ranks[stock])
            if stock in a_ranks:
                ranks.append(a_ranks[stock])
            if stock in m_ranks:
                ranks.append(m_ranks[stock])
            
            if ranks:
                signals[stock] = np.mean(ranks)
        
        return signals
    
    def _voting_ensemble(
        self,
        all_stocks: set,
        traditional: Dict[str, float],
        ai: Dict[str, float],
        ml: Dict[str, float]
    ) -> Dict[str, float]:
        """投票集成"""
        signals = {}
        
        for stock in all_stocks:
            votes = []
            
            if stock in traditional:
                votes.append(1 if traditional[stock] > 0 else -1)
            if stock in ai:
                votes.append(1 if ai[stock] > 0 else -1)
            if stock in ml:
                votes.append(1 if ml[stock] > 0 else -1)
            
            if votes:
                signals[stock] = sum(votes) / len(votes)
        
        return signals
    
    def _calculate_agreement(
        self,
        traditional: Dict[str, float],
        ai: Dict[str, float],
        ml: Dict[str, float]
    ) -> float:
        """计算信号一致性"""
        common_stocks = set(traditional.keys()) & set(ai.keys()) & set(ml.keys())
        
        if len(common_stocks) < 3:
            return 0.0
        
        t_arr = np.array([traditional[s] for s in common_stocks])
        a_arr = np.array([ai[s] for s in common_stocks])
        m_arr = np.array([ml[s] for s in common_stocks])
        
        t_arr = (t_arr - t_arr.mean()) / (t_arr.std() + 1e-8)
        a_arr = (a_arr - a_arr.mean()) / (a_arr.std() + 1e-8)
        m_arr = (m_arr - m_arr.mean()) / (m_arr.std() + 1e-8)
        
        corr_ta = np.corrcoef(t_arr, a_arr)[0, 1]
        corr_tm = np.corrcoef(t_arr, m_arr)[0, 1]
        corr_am = np.corrcoef(a_arr, m_arr)[0, 1]
        
        return (corr_ta + corr_tm + corr_am) / 3
    
    def _calculate_confidence(
        self,
        signals: Dict[str, float],
        agreement: float
    ) -> float:
        """计算信号置信度"""
        if not signals:
            return 0.0
        
        signal_values = np.array(list(signals.values()))
        signal_strength = np.abs(signal_values).mean()
        
        signal_consistency = 1 - np.std(signal_values) / (np.abs(signal_values).mean() + 1e-8)
        signal_consistency = max(0, min(1, signal_consistency))
        
        confidence = 0.4 * signal_strength + 0.3 * signal_consistency + 0.3 * max(0, agreement)
        
        return min(1.0, confidence)
    
    def generate_enhanced_signals(
        self,
        factor_values: pd.DataFrame,
        market_data: pd.DataFrame = None,
        date: str = None,
        top_n: int = 30
    ) -> SignalEnsembleResult:
        """
        生成增强信号（整合所有信号源）
        
        Args:
            factor_values: 因子值DataFrame
            market_data: 市场数据
            date: 日期
            top_n: 返回前N个信号
            
        Returns:
            SignalEnsembleResult: 集成信号结果
        """
        date = date or datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"开始生成增强信号: {date}")
        
        traditional = self.generate_traditional_signals(factor_values, date)
        logger.info(f"传统信号: {len(traditional)} 个")
        
        ai = self.generate_ai_signals(factor_values, market_data, date)
        logger.info(f"AI信号: {len(ai)} 个")
        
        ml = self.generate_ml_signals(factor_values, date)
        logger.info(f"ML信号: {len(ml)} 个")
        
        result = self.ensemble_signals(traditional, ai, ml)
        
        if result.success:
            sorted_signals = sorted(
                result.signals.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]
            
            result.signals = dict(sorted_signals)
            logger.info(f"集成信号: {len(result.signals)} 个, 置信度: {result.confidence:.2f}")
        
        return result


class EnhancedSignalGenerator:
    """
    增强信号生成器
    
    替代原有SignalGenerator，支持AI/ML信号融合
    """
    
    def __init__(self, config: EnhancedSignalConfig = None):
        self.config = config or EnhancedSignalConfig()
        self.integrator = AISignalIntegrator(self.config)
        self._traditional_generator = get_signal_generator()
    
    def generate(
        self,
        factor_values: pd.DataFrame,
        market_data: pd.DataFrame = None,
        date: str = None,
        use_ensemble: bool = True
    ) -> SignalGenerationResult:
        """
        生成信号
        
        Args:
            factor_values: 因子值DataFrame
            market_data: 市场数据
            date: 日期
            use_ensemble: 是否使用集成信号
            
        Returns:
            SignalGenerationResult
        """
        date = date or datetime.now().strftime("%Y-%m-%d")
        
        if use_ensemble:
            ensemble_result = self.integrator.generate_enhanced_signals(
                factor_values=factor_values,
                market_data=market_data,
                date=date
            )
            
            if ensemble_result.success:
                signals = []
                for stock_code, strength in ensemble_result.signals.items():
                    signals.append(GeneratedSignal(
                        signal_id=f"ensemble_{date}",
                        stock_code=stock_code,
                        date=date,
                        strength=strength,
                        direction="buy" if strength > 0 else "sell",
                        confidence=ensemble_result.confidence,
                        source="ensemble"
                    ))
                
                return SignalGenerationResult(
                    success=True,
                    signals=signals,
                    signal_type="ensemble",
                    selected_stocks=list(ensemble_result.signals.keys()),
                    scores=ensemble_result.signals,
                    details={
                        "sources": ensemble_result.sources,
                        "agreement": ensemble_result.agreement_score,
                        "confidence": ensemble_result.confidence
                    }
                )
        
        return self._traditional_generator.generate(factor_values, date)


def create_enhanced_signal_generator(
    config: EnhancedSignalConfig = None
) -> EnhancedSignalGenerator:
    """创建增强信号生成器"""
    return EnhancedSignalGenerator(config)


_enhanced_generator = None


def get_enhanced_signal_generator(
    config: EnhancedSignalConfig = None
) -> EnhancedSignalGenerator:
    """获取增强信号生成器单例"""
    global _enhanced_generator
    if _enhanced_generator is None:
        _enhanced_generator = EnhancedSignalGenerator(config)
    return _enhanced_generator
