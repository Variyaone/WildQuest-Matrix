"""
强化学习执行算法模块

使用强化学习优化订单执行，支持大额订单拆分、TWAP/VWAP优化。
与传统执行算法并存，提供更智能的执行策略。
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

import pandas as pd
import numpy as np

from ..trading.order import TradeOrder, OrderSide, OrderType, OrderStatus
from ..infrastructure.exceptions import TradingException

logger = logging.getLogger(__name__)


class ExecutionAlgorithm(Enum):
    """执行算法类型"""
    TWAP = "twap"
    VWAP = "vwap"
    POV = "pov"
    IS = "implementation_shortfall"
    RL = "reinforcement_learning"


@dataclass
class ExecutionConfig:
    """执行配置"""
    algorithm: ExecutionAlgorithm = ExecutionAlgorithm.RL
    state_dim: int = 20
    action_dim: int = 10
    hidden_dim: int = 32
    learning_rate: float = 1e-4
    gamma: float = 0.99
    max_execution_time: int = 30
    min_slice_interval: int = 1
    max_slice_size_ratio: float = 0.3
    urgency: float = 0.5
    risk_aversion: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm": self.algorithm.value,
            "state_dim": self.state_dim,
            "action_dim": self.action_dim,
            "hidden_dim": self.hidden_dim,
            "learning_rate": self.learning_rate,
            "gamma": self.gamma,
            "max_execution_time": self.max_execution_time,
            "min_slice_interval": self.min_slice_interval,
            "max_slice_size_ratio": self.max_slice_size_ratio,
            "urgency": self.urgency,
            "risk_aversion": self.risk_aversion
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionConfig":
        if 'algorithm' in data and isinstance(data['algorithm'], str):
            data['algorithm'] = ExecutionAlgorithm(data['algorithm'])
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class ExecutionState:
    """执行状态"""
    remaining_quantity: int
    elapsed_time: int
    total_time: int
    avg_price: float
    target_price: float
    market_volume: float
    volatility: float
    spread: float
    momentum: float
    
    def to_array(self) -> np.ndarray:
        """转换为数组"""
        return np.array([
            self.remaining_quantity,
            self.elapsed_time / max(self.total_time, 1),
            self.avg_price / max(self.target_price, 1),
            self.market_volume,
            self.volatility,
            self.spread,
            self.momentum,
            self.elapsed_time,
            self.total_time,
            self.remaining_quantity / max(self.remaining_quantity + 1, 1)
        ])


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    sub_orders: List[TradeOrder] = field(default_factory=list)
    total_filled: int = 0
    avg_fill_price: float = 0.0
    total_cost: float = 0.0
    slippage: float = 0.0
    execution_time: int = 0
    error_message: Optional[str] = None


class ExecutionEnvironment:
    """
    执行环境
    
    模拟订单执行环境，用于强化学习训练。
    """
    
    def __init__(
        self,
        market_data: pd.DataFrame,
        total_quantity: int,
        max_time: int = 30,
        transaction_cost: float = 0.001,
        slippage_model: str = "linear"
    ):
        """
        初始化执行环境
        
        Args:
            market_data: 市场数据
            total_quantity: 总订单量
            max_time: 最大执行时间（分钟）
            transaction_cost: 交易成本
            slippage_model: 滑点模型
        """
        self.market_data = market_data
        self.total_quantity = total_quantity
        self.max_time = max_time
        self.transaction_cost = transaction_cost
        self.slippage_model = slippage_model
        
        self.remaining_quantity = total_quantity
        self.elapsed_time = 0
        self.filled_quantity = 0
        self.total_cost = 0.0
        self.avg_price = 0.0
        
        self.current_step = 0
    
    def reset(self) -> np.ndarray:
        """重置环境"""
        self.remaining_quantity = self.total_quantity
        self.elapsed_time = 0
        self.filled_quantity = 0
        self.total_cost = 0.0
        self.avg_price = 0.0
        self.current_step = 0
        
        return self._get_state()
    
    def step(self, action: float) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        执行动作
        
        Args:
            action: 执行比例 [0, 1]
            
        Returns:
            next_state, reward, done, info
        """
        action = np.clip(action, 0, 1)
        
        execute_quantity = int(action * self.remaining_quantity)
        execute_quantity = max(0, min(execute_quantity, self.remaining_quantity))
        
        current_price = self._get_current_price()
        slippage = self._calculate_slippage(execute_quantity)
        fill_price = current_price * (1 + slippage)
        
        cost = execute_quantity * fill_price * (1 + self.transaction_cost)
        self.total_cost += cost
        self.filled_quantity += execute_quantity
        self.remaining_quantity -= execute_quantity
        
        if self.filled_quantity > 0:
            self.avg_price = self.total_cost / self.filled_quantity
        
        self.elapsed_time += 1
        self.current_step += 1
        
        reward = self._calculate_reward(execute_quantity, fill_price, slippage)
        
        done = (self.remaining_quantity <= 0) or (self.elapsed_time >= self.max_time)
        
        info = {
            'filled_quantity': self.filled_quantity,
            'remaining_quantity': self.remaining_quantity,
            'avg_price': self.avg_price,
            'total_cost': self.total_cost,
            'elapsed_time': self.elapsed_time
        }
        
        return self._get_state(), reward, done, info
    
    def _get_state(self) -> np.ndarray:
        """获取当前状态"""
        if self.current_step < len(self.market_data):
            current_data = self.market_data.iloc[self.current_step]
            price = current_data.get('close', 10.0)
            volume = current_data.get('volume', 1000000)
            volatility = current_data.get('volatility', 0.02)
            spread = current_data.get('spread', 0.001)
            momentum = current_data.get('momentum', 0.0)
        else:
            price = 10.0
            volume = 1000000
            volatility = 0.02
            spread = 0.001
            momentum = 0.0
        
        state = ExecutionState(
            remaining_quantity=self.remaining_quantity,
            elapsed_time=self.elapsed_time,
            total_time=self.max_time,
            avg_price=self.avg_price,
            target_price=price,
            market_volume=volume,
            volatility=volatility,
            spread=spread,
            momentum=momentum
        )
        
        return state.to_array()
    
    def _get_current_price(self) -> float:
        """获取当前价格"""
        if self.current_step < len(self.market_data):
            return self.market_data.iloc[self.current_step].get('close', 10.0)
        return 10.0
    
    def _calculate_slippage(self, quantity: int) -> float:
        """计算滑点"""
        if self.slippage_model == "linear":
            base_slippage = 0.0001
            quantity_impact = quantity / self.total_quantity * 0.001
            return base_slippage + quantity_impact
        elif self.slippage_model == "square_root":
            return 0.001 * np.sqrt(quantity / self.total_quantity)
        else:
            return 0.0001
    
    def _calculate_reward(
        self,
        quantity: int,
        fill_price: float,
        slippage: float
    ) -> float:
        """计算奖励"""
        if quantity == 0:
            return -0.01
        
        efficiency = quantity / self.total_quantity
        
        urgency_penalty = -0.001 * (self.elapsed_time / self.max_time)
        
        slippage_penalty = -slippage * 10
        
        reward = efficiency + urgency_penalty + slippage_penalty
        
        return reward


