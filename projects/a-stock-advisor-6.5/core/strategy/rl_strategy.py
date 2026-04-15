"""
强化学习策略模块

使用强化学习进行动态仓位管理和交易决策，与传统策略并存。
支持PPO、DQN、A2C等算法。
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

import pandas as pd
import numpy as np

from .registry import (
    StrategyMetadata,
    StrategyType,
    StrategyStatus,
    RebalanceFrequency,
    RiskParams,
    get_strategy_registry
)
from .factor_combiner import FactorCombinationConfig
from .designer import StrategyTemplate
# from ..signal import get_signal_registry  # TODO: 移除信号依赖
from ..portfolio import PortfolioOptimizer
from ..infrastructure.exceptions import StrategyException

logger = logging.getLogger(__name__)


class RLAlgorithm(Enum):
    """强化学习算法"""
    PPO = "ppo"
    DQN = "dqn"
    A2C = "a2c"
    SAC = "sac"
    TD3 = "td3"


@dataclass
class RLConfig:
    """强化学习配置"""
    algorithm: RLAlgorithm = RLAlgorithm.PPO
    state_dim: int = 50
    action_dim: int = 10
    hidden_dim: int = 64
    learning_rate: float = 3e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_ratio: float = 0.2
    value_loss_coef: float = 0.5
    entropy_coef: float = 0.01
    max_grad_norm: float = 0.5
    n_steps: int = 2048
    batch_size: int = 64
    n_epochs: int = 10
    target_update_freq: int = 1000
    buffer_size: int = 100000
    tau: float = 0.005
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm": self.algorithm.value,
            "state_dim": self.state_dim,
            "action_dim": self.action_dim,
            "hidden_dim": self.hidden_dim,
            "learning_rate": self.learning_rate,
            "gamma": self.gamma,
            "gae_lambda": self.gae_lambda,
            "clip_ratio": self.clip_ratio,
            "value_loss_coef": self.value_loss_coef,
            "entropy_coef": self.entropy_coef,
            "max_grad_norm": self.max_grad_norm,
            "n_steps": self.n_steps,
            "batch_size": self.batch_size,
            "n_epochs": self.n_epochs,
            "target_update_freq": self.target_update_freq,
            "buffer_size": self.buffer_size,
            "tau": self.tau
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RLConfig":
        if 'algorithm' in data and isinstance(data['algorithm'], str):
            data['algorithm'] = RLAlgorithm(data['algorithm'])
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class TradingState:
    """交易状态"""
    holdings: np.ndarray
    cash: float
    prices: np.ndarray
    factor_values: np.ndarray
    market_features: np.ndarray
    
    def to_array(self) -> np.ndarray:
        """转换为数组"""
        return np.concatenate([
            self.holdings,
            [self.cash],
            self.prices,
            self.factor_values,
            self.market_features
        ])


@dataclass
class TradingAction:
    """交易动作"""
    target_weights: np.ndarray
    
    def to_array(self) -> np.ndarray:
        return self.target_weights


@dataclass
class RLTrainingResult:
    """RL训练结果"""
    success: bool
    episode_rewards: List[float] = field(default_factory=list)
    episode_lengths: List[int] = field(default_factory=list)
    mean_reward: float = 0.0
    std_reward: float = 0.0
    training_time: float = 0.0
    best_episode: int = 0
    best_reward: float = float('-inf')
    error_message: Optional[str] = None


class TradingEnvironment:
    """
    交易环境
    
    模拟交易环境，用于强化学习训练。
    """
    
    def __init__(
        self,
        market_data: pd.DataFrame,
        factor_data: pd.DataFrame,
        initial_cash: float = 1000000.0,
        transaction_cost: float = 0.001,
        slippage: float = 0.0005,
        max_position: float = 0.95
    ):
        """
        初始化交易环境
        
        Args:
            market_data: 市场数据
            factor_data: 因子数据
            initial_cash: 初始资金
            transaction_cost: 交易成本
            slippage: 滑点
            max_position: 最大仓位比例
        """
        self.market_data = market_data
        self.factor_data = factor_data
        self.initial_cash = initial_cash
        self.transaction_cost = transaction_cost
        self.slippage = slippage
        self.max_position = max_position
        
        self.n_stocks = len(market_data.columns) if isinstance(market_data.columns, pd.MultiIndex) else 1
        self.current_step = 0
        self.cash = initial_cash
        self.holdings = np.zeros(self.n_stocks)
        self.portfolio_value = initial_cash
        
        self.action_space = self._define_action_space()
        self.observation_space = self._define_observation_space()
    
    def _define_action_space(self) -> Dict:
        """定义动作空间"""
        return {
            'type': 'continuous',
            'shape': (self.n_stocks,),
            'low': 0.0,
            'high': 1.0
        }
    
    def _define_observation_space(self) -> Dict:
        """定义状态空间"""
        return {
            'type': 'continuous',
            'shape': (self.n_stocks * 2 + 2 + 10,)
        }
    
    def reset(self) -> np.ndarray:
        """重置环境"""
        self.current_step = 0
        self.cash = self.initial_cash
        self.holdings = np.zeros(self.n_stocks)
        self.portfolio_value = self.initial_cash
        
        return self._get_state()
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        执行动作
        
        Args:
            action: 目标仓位权重
            
        Returns:
            next_state, reward, done, info
        """
        action = np.clip(action, 0, 1)
        action = action / (np.sum(action) + 1e-8)
        
        target_values = action * self.portfolio_value * self.max_position
        
        current_prices = self._get_current_prices()
        
        for i in range(self.n_stocks):
            current_value = self.holdings[i] * current_prices[i]
            target_value = target_values[i]
            
            if target_value > current_value:
                trade_value = target_value - current_value
                cost = trade_value * (1 + self.transaction_cost + self.slippage)
                if self.cash >= cost:
                    self.holdings[i] += trade_value / current_prices[i]
                    self.cash -= cost
            elif target_value < current_value:
                trade_value = current_value - target_value
                shares = trade_value / current_prices[i]
                self.holdings[i] -= shares
                self.cash += trade_value * (1 - self.transaction_cost - self.slippage)
        
        self.current_step += 1
        
        next_prices = self._get_current_prices()
        new_portfolio_value = self.cash + np.sum(self.holdings * next_prices)
        
        reward = (new_portfolio_value - self.portfolio_value) / self.portfolio_value
        self.portfolio_value = new_portfolio_value
        
        done = self.current_step >= len(self.market_data) - 1
        
        info = {
            'portfolio_value': self.portfolio_value,
            'cash': self.cash,
            'holdings': self.holdings.copy(),
            'step': self.current_step
        }
        
        return self._get_state(), reward, done, info
    
    def _get_state(self) -> np.ndarray:
        """获取当前状态"""
        prices = self._get_current_prices()
        factors = self._get_current_factors()
        
        holdings_value = self.holdings * prices
        weights = holdings_value / (self.portfolio_value + 1e-8)
        
        market_features = np.array([
            self.portfolio_value / self.initial_cash,
            self.cash / self.portfolio_value,
            np.mean(prices),
            np.std(prices),
            np.sum(weights),
            np.max(weights),
            np.min(weights),
            self.current_step / len(self.market_data),
            0.0,
            0.0
        ])
        
        state = np.concatenate([
            weights,
            [self.cash / self.portfolio_value],
            prices / np.max(prices),
            factors,
            market_features
        ])
        
        return state
    
    def _get_current_prices(self) -> np.ndarray:
        """获取当前价格"""
        if isinstance(self.market_data.columns, pd.MultiIndex):
            return self.market_data.iloc[self.current_step].values[:self.n_stocks]
        else:
            return np.array([self.market_data.iloc[self.current_step]])
    
    def _get_current_factors(self) -> np.ndarray:
        """获取当前因子值"""
        if self.factor_data is not None and len(self.factor_data) > self.current_step:
            factors = self.factor_data.iloc[self.current_step].values
            if len(factors) > self.n_stocks:
                factors = factors[:self.n_stocks]
            return factors
        return np.zeros(self.n_stocks)


