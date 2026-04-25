"""
突发事件模拟器

模拟黑天鹅事件、熔断、涨跌停板等极端情况，测试策略鲁棒性。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import date, timedelta
from enum import Enum
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型"""
    MARKET_CRASH = "market_crash"           # 股灾
    CIRCUIT_BREAKER = "circuit_breaker"     # 熔断
    PANIC_SELLING = "panic_selling"         # 恐慌性抛售
    LIQUIDITY_CRUNCH = "liquidity_crunch"   # 流动性枯竭
    BLACK_SWAN = "black_swan"               # 黑天鹅
    LIMIT_UP_BOARD = "limit_up_board"       # 涨停板
    LIMIT_DOWN_BOARD = "limit_down_board"   # 跌停板
    SUSPENSION = "suspension"               # 停牌
    REGULATORY = "regulatory"               # 监管政策


@dataclass
class MarketEvent:
    """市场事件"""
    event_id: str
    event_type: EventType
    event_date: date
    duration_days: int
    severity: float  # 0-1，严重程度
    affected_stocks: Optional[List[str]] = None
    market_impact: Optional[Dict[str, float]] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'event_date': self.event_date.isoformat(),
            'duration_days': self.duration_days,
            'severity': self.severity,
            'affected_stocks': self.affected_stocks,
            'market_impact': self.market_impact,
            'description': self.description,
            'metadata': self.metadata
        }


@dataclass
class EventEffect:
    """事件影响"""
    trading_halted: bool = False
    halt_duration_hours: float = 0.0
    limit_up_enforced: bool = False
    limit_down_enforced: bool = False
    liquidity_crunch: bool = False
    price_impact: float = 0.0
    volume_impact: float = 0.0
    spread_widening: float = 0.0
    forced_liquidation: bool = False
    message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'trading_halted': self.trading_halted,
            'halt_duration_hours': self.halt_duration_hours,
            'limit_up_enforced': self.limit_up_enforced,
            'limit_down_enforced': self.limit_down_enforced,
            'liquidity_crunch': self.liquidity_crunch,
            'price_impact': self.price_impact,
            'volume_impact': self.volume_impact,
            'spread_widening': self.spread_widening,
            'forced_liquidation': self.forced_liquidation,
            'message': self.message
        }