class RLExecutionAgent:
    """强化学习执行智能体"""
    
    def __init__(self, config: ExecutionConfig):
        self.config = config
        self.policy_network = None
        self.value_network = None
        self.optimizer = None
        self.is_trained = False
        self._build_network()
    
    def _build_network(self):
        """构建网络"""
        try:
            import torch
            import torch.nn as nn
            
            class PolicyNetwork(nn.Module):
                def __init__(self, state_dim, hidden_dim):
                    super().__init__()
                    self.network = nn.Sequential(
                        nn.Linear(state_dim, hidden_dim),
                        nn.ReLU(),
                        nn.Linear(hidden_dim, hidden_dim),
                        nn.ReLU(),
                        nn.Linear(hidden_dim, 1),
                        nn.Sigmoid()
                    )
                
                def forward(self, state):
                    return self.network(state)
            
            class ValueNetwork(nn.Module):
                def __init__(self, state_dim, hidden_dim):
                    super().__init__()
                    self.network = nn.Sequential(
                        nn.Linear(state_dim, hidden_dim),
                        nn.ReLU(),
                        nn.Linear(hidden_dim, hidden_dim),
                        nn.ReLU(),
                        nn.Linear(hidden_dim, 1)
                    )
                
                def forward(self, state):
                    return self.network(state)
            
            self.policy_network = PolicyNetwork(
                self.config.state_dim,
                self.config.hidden_dim
            )
            self.value_network = ValueNetwork(
                self.config.state_dim,
                self.config.hidden_dim
            )
            
            self.optimizer = torch.optim.Adam([
                {'params': self.policy_network.parameters()},
                {'params': self.value_network.parameters()}
            ], lr=self.config.learning_rate)
            
            logger.info("执行智能体网络构建成功")
            
        except ImportError:
            logger.warning("PyTorch未安装")
    
    def select_action(self, state: np.ndarray) -> float:
        """选择动作"""
        if self.policy_network is None:
            return np.random.uniform(0.1, 0.5)
        
        try:
            import torch
            
            with torch.no_grad():
                state_tensor = torch.FloatTensor(state).unsqueeze(0)
                action = self.policy_network(state_tensor)
                return action.item()
                
        except Exception as e:
            logger.error(f"选择动作失败: {e}")
            return np.random.uniform(0.1, 0.5)
    
    def train(
        self,
        market_data: pd.DataFrame,
        total_quantity: int = 10000,
        n_episodes: int = 1000
    ) -> Dict[str, Any]:
        """训练智能体"""
        result = {
            'success': False,
            'episode_rewards': [],
            'mean_reward': 0.0
        }
        
        if self.policy_network is None:
            result['error_message'] = "网络未构建"
            return result
        
        try:
            import torch
            import torch.nn as nn
            
            env = ExecutionEnvironment(
                market_data=market_data,
                total_quantity=total_quantity,
                max_time=self.config.max_execution_time
            )
            
            start_time = datetime.now()
            
            for episode in range(n_episodes):
                state = env.reset()
                episode_reward = 0
                
                states, actions, rewards = [], [], []
                
                done = False
                while not done:
                    action = self.select_action(state)
                    next_state, reward, done, info = env.step(action)
                    
                    states.append(state)
                    actions.append(action)
                    rewards.append(reward)
                    
                    episode_reward += reward
                    state = next_state
                
                result['episode_rewards'].append(episode_reward)
                
                self._update_policy(states, actions, rewards)
                
                if episode % 100 == 0:
                    logger.info(f"Episode {episode}, reward={episode_reward:.4f}")
            
            result['mean_reward'] = np.mean(result['episode_rewards'][-100:])
            result['training_time'] = (datetime.now() - start_time).total_seconds()
            result['success'] = True
            self.is_trained = True
            
        except Exception as e:
            result['error_message'] = str(e)
            logger.error(f"训练失败: {e}")
        
        return result
    
    def _update_policy(self, states, actions, rewards):
        """更新策略"""
        try:
            import torch
            import torch.nn as nn
            
            states = torch.FloatTensor(np.array(states))
            actions = torch.FloatTensor(actions)
            
            returns = []
            R = 0
            for r in reversed(rewards):
                R = r + self.config.gamma * R
                returns.insert(0, R)
            returns = torch.FloatTensor(returns)
            returns = (returns - returns.mean()) / (returns.std() + 1e-8)
            
            pred_actions = self.policy_network(states).squeeze()
            values = self.value_network(states).squeeze()
            
            advantages = returns - values.detach()
            
            policy_loss = -torch.log(pred_actions + 1e-8) * actions * advantages
            value_loss = nn.MSELoss()(values, returns)
            
            loss = policy_loss.mean() + 0.5 * value_loss
            
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            
        except Exception as e:
            logger.error(f"更新策略失败: {e}")
    
    def save(self, path: str):
        """保存模型"""
        try:
            import torch
            
            os.makedirs(os.path.dirname(path), exist_ok=True)
            torch.save({
                'policy_state_dict': self.policy_network.state_dict(),
                'value_state_dict': self.value_network.state_dict(),
                'config': self.config.to_dict()
            }, path)
            logger.info(f"模型已保存至 {path}")
            
        except Exception as e:
            logger.error(f"保存模型失败: {e}")
    
    def load(self, path: str):
        """加载模型"""
        try:
            import torch
            
            checkpoint = torch.load(path)
            self.policy_network.load_state_dict(checkpoint['policy_state_dict'])
            self.value_network.load_state_dict(checkpoint['value_state_dict'])
            self.is_trained = True
            logger.info(f"模型已从 {path} 加载")
            
        except Exception as e:
            logger.error(f"加载模型失败: {e}")


