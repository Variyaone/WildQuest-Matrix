"""
AI信号生成器模块

使用AI模型生成交易信号，支持分类模型和回归模型。
与传统规则信号生成器并存，提供更多信号生成方法。
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
    SignalMetadata,
    SignalRules,
    SignalDirection,
    SignalStrength,
    SignalType,
    SignalStatus,
    get_signal_registry
)
from .generator import GeneratedSignal, SignalGenerationResult
from ..factor import get_factor_engine
from ..infrastructure.exceptions import SignalException

logger = logging.getLogger(__name__)


class AIModelType(Enum):
    """AI模型类型"""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    PROBABILITY = "probability"


@dataclass
class AISignalConfig:
    """AI信号配置"""
    model_type: str = "lstm"
    task_type: AIModelType = AIModelType.REGRESSION
    input_dim: int = 50
    hidden_dim: int = 64
    num_layers: int = 2
    seq_length: int = 20
    batch_size: int = 32
    epochs: int = 100
    learning_rate: float = 0.001
    threshold_buy: float = 0.02
    threshold_sell: float = -0.02
    confidence_threshold: float = 0.6
    use_probabilistic: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_type": self.model_type,
            "task_type": self.task_type.value,
            "input_dim": self.input_dim,
            "hidden_dim": self.hidden_dim,
            "num_layers": self.num_layers,
            "seq_length": self.seq_length,
            "batch_size": self.batch_size,
            "epochs": self.epochs,
            "learning_rate": self.learning_rate,
            "threshold_buy": self.threshold_buy,
            "threshold_sell": self.threshold_sell,
            "confidence_threshold": self.confidence_threshold,
            "use_probabilistic": self.use_probabilistic
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AISignalConfig":
        if 'task_type' in data and isinstance(data['task_type'], str):
            data['task_type'] = AIModelType(data['task_type'])
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class AISignalTrainingResult:
    """AI信号训练结果"""
    success: bool
    train_loss: List[float] = field(default_factory=list)
    val_loss: List[float] = field(default_factory=list)
    train_accuracy: float = 0.0
    val_accuracy: float = 0.0
    best_epoch: int = 0
    training_time: float = 0.0
    error_message: Optional[str] = None


class AISignalModel:
    """AI信号模型基类"""
    
    def __init__(self, config: AISignalConfig):
        self.config = config
        self.model = None
        self.is_trained = False
        self.feature_columns = []
    
    def build(self):
        """构建模型"""
        raise NotImplementedError
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None
    ) -> AISignalTrainingResult:
        """训练模型"""
        raise NotImplementedError
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测"""
        raise NotImplementedError
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """预测概率"""
        raise NotImplementedError
    
    def save(self, path: str):
        """保存模型"""
        raise NotImplementedError
    
    def load(self, path: str):
        """加载模型"""
        raise NotImplementedError