class BlackSwanEventSimulator:
    """
    黑天鹅事件模拟器
    
    模拟极端市场事件，测试策略鲁棒性。
    """
    
    HISTORICAL_EVENTS = {
        "2015-06-15": MarketEvent(
            event_id="2015_crash",
            event_type=EventType.MARKET_CRASH,
            event_date=date(2015, 6, 15),
            duration_days=20,
            severity=0.9,
            market_impact={
                'market_drop': -0.35,
                'volatility_spike': 3.0,
                'liquidity_drop': -0.7
            },
            description="2015年股灾，市场暴跌35%"
        ),
        "2016-01-04": MarketEvent(
            event_id="2016_circuit_breaker",
            event_type=EventType.CIRCUIT_BREAKER,
            event_date=date(2016, 1, 4),
            duration_days=1,
            severity=0.8,
            market_impact={
                'market_drop': -0.07,
                'halt_hours': 2.0
            },
            description="2016年熔断机制触发，提前收盘"
        ),
        "2020-02-03": MarketEvent(
            event_id="2020_pandemic",
            event_type=EventType.BLACK_SWAN,
            event_date=date(2020, 2, 3),
            duration_days=3,
            severity=0.7,
            market_impact={
                'market_drop': -0.08,
                'limit_down_count': 3000
            },
            description="新冠疫情爆发，市场恐慌性下跌"
        ),
        "2018-10-11": MarketEvent(
            event_id="2018_crash",
            event_type=EventType.MARKET_CRASH,
            event_date=date(2018, 10, 11),
            duration_days=10,
            severity=0.6,
            market_impact={
                'market_drop': -0.10,
                'volatility_spike': 2.0
            },
            description="2018年市场大跌"
        ),
        "2019-05-06": MarketEvent(
            event_id="2019_trade_war",
            event_type=EventType.BLACK_SWAN,
            event_date=date(2019, 5, 6),
            duration_days=5,
            severity=0.5,
            market_impact={
                'market_drop': -0.06,
                'volatility_spike': 1.5
            },
            description="中美贸易战升级"
        )
    }
    
    def __init__(
        self,
        enable_historical_events: bool = True,
        enable_synthetic_events: bool = True,
        stress_test_mode: bool = False
    ):
        """
        初始化黑天鹅事件模拟器
        
        Args:
            enable_historical_events: 启用历史事件
            enable_synthetic_events: 启用合成事件
            stress_test_mode: 压力测试模式
        """
        self.enable_historical_events = enable_historical_events
        self.enable_synthetic_events = enable_synthetic_events
        self.stress_test_mode = stress_test_mode
        
        self._custom_events: Dict[str, MarketEvent] = {}
    
    def register_custom_event(self, event: MarketEvent):
        """注册自定义事件"""
        self._custom_events[event.event_id] = event
        logger.info(f"注册自定义事件: {event.event_id}")
    
    def get_event(self, event_id: str) -> Optional[MarketEvent]:
        """获取事件"""
        for event in self.HISTORICAL_EVENTS.values():
            if event.event_id == event_id:
                return event
        if event_id in self._custom_events:
            return self._custom_events[event_id]
        return None
    
    def get_events_in_range(
        self,
        start_date: date,
        end_date: date
    ) -> List[MarketEvent]:
        """获取时间范围内的事件"""
        events = []
        
        all_events = {**self.HISTORICAL_EVENTS, **self._custom_events}
        
        for event in all_events.values():
            event_end = event.event_date + timedelta(days=event.duration_days)
            if event.event_date <= end_date and event_end >= start_date:
                events.append(event)
        
        return sorted(events, key=lambda e: e.event_date)
    
    def apply_event_effects(
        self,
        event: MarketEvent,
        portfolio_value: float,
        positions: Dict[str, Any],
        market_data: pd.DataFrame
    ) -> EventEffect:
        """
        应用事件影响
        
        Args:
            event: 市场事件
            portfolio_value: 组合价值
            positions: 持仓
            market_data: 市场数据
            
        Returns:
            EventEffect: 事件影响
        """
        effect = EventEffect()
        
        if event.event_type == EventType.CIRCUIT_BREAKER:
            effect = self._apply_circuit_breaker(event)
        
        elif event.event_type == EventType.MARKET_CRASH:
            effect = self._apply_market_crash(event, positions, market_data)
        
        elif event.event_type == EventType.BLACK_SWAN:
            effect = self._apply_black_swan(event, positions, market_data)
        
        elif event.event_type == EventType.LIQUIDITY_CRUNCH:
            effect = self._apply_liquidity_crunch(event, positions)
        
        elif event.event_type == EventType.LIMIT_DOWN_BOARD:
            effect = self._apply_limit_down_board(event, positions)
        
        return effect
    
    def _apply_circuit_breaker(self, event: MarketEvent) -> EventEffect:
        """应用熔断影响"""
        halt_hours = event.market_impact.get('halt_hours', 2.0) if event.market_impact else 2.0
        
        return EventEffect(
            trading_halted=True,
            halt_duration_hours=halt_hours,
            price_impact=event.market_impact.get('market_drop', -0.05) if event.market_impact else -0.05,
            message=f"熔断触发，交易暂停{halt_hours}小时"
        )
    
    def _apply_market_crash(
        self,
        event: MarketEvent,
        positions: Dict[str, Any],
        market_data: pd.DataFrame
    ) -> EventEffect:
        """应用股灾影响"""
        market_drop = event.market_impact.get('market_drop', -0.20) if event.market_impact else -0.20
        volatility_spike = event.market_impact.get('volatility_spike', 2.0) if event.market_impact else 2.0
        
        limit_down_count = 0
        if 'pct_chg' in market_data.columns:
            limit_down_count = (market_data['pct_chg'] <= -9.9).sum()
        
        return EventEffect(
            limit_down_enforced=True,
            liquidity_crunch=True,
            price_impact=market_drop,
            volume_impact=-0.5,
            spread_widening=volatility_spike,
            message=f"股灾：市场下跌{abs(market_drop):.1%}，{limit_down_count}只股票跌停"
        )
    
    def _apply_black_swan(
        self,
        event: MarketEvent,
        positions: Dict[str, Any],
        market_data: pd.DataFrame
    ) -> EventEffect:
        """应用黑天鹅影响"""
        market_drop = event.market_impact.get('market_drop', -0.10) if event.market_impact else -0.10
        
        return EventEffect(
            limit_down_enforced=True,
            liquidity_crunch=True,
            forced_liquidation=True,
            price_impact=market_drop,
            volume_impact=-0.7,
            spread_widening=3.0,
            message=f"黑天鹅事件：{event.description}"
        )
    
    def _apply_liquidity_crunch(
        self,
        event: MarketEvent,
        positions: Dict[str, Any]
    ) -> EventEffect:
        """应用流动性枯竭影响"""
        return EventEffect(
            liquidity_crunch=True,
            volume_impact=-0.8,
            spread_widening=5.0,
            message="流动性枯竭：买卖价差急剧扩大"
        )
    
    def _apply_limit_down_board(
        self,
        event: MarketEvent,
        positions: Dict[str, Any]
    ) -> EventEffect:
        """应用跌停板影响"""
        affected_count = len(event.affected_stocks) if event.affected_stocks else 0
        
        return EventEffect(
            limit_down_enforced=True,
            liquidity_crunch=True,
            price_impact=-0.10,
            message=f"跌停板：{affected_count}只股票跌停，无法卖出"
        )
    
    def generate_stress_scenarios(
        self,
        base_date: date,
        scenario_count: int = 5
    ) -> List[MarketEvent]:
        """
        生成压力测试场景
        
        Args:
            base_date: 基准日期
            scenario_count: 场景数量
            
        Returns:
            List[MarketEvent]: 压力场景列表
        """
        scenarios = []
        
        crash_scenario = MarketEvent(
            event_id="stress_crash",
            event_type=EventType.MARKET_CRASH,
            event_date=base_date,
            duration_days=10,
            severity=0.95,
            market_impact={
                'market_drop': -0.30,
                'volatility_spike': 4.0,
                'liquidity_drop': -0.9
            },
            description="压力测试：极端股灾场景"
        )
        scenarios.append(crash_scenario)
        
        liquidity_scenario = MarketEvent(
            event_id="stress_liquidity",
            event_type=EventType.LIQUIDITY_CRUNCH,
            event_date=base_date,
            duration_days=5,
            severity=0.85,
            market_impact={
                'liquidity_drop': -0.95,
                'spread_widening': 10.0
            },
            description="压力测试：流动性枯竭场景"
        )
        scenarios.append(liquidity_scenario)
        
        circuit_breaker_scenario = MarketEvent(
            event_id="stress_circuit_breaker",
            event_type=EventType.CIRCUIT_BREAKER,
            event_date=base_date,
            duration_days=1,
            severity=0.9,
            market_impact={
                'market_drop': -0.10,
                'halt_hours': 4.0
            },
            description="压力测试：全天熔断场景"
        )
        scenarios.append(circuit_breaker_scenario)
        
        black_swan_scenario = MarketEvent(
            event_id="stress_black_swan",
            event_type=EventType.BLACK_SWAN,
            event_date=base_date,
            duration_days=7,
            severity=0.95,
            market_impact={
                'market_drop': -0.25,
                'volatility_spike': 5.0,
                'liquidity_drop': -0.8
            },
            description="压力测试：极端黑天鹅场景"
        )
        scenarios.append(black_swan_scenario)
        
        combined_scenario = MarketEvent(
            event_id="stress_combined",
            event_type=EventType.BLACK_SWAN,
            event_date=base_date,
            duration_days=15,
            severity=1.0,
            market_impact={
                'market_drop': -0.40,
                'volatility_spike': 6.0,
                'liquidity_drop': -0.95,
                'halt_hours': 6.0
            },
            description="压力测试：组合极端场景"
        )
        scenarios.append(combined_scenario)
        
        return scenarios[:scenario_count]
    
    def simulate_event_impact_on_portfolio(
        self,
        event: MarketEvent,
        portfolio_value: float,
        positions: Dict[str, float],
        market_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        模拟事件对组合的影响
        
        Args:
            event: 市场事件
            portfolio_value: 组合价值
            positions: 持仓 {stock_code: weight}
            market_data: 市场数据
            
        Returns:
            Dict: 影响分析结果
        """
        effect = self.apply_event_effects(event, portfolio_value, positions, market_data)
        
        portfolio_impact = portfolio_value * effect.price_impact
        
        if effect.limit_down_enforced:
            sellable_value = portfolio_value * 0.3
        else:
            sellable_value = portfolio_value
        
        if effect.liquidity_crunch:
            liquidation_cost = portfolio_value * 0.05
        else:
            liquidation_cost = 0
        
        net_impact = portfolio_impact - liquidation_cost
        
        return {
            'event': event.to_dict(),
            'effect': effect.to_dict(),
            'portfolio_value_before': portfolio_value,
            'portfolio_impact': portfolio_impact,
            'sellable_value': sellable_value,
            'liquidation_cost': liquidation_cost,
            'net_impact': net_impact,
            'portfolio_value_after': portfolio_value + net_impact,
            'impact_pct': net_impact / portfolio_value if portfolio_value > 0 else 0
        }


def create_event_simulator(
    enable_historical_events: bool = True,
    stress_test_mode: bool = False
) -> BlackSwanEventSimulator:
    """创建黑天鹅事件模拟器"""
    return BlackSwanEventSimulator(
        enable_historical_events=enable_historical_events,
        stress_test_mode=stress_test_mode
    )