class TWAPExecutor:
    """TWAP执行算法"""
    
    def __init__(self, time_horizon: int = 30):
        self.time_horizon = time_horizon
    
    def split_order(
        self,
        order: TradeOrder,
        market_data: pd.DataFrame
    ) -> List[TradeOrder]:
        """拆分订单"""
        total_quantity = order.quantity
        slice_quantity = total_quantity // self.time_horizon
        
        sub_orders = []
        for i in range(self.time_horizon):
            qty = slice_quantity if i < self.time_horizon - 1 else total_quantity - slice_quantity * (self.time_horizon - 1)
            
            if qty <= 0:
                break
            
            sub_order = TradeOrder(
                order_id=f"{order.order_id}_TWAP_{i}",
                stock_code=order.stock_code,
                stock_name=order.stock_name,
                side=order.side,
                order_type=OrderType.LIMIT,
                quantity=qty,
                price=order.price,
                reason=f"TWAP拆单 {i+1}/{self.time_horizon}"
            )
            sub_orders.append(sub_order)
        
        return sub_orders


class VWAPExecutor:
    """VWAP执行算法"""
    
    def __init__(self, time_horizon: int = 30):
        self.time_horizon = time_horizon
    
    def split_order(
        self,
        order: TradeOrder,
        market_data: pd.DataFrame
    ) -> List[TradeOrder]:
        """拆分订单"""
        total_quantity = order.quantity
        
        volume_profile = self._estimate_volume_profile(market_data)
        
        sub_orders = []
        remaining = total_quantity
        
        for i, volume_ratio in enumerate(volume_profile):
            if remaining <= 0:
                break
            
            qty = int(total_quantity * volume_ratio)
            qty = min(qty, remaining)
            
            if qty <= 0:
                continue
            
            sub_order = TradeOrder(
                order_id=f"{order.order_id}_VWAP_{i}",
                stock_code=order.stock_code,
                stock_name=order.stock_name,
                side=order.side,
                order_type=OrderType.LIMIT,
                quantity=qty,
                price=order.price,
                reason=f"VWAP拆单 {i+1}/{self.time_horizon}"
            )
            sub_orders.append(sub_order)
            remaining -= qty
        
        return sub_orders
    
    def _estimate_volume_profile(self, market_data: pd.DataFrame) -> List[float]:
        """估计成交量分布"""
        if 'volume' not in market_data.columns:
            return [1.0 / self.time_horizon] * self.time_horizon
        
        avg_volume = market_data['volume'].mean()
        profile = []
        
        for i in range(self.time_horizon):
            if i < len(market_data):
                vol = market_data['volume'].iloc[i]
                profile.append(vol / avg_volume if avg_volume > 0 else 1.0)
            else:
                profile.append(1.0)
        
        total = sum(profile)
        return [p / total for p in profile]


