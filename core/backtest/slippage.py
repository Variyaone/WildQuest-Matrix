"""
滑点模型

模拟交易中的滑点效应。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any
import numpy as np
import pandas as pd


class SlippageType(Enum):
    """滑点类型"""
    FIXED = "fixed"
    PERCENTAGE = "percentage"
    VOLUME_WEIGHTED = "volume_weighted"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    MARKET_IMPACT = "market_impact"


@dataclass
class SlippageResult:
    """滑点计算结果"""
    original_price: float
    adjusted_price: float
    slippage_amount: float
    slippage_rate: float
    slippage_type: str
    details: Dict[str, Any]


class BaseSlippageModel(ABC):
    """滑点模型基类"""
    
    @abstractmethod
    def calculate_slippage(
        self,
        price: float,
        volume: float,
        direction: str,
        market_data: Optional[Dict[str, Any]] = None
    ) -> SlippageResult:
        """
        计算滑点
        
        Args:
            price: 原始价格
            volume: 交易量
            direction: 交易方向 (buy/sell)
            market_data: 市场数据
            
        Returns:
            SlippageResult: 滑点计算结果
        """
        pass


class FixedSlippageModel(BaseSlippageModel):
    """固定滑点模型"""
    
    def __init__(self, slippage_rate: float = 0.001):
        """
        初始化固定滑点模型
        
        Args:
            slippage_rate: 固定滑点率
        """
        self.slippage_rate = slippage_rate
    
    def calculate_slippage(
        self,
        price: float,
        volume: float,
        direction: str,
        market_data: Optional[Dict[str, Any]] = None
    ) -> SlippageResult:
        """计算固定滑点"""
        slippage_amount = price * self.slippage_rate
        
        if direction == 'buy':
            adjusted_price = price + slippage_amount
        else:
            adjusted_price = price - slippage_amount
        
        return SlippageResult(
            original_price=price,
            adjusted_price=adjusted_price,
            slippage_amount=slippage_amount,
            slippage_rate=self.slippage_rate,
            slippage_type=SlippageType.FIXED.value,
            details={'fixed_rate': self.slippage_rate}
        )


class PercentageSlippageModel(BaseSlippageModel):
    """百分比滑点模型"""
    
    def __init__(self, base_rate: float = 0.001, volume_factor: float = 0.0001):
        """
        初始化百分比滑点模型
        
        Args:
            base_rate: 基础滑点率
            volume_factor: 成交量因子
        """
        self.base_rate = base_rate
        self.volume_factor = volume_factor
    
    def calculate_slippage(
        self,
        price: float,
        volume: float,
        direction: str,
        market_data: Optional[Dict[str, Any]] = None
    ) -> SlippageResult:
        """计算百分比滑点"""
        volume_adj = volume * self.volume_factor if volume > 0 else 0
        total_rate = self.base_rate + volume_adj
        slippage_amount = price * total_rate
        
        if direction == 'buy':
            adjusted_price = price + slippage_amount
        else:
            adjusted_price = price - slippage_amount
        
        return SlippageResult(
            original_price=price,
            adjusted_price=adjusted_price,
            slippage_amount=slippage_amount,
            slippage_rate=total_rate,
            slippage_type=SlippageType.PERCENTAGE.value,
            details={
                'base_rate': self.base_rate,
                'volume_factor': self.volume_factor,
                'volume_adjustment': volume_adj
            }
        )


class VolumeWeightedSlippageModel(BaseSlippageModel):
    """成交量加权滑点模型"""
    
    def __init__(self, base_rate: float = 0.0005, volume_threshold: float = 100000):
        """
        初始化成交量加权滑点模型
        
        Args:
            base_rate: 基础滑点率
            volume_threshold: 成交量阈值
        """
        self.base_rate = base_rate
        self.volume_threshold = volume_threshold
    
    def calculate_slippage(
        self,
        price: float,
        volume: float,
        direction: str,
        market_data: Optional[Dict[str, Any]] = None
    ) -> SlippageResult:
        """计算成交量加权滑点"""
        market_data = market_data or {}
        avg_volume = market_data.get('avg_volume', self.volume_threshold)
        
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
        adjusted_rate = self.base_rate * (1 + np.log1p(volume_ratio))
        
        slippage_amount = price * adjusted_rate
        
        if direction == 'buy':
            adjusted_price = price + slippage_amount
        else:
            adjusted_price = price - slippage_amount
        
        return SlippageResult(
            original_price=price,
            adjusted_price=adjusted_price,
            slippage_amount=slippage_amount,
            slippage_rate=adjusted_rate,
            slippage_type=SlippageType.VOLUME_WEIGHTED.value,
            details={
                'base_rate': self.base_rate,
                'volume_ratio': volume_ratio,
                'avg_volume': avg_volume
            }
        )


class VolatilityAdjustedSlippageModel(BaseSlippageModel):
    """波动率调整滑点模型"""
    
    def __init__(self, base_rate: float = 0.001, volatility_multiplier: float = 2.0):
        """
        初始化波动率调整滑点模型
        
        Args:
            base_rate: 基础滑点率
            volatility_multiplier: 波动率乘数
        """
        self.base_rate = base_rate
        self.volatility_multiplier = volatility_multiplier
    
    def calculate_slippage(
        self,
        price: float,
        volume: float,
        direction: str,
        market_data: Optional[Dict[str, Any]] = None
    ) -> SlippageResult:
        """计算波动率调整滑点"""
        market_data = market_data or {}
        volatility = market_data.get('volatility', 0.02)
        
        volatility_adj = volatility * self.volatility_multiplier
        total_rate = self.base_rate + volatility_adj
        slippage_amount = price * total_rate
        
        if direction == 'buy':
            adjusted_price = price + slippage_amount
        else:
            adjusted_price = price - slippage_amount
        
        return SlippageResult(
            original_price=price,
            adjusted_price=adjusted_price,
            slippage_amount=slippage_amount,
            slippage_rate=total_rate,
            slippage_type=SlippageType.VOLATILITY_ADJUSTED.value,
            details={
                'base_rate': self.base_rate,
                'volatility': volatility,
                'volatility_adjustment': volatility_adj
            }
        )


class MarketImpactSlippageModel(BaseSlippageModel):
    """市场冲击滑点模型"""
    
    def __init__(
        self,
        base_rate: float = 0.0005,
        impact_coefficient: float = 0.1,
        decay_factor: float = 0.5
    ):
        """
        初始化市场冲击滑点模型
        
        Args:
            base_rate: 基础滑点率
            impact_coefficient: 冲击系数
            decay_factor: 衰减因子
        """
        self.base_rate = base_rate
        self.impact_coefficient = impact_coefficient
        self.decay_factor = decay_factor
    
    def calculate_slippage(
        self,
        price: float,
        volume: float,
        direction: str,
        market_data: Optional[Dict[str, Any]] = None
    ) -> SlippageResult:
        """计算市场冲击滑点"""
        market_data = market_data or {}
        avg_volume = market_data.get('avg_volume', 100000)
        market_cap = market_data.get('market_cap', 1e9)
        
        participation_rate = volume / avg_volume if avg_volume > 0 else 0.01
        
        market_impact = self.impact_coefficient * np.sqrt(participation_rate)
        size_adjustment = np.log10(market_cap / 1e9) * self.decay_factor if market_cap > 0 else 0
        
        total_rate = self.base_rate + market_impact - size_adjustment
        total_rate = max(total_rate, 0.0001)
        
        slippage_amount = price * total_rate
        
        if direction == 'buy':
            adjusted_price = price + slippage_amount
        else:
            adjusted_price = price - slippage_amount
        
        return SlippageResult(
            original_price=price,
            adjusted_price=adjusted_price,
            slippage_amount=slippage_amount,
            slippage_rate=total_rate,
            slippage_type=SlippageType.MARKET_IMPACT.value,
            details={
                'base_rate': self.base_rate,
                'participation_rate': participation_rate,
                'market_impact': market_impact,
                'size_adjustment': size_adjustment
            }
        )


class SlippageModel:
    """
    滑点模型管理器
    
    统一管理不同的滑点模型。
    """
    
    _models: Dict[str, BaseSlippageModel] = {}
    
    @classmethod
    def register(cls, name: str, model: BaseSlippageModel):
        """注册滑点模型"""
        cls._models[name] = model
    
    @classmethod
    def get(cls, name: str) -> Optional[BaseSlippageModel]:
        """获取滑点模型"""
        return cls._models.get(name)
    
    @classmethod
    def create(
        cls,
        slippage_type: SlippageType = SlippageType.PERCENTAGE,
        **kwargs
    ) -> BaseSlippageModel:
        """
        创建滑点模型
        
        Args:
            slippage_type: 滑点类型
            **kwargs: 模型参数
            
        Returns:
            BaseSlippageModel: 滑点模型实例
        """
        if slippage_type == SlippageType.FIXED:
            return FixedSlippageModel(**kwargs)
        elif slippage_type == SlippageType.PERCENTAGE:
            return PercentageSlippageModel(**kwargs)
        elif slippage_type == SlippageType.VOLUME_WEIGHTED:
            return VolumeWeightedSlippageModel(**kwargs)
        elif slippage_type == SlippageType.VOLATILITY_ADJUSTED:
            return VolatilityAdjustedSlippageModel(**kwargs)
        elif slippage_type == SlippageType.MARKET_IMPACT:
            return MarketImpactSlippageModel(**kwargs)
        else:
            return PercentageSlippageModel(**kwargs)
    
    @classmethod
    def list_models(cls) -> list:
        """列出所有已注册的模型"""
        return list(cls._models.keys())


SlippageModel.register('fixed', FixedSlippageModel())
SlippageModel.register('percentage', PercentageSlippageModel())
SlippageModel.register('volume_weighted', VolumeWeightedSlippageModel())
SlippageModel.register('volatility_adjusted', VolatilityAdjustedSlippageModel())
SlippageModel.register('market_impact', MarketImpactSlippageModel())