class LSTMSignalModel(AISignalModel):
    """LSTM信号模型"""
    
    def build(self):
        """构建LSTM模型"""
        try:
            import torch
            import torch.nn as nn
            
            if self.config.task_type == AIModelType.CLASSIFICATION:
                output_dim = 3
            else:
                output_dim = 1
            
            class LSTMNet(nn.Module):
                def __init__(self, input_dim, hidden_dim, num_layers, output_dim):
                    super().__init__()
                    self.lstm = nn.LSTM(
                        input_dim,
                        hidden_dim,
                        num_layers,
                        batch_first=True,
                        dropout=0.1
                    )
                    self.fc = nn.Linear(hidden_dim, output_dim)
                
                def forward(self, x):
                    lstm_out, _ = self.lstm(x)
                    out = self.fc(lstm_out[:, -1, :])
                    return out
            
            self.model = LSTMNet(
                self.config.input_dim,
                self.config.hidden_dim,
                self.config.num_layers,
                output_dim
            )
            logger.info("LSTM信号模型构建成功")
            
        except ImportError:
            logger.warning("PyTorch未安装")
            self.model = None
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None
    ) -> AISignalTrainingResult:
        """训练LSTM模型"""
        result = AISignalTrainingResult(success=False)
        
        if self.model is None:
            result.error_message = "模型未构建"
            return result
        
        try:
            import torch
            import torch.nn as nn
            from torch.utils.data import DataLoader, TensorDataset
            
            start_time = datetime.now()
            
            X_train_tensor = torch.FloatTensor(X_train)
            
            if self.config.task_type == AIModelType.CLASSIFICATION:
                y_train_tensor = torch.LongTensor(y_train)
                criterion = nn.CrossEntropyLoss()
            else:
                y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1)
                criterion = nn.MSELoss()
            
            train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
            train_loader = DataLoader(
                train_dataset,
                batch_size=self.config.batch_size,
                shuffle=True
            )
            
            optimizer = torch.optim.Adam(
                self.model.parameters(),
                lr=self.config.learning_rate
            )
            
            for epoch in range(self.config.epochs):
                self.model.train()
                train_loss = 0.0
                
                for batch_X, batch_y in train_loader:
                    optimizer.zero_grad()
                    outputs = self.model(batch_X)
                    loss = criterion(outputs, batch_y)
                    loss.backward()
                    optimizer.step()
                    train_loss += loss.item()
                
                train_loss /= len(train_loader)
                result.train_loss.append(train_loss)
                
                if epoch % 10 == 0:
                    logger.info(f"Epoch {epoch}: train_loss={train_loss:.6f}")
            
            result.training_time = (datetime.now() - start_time).total_seconds()
            result.success = True
            self.is_trained = True
            
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"LSTM训练失败: {e}")
        
        return result
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测"""
        if self.model is None or not self.is_trained:
            raise ValueError("模型未训练")
        
        try:
            import torch
            
            self.model.eval()
            with torch.no_grad():
                X_tensor = torch.FloatTensor(X)
                outputs = self.model(X_tensor)
                
                if self.config.task_type == AIModelType.CLASSIFICATION:
                    predictions = torch.argmax(outputs, dim=1).numpy()
                else:
                    predictions = outputs.numpy().flatten()
            
            return predictions
            
        except Exception as e:
            logger.error(f"预测失败: {e}")
            raise
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """预测概率"""
        if self.model is None or not self.is_trained:
            raise ValueError("模型未训练")
        
        try:
            import torch
            import torch.nn.functional as F
            
            self.model.eval()
            with torch.no_grad():
                X_tensor = torch.FloatTensor(X)
                outputs = self.model(X_tensor)
                proba = F.softmax(outputs, dim=1).numpy()
            
            return proba
            
        except Exception as e:
            logger.error(f"预测概率失败: {e}")
            raise
    
    def save(self, path: str):
        """保存模型"""
        try:
            import torch
            
            os.makedirs(os.path.dirname(path), exist_ok=True)
            torch.save({
                'model_state_dict': self.model.state_dict(),
                'config': self.config.to_dict(),
                'feature_columns': self.feature_columns
            }, path)
            logger.info(f"模型已保存至 {path}")
            
        except Exception as e:
            logger.error(f"保存模型失败: {e}")
    
    def load(self, path: str):
        """加载模型"""
        try:
            import torch
            
            checkpoint = torch.load(path)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.feature_columns = checkpoint.get('feature_columns', [])
            self.is_trained = True
            logger.info(f"模型已从 {path} 加载")
            
        except Exception as e:
            logger.error(f"加载模型失败: {e}")


class MLSignalModel(AISignalModel):
    """传统机器学习信号模型"""
    
    def build(self):
        """构建ML模型"""
        try:
            if self.config.model_type == "xgboost":
                import xgboost as xgb
                if self.config.task_type == AIModelType.CLASSIFICATION:
                    self.model = xgb.XGBClassifier(
                        n_estimators=100,
                        max_depth=6,
                        learning_rate=0.1,
                        random_state=42,
                        use_label_encoder=False,
                        eval_metric='mlogloss'
                    )
                else:
                    self.model = xgb.XGBRegressor(
                        n_estimators=100,
                        max_depth=6,
                        learning_rate=0.1,
                        random_state=42
                    )
            elif self.config.model_type == "lightgbm":
                import lightgbm as lgb
                if self.config.task_type == AIModelType.CLASSIFICATION:
                    self.model = lgb.LGBMClassifier(
                        n_estimators=100,
                        max_depth=6,
                        learning_rate=0.1,
                        random_state=42
                    )
                else:
                    self.model = lgb.LGBMRegressor(
                        n_estimators=100,
                        max_depth=6,
                        learning_rate=0.1,
                        random_state=42
                    )
            elif self.config.model_type == "random_forest":
                from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
                if self.config.task_type == AIModelType.CLASSIFICATION:
                    self.model = RandomForestClassifier(
                        n_estimators=100,
                        max_depth=6,
                        random_state=42
                    )
                else:
                    self.model = RandomForestRegressor(
                        n_estimators=100,
                        max_depth=6,
                        random_state=42
                    )
            else:
                from sklearn.linear_model import LogisticRegression, LinearRegression
                if self.config.task_type == AIModelType.CLASSIFICATION:
                    self.model = LogisticRegression(random_state=42)
                else:
                    self.model = LinearRegression()
            
            logger.info(f"{self.config.model_type}信号模型构建成功")
            
        except ImportError as e:
            logger.warning(f"依赖库未安装: {e}")
            self.model = None
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None
    ) -> AISignalTrainingResult:
        """训练ML模型"""
        result = AISignalTrainingResult(success=False)
        
        if self.model is None:
            result.error_message = "模型未构建"
            return result
        
        try:
            start_time = datetime.now()
            
            X_train_flat = X_train.reshape(X_train.shape[0], -1)
            
            self.model.fit(X_train_flat, y_train)
            
            train_pred = self.model.predict(X_train_flat)
            
            if self.config.task_type == AIModelType.CLASSIFICATION:
                train_accuracy = np.mean(train_pred == y_train)
                result.train_accuracy = train_accuracy
            else:
                train_loss = np.mean((train_pred - y_train) ** 2)
                result.train_loss.append(train_loss)
            
            if X_val is not None and y_val is not None:
                X_val_flat = X_val.reshape(X_val.shape[0], -1)
                val_pred = self.model.predict(X_val_flat)
                
                if self.config.task_type == AIModelType.CLASSIFICATION:
                    val_accuracy = np.mean(val_pred == y_val)
                    result.val_accuracy = val_accuracy
                else:
                    val_loss = np.mean((val_pred - y_val) ** 2)
                    result.val_loss.append(val_loss)
            
            result.training_time = (datetime.now() - start_time).total_seconds()
            result.success = True
            self.is_trained = True
            
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"ML模型训练失败: {e}")
        
        return result
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测"""
        if self.model is None or not self.is_trained:
            raise ValueError("模型未训练")
        
        X_flat = X.reshape(X.shape[0], -1)
        return self.model.predict(X_flat)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """预测概率"""
        if self.model is None or not self.is_trained:
            raise ValueError("模型未训练")
        
        X_flat = X.reshape(X.shape[0], -1)
        
        if hasattr(self.model, 'predict_proba'):
            return self.model.predict_proba(X_flat)
        else:
            predictions = self.model.predict(X_flat)
            proba = np.zeros((len(predictions), 3))
            for i, pred in enumerate(predictions):
                if pred < 0:
                    proba[i, 0] = 0.7
                elif pred > 0:
                    proba[i, 2] = 0.7
                else:
                    proba[i, 1] = 0.7
            return proba
    
    def save(self, path: str):
        """保存模型"""
        try:
            import joblib
            
            os.makedirs(os.path.dirname(path), exist_ok=True)
            joblib.dump({
                'model': self.model,
                'config': self.config.to_dict(),
                'feature_columns': self.feature_columns
            }, path)
            logger.info(f"模型已保存至 {path}")
            
        except Exception as e:
            logger.error(f"保存模型失败: {e}")
    
    def load(self, path: str):
        """加载模型"""
        try:
            import joblib
            
            checkpoint = joblib.load(path)
            self.model = checkpoint['model']
            self.feature_columns = checkpoint.get('feature_columns', [])
            self.is_trained = True
            logger.info(f"模型已从 {path} 加载")
            
        except Exception as e:
            logger.error(f"加载模型失败: {e}")


