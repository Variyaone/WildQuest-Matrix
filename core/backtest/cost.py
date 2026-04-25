"""
交易成本模型

计算交易过程中的各种成本。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List
import numpy as np
import pandas as pd


class CostType(Enum):
    """成本类型"""
    COMMISSION = "commission"
    STAMP_DUTY = "stamp_duty"
    TRANSFER_FEE = "transfer_fee"
    SLIPPAGE = "slippage"
    MARKET_IMPACT = "market_impact"
    FINANCING = "financing"


@dataclass
class TransactionCost:
    """交易成本"""
    total_cost: float
    commission: float
    stamp_duty: float
    transfer_fee: float
    slippage_cost: float
    market_impact: float
    financing: float
    cost_rate: float
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'total_cost': self.total_cost,
            'commission': self.commission,
            'stamp_duty': self.stamp_duty,
            'transfer_fee': self.transfer_fee,
            'slippage_cost': self.slippage_cost,
            'market_impact': self.market_impact,
            'financing': self.financing,
            'cost_rate': self.cost_rate,
            'details': self.details
        }


class BaseCostModel(ABC):
    """成本模型基类"""
    
    @abstractmethod
    def calculate(
        self,
        price: float,
        volume: float,
        direction: str,
        market_data: Optional[Dict[str, Any]] = None
    ) -> TransactionCost:
        """
        计算交易成本
        
        Args:
            price: 交易价格
            volume: 交易数量
            direction: 交易方向 (buy/sell)
            market_data: 市场数据
            
        Returns:
            TransactionCost: 交易成本
        """
        pass


class AShareCostModel(BaseCostModel):
    """A股交易成本模型"""
    
    def __init__(
        self,
        commission_rate: float = 0.0003,
        min_commission: float = 5.0,
        stamp_duty_rate: float = 0.001,
        transfer_fee_rate: float = 0.00001,
        slippage_rate: float = 0.001
    ):
        """
        初始化A股成本模型
        
        Args:
            commission_rate: 佣金率
            min_commission: 最低佣金
            stamp_duty_rate: 印花税率（仅卖出）
            transfer_fee_rate: 过户费率
            slippage_rate: 滑点率
        """
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.stamp_duty_rate = stamp_duty_rate
        self.transfer_fee_rate = transfer_fee_rate
        self.slippage_rate = slippage_rate
    
    def calculate(
        self,
        price: float,
        volume: float,
        direction: str,
        market_data: Optional[Dict[str, Any]] = None
    ) -> TransactionCost:
        """计算A股交易成本"""
        trade_value = price * volume
        
        commission = max(trade_value * self.commission_rate, self.min_commission)
        
        stamp_duty = trade_value * self.stamp_duty_rate if direction == 'sell' else 0.0
        
        transfer_fee = trade_value * self.transfer_fee_rate
        
        slippage_cost = trade_value * self.slippage_rate
        
        market_impact = 0.0
        
        financing = 0.0
        
        total_cost = commission + stamp_duty + transfer_fee + slippage_cost + market_impact + financing
        cost_rate = total_cost / trade_value if trade_value > 0 else 0.0
        
        return TransactionCost(
            total_cost=total_cost,
            commission=commission,
            stamp_duty=stamp_duty,
            transfer_fee=transfer_fee,
            slippage_cost=slippage_cost,
            market_impact=market_impact,
            financing=financing,
            cost_rate=cost_rate,
            details={
                'trade_value': trade_value,
                'direction': direction,
                'commission_rate': self.commission_rate,
                'stamp_duty_rate': self.stamp_duty_rate,
                'transfer_fee_rate': self.transfer_fee_rate,
                'slippage_rate': self.slippage_rate
            }
        )


class DetailedCostModel(BaseCostModel):
    """详细成本模型"""
    
    def __init__(
        self,
        commission_rate: float = 0.0003,
        min_commission: float = 5.0,
        stamp_duty_rate: float = 0.001,
        transfer_fee_rate: float = 0.00001,
        slippage_rate: float = 0.001,
        market_impact_coefficient: float = 0.1,
        financing_rate: float = 0.0
    ):
        """
        初始化详细成本模型
        
        Args:
            commission_rate: 佣金率
            min_commission: 最低佣金
            stamp_duty_rate: 印花税率
            transfer_fee_rate: 过户费率
            slippage_rate: 滑点率
            market_impact_coefficient: 市场冲击系数
            financing_rate: 融资利率
        """
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.stamp_duty_rate = stamp_duty_rate
        self.transfer_fee_rate = transfer_fee_rate
        self.slippage_rate = slippage_rate
        self.market_impact_coefficient = market_impact_coefficient
        self.financing_rate = financing_rate
    
    def calculate(
        self,
        price: float,
        volume: float,
        direction: str,
        market_data: Optional[Dict[str, Any]] = None
    ) -> TransactionCost:
        """计算详细交易成本"""
        market_data = market_data or {}
        trade_value = price * volume
        
        commission = max(trade_value * self.commission_rate, self.min_commission)
        
        stamp_duty = trade_value * self.stamp_duty_rate if direction == 'sell' else 0.0
        
        transfer_fee = trade_value * self.transfer_fee_rate
        
        slippage_cost = trade_value * self.slippage_rate
        
        avg_volume = market_data.get('avg_volume', volume)
        participation_rate = volume / avg_volume if avg_volume > 0 else 0.01
        market_impact = trade_value * self.market_impact_coefficient * np.sqrt(participation_rate)
        
        financing = trade_value * self.financing_rate if direction == 'buy' else 0.0
        
        total_cost = commission + stamp_duty + transfer_fee + slippage_cost + market_impact + financing
        cost_rate = total_cost / trade_value if trade_value > 0 else 0.0
        
        return TransactionCost(
            total_cost=total_cost,
            commission=commission,
            stamp_duty=stamp_duty,
            transfer_fee=transfer_fee,
            slippage_cost=slippage_cost,
            market_impact=market_impact,
            financing=financing,
            cost_rate=cost_rate,
            details={
                'trade_value': trade_value,
                'direction': direction,
                'participation_rate': participation_rate,
                'commission_rate': self.commission_rate,
                'stamp_duty_rate': self.stamp_duty_rate,
                'transfer_fee_rate': self.transfer_fee_rate,
                'slippage_rate': self.slippage_rate,
                'market_impact_coefficient': self.market_impact_coefficient,
                'financing_rate': self.financing_rate
            }
        )


class CostModel:
    """
    成本模型管理器
    
    统一管理不同的成本模型。
    """
    
    _models: Dict[str, BaseCostModel] = {}
    
    @classmethod
    def register(cls, name: str, model: BaseCostModel):
        """注册成本模型"""
        cls._models[name] = model
    
    @classmethod
    def get(cls, name: str) -> Optional[BaseCostModel]:
        """获取成本模型"""
        return cls._models.get(name)
    
    @classmethod
    def create(cls, model_type: str = "ashare", **kwargs) -> BaseCostModel:
        """
        创建成本模型
        
        Args:
            model_type: 模型类型
            **kwargs: 模型参数
            
        Returns:
            BaseCostModel: 成本模型实例
        """
        if model_type == "ashare":
            return AShareCostModel(**kwargs)
        elif model_type == "detailed":
            return DetailedCostModel(**kwargs)
        else:
            return AShareCostModel(**kwargs)
    
    @classmethod
    def list_models(cls) -> list:
        """列出所有已注册的模型"""
        return list(cls._models.keys())
    
    @classmethod
    def calculate_total_cost(
        cls,
        trades: List[Dict[str, Any]],
        model_name: str = "ashare"
    ) -> Dict[str, Any]:
        """
        计算多笔交易的总成本
        
        Args:
            trades: 交易列表
            model_name: 成本模型名称
            
        Returns:
            Dict: 总成本信息
        """
        model = cls.get(model_name)
        if not model:
            model = AShareCostModel()
        
        total_cost = 0.0
        total_commission = 0.0
        total_stamp_duty = 0.0
        total_transfer_fee = 0.0
        total_slippage = 0.0
        total_market_impact = 0.0
        total_financing = 0.0
        total_trade_value = 0.0
        
        for trade in trades:
            cost = model.calculate(
                price=trade.get('price', 0),
                volume=trade.get('volume', 0),
                direction=trade.get('direction', 'buy'),
                market_data=trade.get('market_data')
            )
            
            total_cost += cost.total_cost
            total_commission += cost.commission
            total_stamp_duty += cost.stamp_duty
            total_transfer_fee += cost.transfer_fee
            total_slippage += cost.slippage_cost
            total_market_impact += cost.market_impact
            total_financing += cost.financing
            total_trade_value += trade.get('price', 0) * trade.get('volume', 0)
        
        return {
            'total_cost': total_cost,
            'total_commission': total_commission,
            'total_stamp_duty': total_stamp_duty,
            'total_transfer_fee': total_transfer_fee,
            'total_slippage': total_slippage,
            'total_market_impact': total_market_impact,
            'total_financing': total_financing,
            'total_trade_value': total_trade_value,
            'average_cost_rate': total_cost / total_trade_value if total_trade_value > 0 else 0,
            'trade_count': len(trades)
        }


CostModel.register('ashare', AShareCostModel())
CostModel.register('detailed', DetailedCostModel())