class RLExecutionAlgorithm:
    """
    强化学习执行算法
    
    使用强化学习优化订单执行，与传统执行算法并存。
    """
    
    def __init__(
        self,
        config: Optional[ExecutionConfig] = None,
        agent_path: Optional[str] = None
    ):
        """
        初始化RL执行算法
        
        Args:
            config: 执行配置
            agent_path: 预训练智能体路径
        """
        self.config = config or ExecutionConfig()
        self.agent_path = agent_path
        self.agent = None
        self.twap_executor = TWAPExecutor(self.config.max_execution_time)
        self.vwap_executor = VWAPExecutor(self.config.max_execution_time)
        
        self._build_agent()
        
        if agent_path and os.path.exists(agent_path):
            self.agent.load(agent_path)
    
    def _build_agent(self):
        """构建智能体"""
        self.agent = RLExecutionAgent(self.config)
    
    def train(
        self,
        market_data: pd.DataFrame,
        n_episodes: int = 1000
    ) -> Dict[str, Any]:
        """
        训练执行智能体
        
        Args:
            market_data: 市场数据
            n_episodes: 训练回合数
            
        Returns:
            训练结果
        """
        logger.info("开始训练RL执行智能体")
        
        result = self.agent.train(market_data, n_episodes=n_episodes)
        
        if result['success']:
            logger.info(f"训练成功，平均奖励: {result['mean_reward']:.4f}")
        else:
            logger.error(f"训练失败: {result.get('error_message')}")
        
        return result
    
    def split_order(
        self,
        order: TradeOrder,
        market_data: pd.DataFrame,
        method: str = "rl"
    ) -> ExecutionResult:
        """
        拆分订单
        
        Args:
            order: 原始订单
            market_data: 市场数据
            method: 执行方法 (rl/twap/vwap)
            
        Returns:
            执行结果
        """
        result = ExecutionResult(success=False)
        
        try:
            if method == "twap":
                sub_orders = self.twap_executor.split_order(order, market_data)
            elif method == "vwap":
                sub_orders = self.vwap_executor.split_order(order, market_data)
            elif method == "rl":
                sub_orders = self._rl_split(order, market_data)
            else:
                sub_orders = self.twap_executor.split_order(order, market_data)
            
            result.sub_orders = sub_orders
            result.total_filled = sum(o.quantity for o in sub_orders)
            result.success = True
            
            logger.info(f"订单拆分成功: {order.order_id} -> {len(sub_orders)}个子订单")
            
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"订单拆分失败: {e}")
        
        return result
    
    def _rl_split(
        self,
        order: TradeOrder,
        market_data: pd.DataFrame
    ) -> List[TradeOrder]:
        """RL拆分"""
        if not self.agent.is_trained:
            logger.warning("RL智能体未训练，回退到TWAP")
            return self.twap_executor.split_order(order, market_data)
        
        sub_orders = []
        remaining_quantity = order.quantity
        elapsed_time = 0
        
        while remaining_quantity > 0 and elapsed_time < self.config.max_execution_time:
            state = self._build_execution_state(
                remaining_quantity,
                elapsed_time,
                market_data
            )
            
            action = self.agent.select_action(state)
            
            execute_quantity = int(action * remaining_quantity * self.config.max_slice_size_ratio)
            execute_quantity = max(1, min(execute_quantity, remaining_quantity))
            
            current_price = self._get_current_price(market_data, elapsed_time)
            
            sub_order = TradeOrder(
                order_id=f"{order.order_id}_RL_{elapsed_time}",
                stock_code=order.stock_code,
                stock_name=order.stock_name,
                side=order.side,
                order_type=OrderType.LIMIT,
                quantity=execute_quantity,
                price=current_price,
                reason=f"RL拆单 t={elapsed_time}"
            )
            sub_orders.append(sub_order)
            
            remaining_quantity -= execute_quantity
            elapsed_time += 1
        
        return sub_orders
    
    def _build_execution_state(
        self,
        remaining_quantity: int,
        elapsed_time: int,
        market_data: pd.DataFrame
    ) -> np.ndarray:
        """构建执行状态"""
        if elapsed_time < len(market_data):
            current_data = market_data.iloc[elapsed_time]
            price = current_data.get('close', 10.0)
            volume = current_data.get('volume', 1000000)
            volatility = current_data.get('volatility', 0.02)
            spread = current_data.get('spread', 0.001)
            momentum = current_data.get('momentum', 0.0)
        else:
            price = 10.0
            volume = 1000000
            volatility = 0.02
            spread = 0.001
            momentum = 0.0
        
        return np.array([
            remaining_quantity,
            elapsed_time / self.config.max_execution_time,
            price,
            volume,
            volatility,
            spread,
            momentum,
            remaining_quantity / max(remaining_quantity + 1, 1),
            0.0,
            0.0
        ])
    
    def _get_current_price(self, market_data: pd.DataFrame, step: int) -> float:
        """获取当前价格"""
        if step < len(market_data):
            return market_data.iloc[step].get('close', 10.0)
        return 10.0
    
    def save_agent(self, path: Optional[str] = None):
        """保存智能体"""
        path = path or self.agent_path
        if path is None:
            raise ValueError("未指定保存路径")
        
        self.agent.save(path)
        self.agent_path = path
    
    def load_agent(self, path: str):
        """加载智能体"""
        self.agent.load(path)
        self.agent_path = path


def create_rl_executor(
    agent_path: Optional[str] = None,
    max_execution_time: int = 30,
    **kwargs
) -> RLExecutionAlgorithm:
    """
    创建RL执行器的便捷函数
    
    Args:
        agent_path: 预训练智能体路径
        max_execution_time: 最大执行时间
        **kwargs: 其他配置参数
        
    Returns:
        RLExecutionAlgorithm实例
    """
    config = ExecutionConfig(
        max_execution_time=max_execution_time,
        **kwargs
    )
    return RLExecutionAlgorithm(config, agent_path)


_rl_executor_instance: Optional[RLExecutionAlgorithm] = None


def get_rl_executor(
    agent_path: Optional[str] = None,
    max_execution_time: int = 30,
    **kwargs
) -> RLExecutionAlgorithm:
    """
    获取RL执行器单例
    
    Args:
        agent_path: 预训练智能体路径
        max_execution_time: 最大执行时间
        **kwargs: 其他配置参数
        
    Returns:
        RLExecutionAlgorithm实例
    """
    global _rl_executor_instance
    if _rl_executor_instance is None:
        _rl_executor_instance = create_rl_executor(agent_path, max_execution_time, **kwargs)
    return _rl_executor_instance