class AISignalGenerator:
    """
    AI信号生成器
    
    使用AI模型生成交易信号，与传统信号生成器并存。
    """
    
    MODEL_MAP = {
        "lstm": LSTMSignalModel,
        "transformer": LSTMSignalModel,
        "xgboost": MLSignalModel,
        "lightgbm": MLSignalModel,
        "random_forest": MLSignalModel,
        "linear": MLSignalModel
    }
    
    def __init__(
        self,
        signal_id: str,
        config: Optional[AISignalConfig] = None,
        model_path: Optional[str] = None
    ):
        """
        初始化AI信号生成器
        
        Args:
            signal_id: 信号ID
            config: 模型配置
            model_path: 预训练模型路径
        """
        self.signal_id = signal_id
        self.config = config or AISignalConfig()
        self.model_path = model_path
        self.model = None
        self._build_model()
        
        if model_path and os.path.exists(model_path):
            self.model.load(model_path)
    
    def _build_model(self):
        """构建模型"""
        model_class = self.MODEL_MAP.get(self.config.model_type)
        if model_class is None:
            raise ValueError(f"不支持的模型类型: {self.config.model_type}")
        
        self.model = model_class(self.config)
        self.model.build()
    
    def prepare_features(
        self,
        factor_values: pd.DataFrame,
        market_data: Optional[pd.DataFrame] = None,
        additional_features: Optional[pd.DataFrame] = None
    ) -> np.ndarray:
        """
        准备特征
        
        Args:
            factor_values: 因子值DataFrame
            market_data: 市场数据
            additional_features: 额外特征
            
        Returns:
            特征数组
        """
        features = factor_values.values
        
        if market_data is not None:
            market_features = market_data.values
            if len(market_features) == len(features):
                features = np.hstack([features, market_features])
        
        if additional_features is not None:
            additional = additional_features.values
            if len(additional) == len(features):
                features = np.hstack([features, additional])
        
        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
        
        return features
    
    def create_sequences(
        self,
        features: np.ndarray,
        seq_length: Optional[int] = None
    ) -> np.ndarray:
        """
        创建时序序列
        
        Args:
            features: 特征数组
            seq_length: 序列长度
            
        Returns:
            序列数组
        """
        seq_length = seq_length or self.config.seq_length
        sequences = []
        
        for i in range(len(features) - seq_length + 1):
            sequences.append(features[i:i + seq_length])
        
        return np.array(sequences)
    
    def train(
        self,
        factor_values: pd.DataFrame,
        labels: pd.Series,
        market_data: Optional[pd.DataFrame] = None,
        validation_split: float = 0.2
    ) -> AISignalTrainingResult:
        """
        训练信号模型
        
        Args:
            factor_values: 因子值
            labels: 标签（-1: 卖出, 0: 持有, 1: 买入）或收益率
            market_data: 市场数据
            validation_split: 验证集比例
            
        Returns:
            训练结果
        """
        logger.info(f"开始训练AI信号模型: {self.signal_id}")
        
        features = self.prepare_features(factor_values, market_data)
        sequences = self.create_sequences(features)
        
        labels_aligned = labels.values[self.config.seq_length - 1:]
        min_len = min(len(sequences), len(labels_aligned))
        sequences = sequences[:min_len]
        labels_aligned = labels_aligned[:min_len]
        
        split_idx = int(len(sequences) * (1 - validation_split))
        X_train = sequences[:split_idx]
        y_train = labels_aligned[:split_idx]
        X_val = sequences[split_idx:]
        y_val = labels_aligned[split_idx:]
        
        result = self.model.train(X_train, y_train, X_val, y_val)
        
        if result.success:
            logger.info(f"AI信号模型训练成功")
        else:
            logger.error(f"AI信号模型训练失败: {result.error_message}")
        
        return result
    
    def generate(
        self,
        factor_values: pd.DataFrame,
        market_data: Optional[pd.DataFrame] = None,
        date: Optional[str] = None
    ) -> SignalGenerationResult:
        """
        生成交易信号
        
        Args:
            factor_values: 因子值DataFrame，index为股票代码
            market_data: 市场数据
            date: 信号日期
            
        Returns:
            信号生成结果
        """
        result = SignalGenerationResult(
            success=False,
            signal_id=self.signal_id,
            signals=[]
        )
        
        if not self.model.is_trained:
            result.error_message = "模型未训练"
            return result
        
        try:
            date = date or datetime.now().strftime("%Y-%m-%d")
            
            signals = []
            
            for stock_code in factor_values.index:
                stock_factors = factor_values.loc[[stock_code]]
                features = self.prepare_features(stock_factors, market_data)
                
                if len(features) < self.config.seq_length:
                    continue
                
                sequences = self.create_sequences(features)
                last_sequence = sequences[-1:]
                
                prediction = self.model.predict(last_sequence)[0]
                
                if self.config.use_probabilistic and hasattr(self.model, 'predict_proba'):
                    proba = self.model.predict_proba(last_sequence)[0]
                    confidence = np.max(proba)
                else:
                    confidence = min(abs(prediction), 1.0)
                
                if self.config.task_type == AIModelType.CLASSIFICATION:
                    direction_map = {
                        0: SignalDirection.SELL,
                        1: SignalDirection.HOLD,
                        2: SignalDirection.BUY
                    }
                    direction = direction_map.get(int(prediction), SignalDirection.HOLD)
                else:
                    if prediction > self.config.threshold_buy:
                        direction = SignalDirection.BUY
                    elif prediction < self.config.threshold_sell:
                        direction = SignalDirection.SELL
                    else:
                        direction = SignalDirection.HOLD
                
                if confidence < self.config.confidence_threshold:
                    direction = SignalDirection.HOLD
                
                if abs(prediction) > 0.05:
                    strength = SignalStrength.STRONG
                elif abs(prediction) > 0.02:
                    strength = SignalStrength.MEDIUM
                else:
                    strength = SignalStrength.WEAK
                
                signal = GeneratedSignal(
                    signal_id=self.signal_id,
                    date=date,
                    stock_code=stock_code,
                    direction=direction,
                    strength=strength,
                    score=float(prediction),
                    factor_values=factor_values.loc[stock_code].to_dict(),
                    confidence=confidence
                )
                
                signals.append(signal)
            
            result.signals = signals
            result.total_count = len(signals)
            result.success = True
            
            logger.info(f"生成 {len(signals)} 个AI信号")
            
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"AI信号生成失败: {e}")
        
        return result
    
    def save_model(self, path: Optional[str] = None):
        """
        保存模型
        
        Args:
            path: 保存路径，如果为None则使用初始化时的路径
        """
        path = path or self.model_path
        if path is None:
            raise ValueError("未指定模型保存路径")
        
        self.model.save(path)
        self.model_path = path
    
    def load_model(self, path: str):
        """
        加载模型
        
        Args:
            path: 模型路径
        """
        self.model.load(path)
        self.model_path = path