class PPOAgent:
    """PPO智能体"""
    
    def __init__(self, config: RLConfig):
        self.config = config
        self.actor = None
        self.critic = None
        self.optimizer = None
        self.is_trained = False
        self._build_network()
    
    def _build_network(self):
        """构建网络"""
        try:
            import torch
            import torch.nn as nn
            
            class ActorNetwork(nn.Module):
                def __init__(self, state_dim, action_dim, hidden_dim):
                    super().__init__()
                    self.network = nn.Sequential(
                        nn.Linear(state_dim, hidden_dim),
                        nn.ReLU(),
                        nn.Linear(hidden_dim, hidden_dim),
                        nn.ReLU(),
                        nn.Linear(hidden_dim, action_dim),
                        nn.Softmax(dim=-1)
                    )
                
                def forward(self, state):
                    return self.network(state)
            
            class CriticNetwork(nn.Module):
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
            
            self.actor = ActorNetwork(
                self.config.state_dim,
                self.config.action_dim,
                self.config.hidden_dim
            )
            self.critic = CriticNetwork(
                self.config.state_dim,
                self.config.hidden_dim
            )
            
            self.optimizer = torch.optim.Adam([
                {'params': self.actor.parameters(), 'lr': self.config.learning_rate},
                {'params': self.critic.parameters(), 'lr': self.config.learning_rate}
            ])
            
            logger.info("PPO网络构建成功")
            
        except ImportError:
            logger.warning("PyTorch未安装")
    
    def select_action(self, state: np.ndarray, deterministic: bool = False) -> np.ndarray:
        """选择动作"""
        if self.actor is None:
            return np.random.dirichlet(np.ones(self.config.action_dim))
        
        try:
            import torch
            
            with torch.no_grad():
                state_tensor = torch.FloatTensor(state).unsqueeze(0)
                action_probs = self.actor(state_tensor)
                
                if deterministic:
                    action = torch.argmax(action_probs, dim=-1).numpy()
                else:
                    action = torch.multinomial(action_probs, 1).numpy().flatten()
                
                return action
                
        except Exception as e:
            logger.error(f"选择动作失败: {e}")
            return np.random.dirichlet(np.ones(self.config.action_dim))
    
    def train(self, env: TradingEnvironment, total_steps: int = 100000) -> RLTrainingResult:
        """训练智能体"""
        result = RLTrainingResult(success=False)
        
        if self.actor is None or self.critic is None:
            result.error_message = "网络未构建"
            return result
        
        try:
            import torch
            import torch.nn as nn
            from torch.distributions import Categorical
            
            start_time = datetime.now()
            
            state = env.reset()
            episode_reward = 0
            episode_length = 0
            
            states, actions, rewards, values, log_probs = [], [], [], [], []
            
            for step in range(total_steps):
                state_tensor = torch.FloatTensor(state)
                
                with torch.no_grad():
                    action_probs = self.actor(state_tensor)
                    value = self.critic(state_tensor)
                    dist = Categorical(action_probs)
                    action = dist.sample()
                    log_prob = dist.log_prob(action)
                
                next_state, reward, done, info = env.step(action.numpy())
                
                states.append(state)
                actions.append(action.item())
                rewards.append(reward)
                values.append(value.item())
                log_probs.append(log_prob.item())
                
                episode_reward += reward
                episode_length += 1
                state = next_state
                
                if done or len(states) >= self.config.n_steps:
                    self._update_policy(
                        states, actions, rewards, values, log_probs
                    )
                    states, actions, rewards, values, log_probs = [], [], [], [], []
                    
                    result.episode_rewards.append(episode_reward)
                    result.episode_lengths.append(episode_length)
                    
                    if episode_reward > result.best_reward:
                        result.best_reward = episode_reward
                        result.best_episode = len(result.episode_rewards)
                    
                    episode_reward = 0
                    episode_length = 0
                    state = env.reset()
                
                if step % 1000 == 0:
                    logger.info(f"Step {step}/{total_steps}")
            
            result.mean_reward = np.mean(result.episode_rewards[-100:]) if result.episode_rewards else 0
            result.std_reward = np.std(result.episode_rewards[-100:]) if result.episode_rewards else 0
            result.training_time = (datetime.now() - start_time).total_seconds()
            result.success = True
            self.is_trained = True
            
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"PPO训练失败: {e}")
        
        return result
    
    def _update_policy(self, states, actions, rewards, values, log_probs):
        """更新策略"""
        try:
            import torch
            
            states = torch.FloatTensor(np.array(states))
            actions = torch.LongTensor(actions)
            
            returns = []
            R = 0
            for r in reversed(rewards):
                R = r + self.config.gamma * R
                returns.insert(0, R)
            returns = torch.FloatTensor(returns)
            
            returns = (returns - returns.mean()) / (returns.std() + 1e-8)
            
            for _ in range(self.config.n_epochs):
                action_probs = self.actor(states)
                values_pred = self.critic(states)
                
                from torch.distributions import Categorical
                dist = Categorical(action_probs)
                new_log_probs = dist.log_prob(actions)
                
                advantages = returns - values_pred.squeeze()
                
                ratio = torch.exp(new_log_probs - torch.FloatTensor(log_probs))
                surr1 = ratio * advantages
                surr2 = torch.clamp(ratio, 1 - self.config.clip_ratio, 1 + self.config.clip_ratio) * advantages
                
                actor_loss = -torch.min(surr1, surr2).mean()
                critic_loss = nn.MSELoss()(values_pred.squeeze(), returns)
                
                loss = actor_loss + self.config.value_loss_coef * critic_loss
                
                self.optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(
                    list(self.actor.parameters()) + list(self.critic.parameters()),
                    self.config.max_grad_norm
                )
                self.optimizer.step()
                
        except Exception as e:
            logger.error(f"更新策略失败: {e}")
    
    def save(self, path: str):
        """保存模型"""
        try:
            import torch
            
            os.makedirs(os.path.dirname(path), exist_ok=True)
            torch.save({
                'actor_state_dict': self.actor.state_dict(),
                'critic_state_dict': self.critic.state_dict(),
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
            self.actor.load_state_dict(checkpoint['actor_state_dict'])
            self.critic.load_state_dict(checkpoint['critic_state_dict'])
            self.is_trained = True
            logger.info(f"模型已从 {path} 加载")
            
        except Exception as e:
            logger.error(f"加载模型失败: {e}")


class DQNAgent:
    """DQN智能体"""
    
    def __init__(self, config: RLConfig):
        self.config = config
        self.q_network = None
        self.target_network = None
        self.optimizer = None
        self.memory = []
        self.is_trained = False
        self._build_network()
    
    def _build_network(self):
        """构建网络"""
        try:
            import torch
            import torch.nn as nn
            
            class QNetwork(nn.Module):
                def __init__(self, state_dim, action_dim, hidden_dim):
                    super().__init__()
                    self.network = nn.Sequential(
                        nn.Linear(state_dim, hidden_dim),
                        nn.ReLU(),
                        nn.Linear(hidden_dim, hidden_dim),
                        nn.ReLU(),
                        nn.Linear(hidden_dim, action_dim)
                    )
                
                def forward(self, state):
                    return self.network(state)
            
            self.q_network = QNetwork(
                self.config.state_dim,
                self.config.action_dim,
                self.config.hidden_dim
            )
            self.target_network = QNetwork(
                self.config.state_dim,
                self.config.action_dim,
                self.config.hidden_dim
            )
            self.target_network.load_state_dict(self.q_network.state_dict())
            
            self.optimizer = torch.optim.Adam(
                self.q_network.parameters(),
                lr=self.config.learning_rate
            )
            
            logger.info("DQN网络构建成功")
            
        except ImportError:
            logger.warning("PyTorch未安装")
    
    def select_action(self, state: np.ndarray, epsilon: float = 0.1) -> int:
        """选择动作"""
        if self.q_network is None:
            return np.random.randint(self.config.action_dim)
        
        try:
            import torch
            
            if np.random.random() < epsilon:
                return np.random.randint(self.config.action_dim)
            
            with torch.no_grad():
                state_tensor = torch.FloatTensor(state).unsqueeze(0)
                q_values = self.q_network(state_tensor)
                return q_values.argmax(dim=-1).item()
                
        except Exception as e:
            logger.error(f"选择动作失败: {e}")
            return np.random.randint(self.config.action_dim)
    
    def train(self, env: TradingEnvironment, total_steps: int = 100000) -> RLTrainingResult:
        """训练智能体"""
        result = RLTrainingResult(success=False)
        
        if self.q_network is None:
            result.error_message = "网络未构建"
            return result
        
        try:
            import torch
            import torch.nn as nn
            import random
            
            start_time = datetime.now()
            
            state = env.reset()
            episode_reward = 0
            episode_length = 0
            epsilon = 1.0
            
            for step in range(total_steps):
                action = self.select_action(state, epsilon)
                next_state, reward, done, info = env.step(action)
                
                self.memory.append((state, action, reward, next_state, done))
                if len(self.memory) > self.config.buffer_size:
                    self.memory.pop(0)
                
                if len(self.memory) >= self.config.batch_size:
                    self._replay()
                
                if step % self.config.target_update_freq == 0:
                    self.target_network.load_state_dict(self.q_network.state_dict())
                
                episode_reward += reward
                episode_length += 1
                state = next_state
                
                epsilon = max(0.01, epsilon * 0.999)
                
                if done:
                    result.episode_rewards.append(episode_reward)
                    result.episode_lengths.append(episode_length)
                    
                    if episode_reward > result.best_reward:
                        result.best_reward = episode_reward
                        result.best_episode = len(result.episode_rewards)
                    
                    episode_reward = 0
                    episode_length = 0
                    state = env.reset()
                
                if step % 1000 == 0:
                    logger.info(f"Step {step}/{total_steps}, epsilon={epsilon:.3f}")
            
            result.mean_reward = np.mean(result.episode_rewards[-100:]) if result.episode_rewards else 0
            result.std_reward = np.std(result.episode_rewards[-100:]) if result.episode_rewards else 0
            result.training_time = (datetime.now() - start_time).total_seconds()
            result.success = True
            self.is_trained = True
            
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"DQN训练失败: {e}")
        
        return result
    
    def _replay(self):
        """经验回放"""
        try:
            import torch
            import torch.nn as nn
            import random
            
            batch = random.sample(self.memory, self.config.batch_size)
            states, actions, rewards, next_states, dones = zip(*batch)
            
            states = torch.FloatTensor(np.array(states))
            actions = torch.LongTensor(actions)
            rewards = torch.FloatTensor(rewards)
            next_states = torch.FloatTensor(np.array(next_states))
            dones = torch.FloatTensor(dones)
            
            q_values = self.q_network(states).gather(1, actions.unsqueeze(1))
            
            with torch.no_grad():
                next_q_values = self.target_network(next_states).max(1)[0]
                target_q_values = rewards + self.config.gamma * next_q_values * (1 - dones)
            
            loss = nn.MSELoss()(q_values.squeeze(), target_q_values)
            
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            
        except Exception as e:
            logger.error(f"经验回放失败: {e}")
    
    def save(self, path: str):
        """保存模型"""
        try:
            import torch
            
            os.makedirs(os.path.dirname(path), exist_ok=True)
            torch.save({
                'q_network_state_dict': self.q_network.state_dict(),
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
            self.q_network.load_state_dict(checkpoint['q_network_state_dict'])
            self.target_network.load_state_dict(checkpoint['q_network_state_dict'])
            self.is_trained = True
            logger.info(f"模型已从 {path} 加载")
            
        except Exception as e:
            logger.error(f"加载模型失败: {e}")


class RLTradingStrategy:
    """
    强化学习交易策略
    
    使用强化学习进行动态仓位管理，与传统策略并存。
    """
    
    AGENT_MAP = {
        RLAlgorithm.PPO: PPOAgent,
        RLAlgorithm.DQN: DQNAgent,
    }
    
    def __init__(
        self,
        strategy_id: str,
        config: Optional[RLConfig] = None,
        agent_path: Optional[str] = None
    ):
        """
        初始化RL策略
        
        Args:
            strategy_id: 策略ID
            config: RL配置
            agent_path: 预训练智能体路径
        """
        self.strategy_id = strategy_id
        self.config = config or RLConfig()
        self.agent_path = agent_path
        self.agent = None
        self._build_agent()
        
        if agent_path and os.path.exists(agent_path):
            self.agent.load(agent_path)
    
    def _build_agent(self):
        """构建智能体"""
        agent_class = self.AGENT_MAP.get(self.config.algorithm)
        if agent_class is None:
            raise ValueError(f"不支持的算法: {self.config.algorithm}")
        
        self.agent = agent_class(self.config)
    
    def train(
        self,
        market_data: pd.DataFrame,
        factor_data: pd.DataFrame,
        total_steps: int = 100000,
        initial_cash: float = 1000000.0
    ) -> RLTrainingResult:
        """
        训练策略
        
        Args:
            market_data: 市场数据
            factor_data: 因子数据
            total_steps: 总训练步数
            initial_cash: 初始资金
            
        Returns:
            训练结果
        """
        logger.info(f"开始训练RL策略: {self.strategy_id}")
        
        env = TradingEnvironment(
            market_data=market_data,
            factor_data=factor_data,
            initial_cash=initial_cash
        )
        
        result = self.agent.train(env, total_steps)
        
        if result.success:
            logger.info(f"RL策略训练成功，平均奖励: {result.mean_reward:.4f}")
        else:
            logger.error(f"RL策略训练失败: {result.error_message}")
        
        return result
    
    def execute(
        self,
        signals: Dict[str, float],
        current_portfolio: Dict[str, float],
        market_data: pd.DataFrame,
        factor_values: Optional[pd.DataFrame] = None
    ) -> Dict[str, float]:
        """
        执行策略
        
        Args:
            signals: 信号字典 {股票代码: 信号强度}
            current_portfolio: 当前持仓 {股票代码: 持仓权重}
            market_data: 市场数据
            factor_values: 因子值
            
        Returns:
            目标持仓 {股票代码: 目标权重}
        """
        if not self.agent.is_trained:
            logger.warning("智能体未训练，返回当前持仓")
            return current_portfolio
        
        try:
            stocks = list(signals.keys())
            n_stocks = len(stocks)
            
            holdings = np.array([current_portfolio.get(s, 0.0) for s in stocks])
            signal_values = np.array([signals.get(s, 0.0) for s in stocks])
            
            prices = market_data.iloc[-1].values if len(market_data) > 0 else np.ones(n_stocks)
            prices = prices[:n_stocks] if len(prices) >= n_stocks else np.ones(n_stocks)
            
            factors = factor_values.iloc[-1].values if factor_values is not None and len(factor_values) > 0 else np.zeros(n_stocks)
            factors = factors[:n_stocks] if len(factors) >= n_stocks else np.zeros(n_stocks)
            
            portfolio_value = np.sum(holdings * prices) + 1.0
            cash = 1.0
            
            state = np.concatenate([
                holdings,
                [cash / portfolio_value],
                prices / np.max(prices),
                factors,
                signal_values,
                [portfolio_value, 0.0, 0.0, 0.0, 0.0, 0.0]
            ])
            
            if self.config.algorithm == RLAlgorithm.DQN:
                action_idx = self.agent.select_action(state, epsilon=0.0)
                target_weights = np.zeros(n_stocks)
                target_weights[action_idx] = 1.0
            else:
                target_weights = self.agent.select_action(state, deterministic=True)
            
            target_weights = np.clip(target_weights, 0, 1)
            target_weights = target_weights / (np.sum(target_weights) + 1e-8)
            
            target_portfolio = {
                stock: float(weight)
                for stock, weight in zip(stocks, target_weights)
                if weight > 0.01
            }
            
            return target_portfolio
            
        except Exception as e:
            logger.error(f"执行策略失败: {e}")
            return current_portfolio
    
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


def create_rl_strategy(
    strategy_id: str,
    algorithm: str = "ppo",
    agent_path: Optional[str] = None,
    **kwargs
) -> RLTradingStrategy:
    """
    创建RL策略的便捷函数
    
    Args:
        strategy_id: 策略ID
        algorithm: 算法类型
        agent_path: 预训练智能体路径
        **kwargs: 其他配置参数
        
    Returns:
        RLTradingStrategy实例
    """
    algorithm_enum = RLAlgorithm(algorithm)
    config = RLConfig(algorithm=algorithm_enum, **kwargs)
    return RLTradingStrategy(strategy_id, config, agent_path)


_rl_strategy_instance = None


def get_rl_strategy(
    strategy_id: str = "rl_default",
    algorithm: str = "ppo",
    agent_path: Optional[str] = None,
    **kwargs
) -> RLTradingStrategy:
    """
    获取RL策略单例
    
    Args:
        strategy_id: 策略ID
        algorithm: 算法类型
        agent_path: 预训练智能体路径
        **kwargs: 其他配置参数
        
    Returns:
        RLTradingStrategy实例
    """
    global _rl_strategy_instance
    if _rl_strategy_instance is None:
        _rl_strategy_instance = create_rl_strategy(strategy_id, algorithm, agent_path, **kwargs)
    return _rl_strategy_instance


def register_rl_strategy(
    strategy_id: str,
    strategy_name: str,
    algorithm: str = "ppo",
    agent_path: Optional[str] = None,
    description: str = ""
) -> str:
    """
    注册RL策略到策略库
    
    Args:
        strategy_id: 策略ID
        strategy_name: 策略名称
        algorithm: 算法类型
        agent_path: 智能体路径
        description: 描述
        
    Returns:
        策略ID
    """
    config = RLConfig(algorithm=RLAlgorithm(algorithm))
    strategy = RLTradingStrategy(strategy_id, config, agent_path)
    
    metadata = StrategyMetadata(
        id=strategy_id,
        name=strategy_name,
        description=description or f"强化学习策略({algorithm})",
        strategy_type=StrategyType.CUSTOM,
        status=StrategyStatus.TESTING,
        factor_config=FactorCombinationConfig(
            factor_ids=[],
            weights=[],
            combination_method="rl_agent"
        ),
        rebalance_freq=RebalanceFrequency.DAILY
    )
    
    registry = get_strategy_registry()
    registry.register(metadata)
    
    logger.info(f"RL策略已注册: {strategy_id}")
    
    return strategy_id