def create_ai_signal_generator(
    signal_id: str,
    model_type: str = "lstm",
    task_type: str = "regression",
    model_path: Optional[str] = None,
    **kwargs
) -> AISignalGenerator:
    """
    创建AI信号生成器的便捷函数
    
    Args:
        signal_id: 信号ID
        model_type: 模型类型
        task_type: 任务类型（classification或regression）
        model_path: 预训练模型路径
        **kwargs: 其他配置参数
        
    Returns:
        AISignalGenerator实例
    """
    task_type_enum = AIModelType(task_type)
    config = AISignalConfig(
        model_type=model_type,
        task_type=task_type_enum,
        **kwargs
    )
    return AISignalGenerator(signal_id, config, model_path)


def register_ai_signal(
    signal_id: str,
    signal_name: str,
    model_type: str = "lstm",
    model_path: Optional[str] = None,
    description: str = ""
) -> str:
    """
    注册AI信号到信号库
    
    Args:
        signal_id: 信号ID
        signal_name: 信号名称
        model_type: 模型类型
        model_path: 模型路径
        description: 描述
        
    Returns:
        信号ID
    """
    config = AISignalConfig(model_type=model_type)
    generator = AISignalGenerator(signal_id, config, model_path)
    
    metadata = SignalMetadata(
        id=signal_id,
        name=signal_name,
        description=description or f"AI信号({model_type})",
        signal_type=SignalType.STOCK_SELECTION,
        direction=SignalDirection.BUY,
        rules=SignalRules(
            factors=[],
            weights=[],
            threshold=0.0,
            conditions=[],
            combination_method="ai_model"
        ),
        source="AI生成"
    )
    
    registry = get_signal_registry()
    registry.register(metadata)
    
    logger.info(f"AI信号已注册: {signal_id}")
    
    return signal_id
