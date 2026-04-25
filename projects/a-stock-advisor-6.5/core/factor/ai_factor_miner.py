"""
AI因子挖掘器模块

使用深度学习模型自动挖掘因子，支持LSTM、Transformer等模型。
与遗传规划挖掘器并存，提供更多因子挖掘方法。
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import numpy as np

from .registry import FactorMetadata, get_factor_registry
from .classification import FactorCategory, FactorSubCategory
from .validator import FactorValidator, ValidationResult
from ..infrastructure.exceptions import FactorException

logger = logging.getLogger(__name__)


@dataclass
class AIModelConfig:
    """AI模型配置"""
    model_type: str = "lstm"
    input_dim: int = 50
    hidden_dim: int = 64
    num_layers: int = 2
    num_heads: int = 4
    dropout: float = 0.1
    output_dim: int = 1
    seq_length: int = 20
    batch_size: int = 32
    epochs: int = 100
    learning_rate: float = 0.001
    early_stopping_patience: int = 10
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_type": self.model_type,
            "input_dim": self.input_dim,
            "hidden_dim": self.hidden_dim,
            "num_layers": self.num_layers,
            "num_heads": self.num_heads,
            "dropout": self.dropout,
            "output_dim": self.output_dim,
            "seq_length": self.seq_length,
            "batch_size": self.batch_size,
            "epochs": self.epochs,
            "learning_rate": self.learning_rate,
            "early_stopping_patience": self.early_stopping_patience
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AIModelConfig":
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class TrainingResult:
    """训练结果"""
    success: bool
    model_path: Optional[str] = None
    train_loss: List[float] = field(default_factory=list)
    val_loss: List[float] = field(default_factory=list)
    best_epoch: int = 0
    best_val_loss: float = float('inf')
    training_time: float = 0.0
    error_message: Optional[str] = None


@dataclass
class AIFactorResult:
    """AI因子挖掘结果"""
    success: bool
    factor_id: Optional[str] = None
    factor_name: Optional[str] = None
    factor_values: Optional[pd.DataFrame] = None
    ic: float = 0.0
    ir: float = 0.0
    training_result: Optional[TrainingResult] = None
    validation_result: Optional[ValidationResult] = None
    error_message: Optional[str] = None


class FeatureEngineer:
    """特征工程"""
    
    @staticmethod
    def prepare_features(
        market_data: pd.DataFrame,
        feature_columns: Optional[List[str]] = None
    ) -> np.ndarray:
        """
        准备特征
        
        Args:
            market_data: 市场数据，包含OHLCV等
            feature_columns: 指定特征列，如果为None则自动选择
            
        Returns:
            特征数组，shape (n_samples, n_features)
        """
        if feature_columns is None:
            feature_columns = ['open', 'high', 'low', 'close', 'volume']
            feature_columns = [col for col in feature_columns if col in market_data.columns]
        
        features = market_data[feature_columns].values
        
        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
        
        return features
    
    @staticmethod
    def create_sequences(
        features: np.ndarray,
        seq_length: int
    ) -> np.ndarray:
        """
        创建时序序列
        
        Args:
            features: 特征数组，shape (n_samples, n_features)
            seq_length: 序列长度
            
        Returns:
            序列数组，shape (n_samples - seq_length + 1, seq_length, n_features)
        """
        sequences = []
        for i in range(len(features) - seq_length + 1):
            sequences.append(features[i:i + seq_length])
        return np.array(sequences)
    
    @staticmethod
    def normalize_features(
        features: np.ndarray,
        method: str = "zscore"
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        特征标准化
        
        Args:
            features: 特征数组
            method: 标准化方法，zscore或minmax
            
        Returns:
            标准化后的特征，标准化参数
        """
        if method == "zscore":
            mean = np.mean(features, axis=0)
            std = np.std(features, axis=0) + 1e-8
            normalized = (features - mean) / std
            params = {"mean": mean, "std": std}
        elif method == "minmax":
            min_val = np.min(features, axis=0)
            max_val = np.max(features, axis=0)
            range_val = max_val - min_val + 1e-8
            normalized = (features - min_val) / range_val
            params = {"min": min_val, "max": max_val}
        else:
            normalized = features
            params = {}
        
        return normalized, params


class BaseModel:
    """模型基类"""
    
    def __init__(self, config: AIModelConfig):
        self.config = config
        self.model = None
        self.is_trained = False
    
    def build(self):
        """构建模型"""
        raise NotImplementedError
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None
    ) -> TrainingResult:
        """训练模型"""
        raise NotImplementedError
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测"""
        raise NotImplementedError
    
    def save(self, path: str):
        """保存模型"""
        raise NotImplementedError
    
    def load(self, path: str):
        """加载模型"""
        raise NotImplementedError


class LSTMModel(BaseModel):
    """LSTM模型"""
    
    def build(self):
        """构建LSTM模型"""
        try:
            import torch
            import torch.nn as nn
            
            class LSTMNet(nn.Module):
                def __init__(self, input_dim, hidden_dim, num_layers, output_dim, dropout):
                    super().__init__()
                    self.lstm = nn.LSTM(
                        input_dim, 
                        hidden_dim, 
                        num_layers, 
                        batch_first=True,
                        dropout=dropout if num_layers > 1 else 0
                    )
                    self.fc = nn.Linear(hidden_dim, output_dim)
                    self.dropout = nn.Dropout(dropout)
                
                def forward(self, x):
                    lstm_out, _ = self.lstm(x)
                    out = self.dropout(lstm_out[:, -1, :])
                    out = self.fc(out)
                    return out
            
            self.model = LSTMNet(
                self.config.input_dim,
                self.config.hidden_dim,
                self.config.num_layers,
                self.config.output_dim,
                self.config.dropout
            )
            logger.info("LSTM模型构建成功")
            
        except ImportError:
            logger.warning("PyTorch未安装，使用简化版本")
            self.model = None
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None
    ) -> TrainingResult:
        """训练LSTM模型"""
        result = TrainingResult(success=False)
        
        if self.model is None:
            result.error_message = "模型未构建或PyTorch未安装"
            return result
        
        try:
            import torch
            import torch.nn as nn
            from torch.utils.data import DataLoader, TensorDataset
            
            start_time = datetime.now()
            
            X_train_tensor = torch.FloatTensor(X_train)
            y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1)
            
            train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
            train_loader = DataLoader(
                train_dataset, 
                batch_size=self.config.batch_size,
                shuffle=True
            )
            
            criterion = nn.MSELoss()
            optimizer = torch.optim.Adam(
                self.model.parameters(), 
                lr=self.config.learning_rate
            )
            
            best_val_loss = float('inf')
            patience_counter = 0
            
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
                
                if X_val is not None and y_val is not None:
                    self.model.eval()
                    with torch.no_grad():
                        X_val_tensor = torch.FloatTensor(X_val)
                        y_val_tensor = torch.FloatTensor(y_val).unsqueeze(1)
                        val_outputs = self.model(X_val_tensor)
                        val_loss = criterion(val_outputs, y_val_tensor).item()
                        result.val_loss.append(val_loss)
                        
                        if val_loss < best_val_loss:
                            best_val_loss = val_loss
                            patience_counter = 0
                            result.best_epoch = epoch
                            result.best_val_loss = val_loss
                        else:
                            patience_counter += 1
                        
                        if patience_counter >= self.config.early_stopping_patience:
                            logger.info(f"Early stopping at epoch {epoch}")
                            break
                
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
                predictions = self.model(X_tensor).numpy().flatten()
            
            return predictions
            
        except Exception as e:
            logger.error(f"预测失败: {e}")
            raise
    
    def save(self, path: str):
        """保存模型"""
        try:
            import torch
            
            os.makedirs(os.path.dirname(path), exist_ok=True)
            torch.save({
                'model_state_dict': self.model.state_dict(),
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
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.is_trained = True
            logger.info(f"模型已从 {path} 加载")
            
        except Exception as e:
            logger.error(f"加载模型失败: {e}")


class TransformerModel(BaseModel):
    """Transformer模型"""
    
    def build(self):
        """构建Transformer模型"""
        try:
            import torch
            import torch.nn as nn
            
            class TransformerNet(nn.Module):
                def __init__(self, input_dim, hidden_dim, num_heads, num_layers, output_dim, dropout):
                    super().__init__()
                    self.input_projection = nn.Linear(input_dim, hidden_dim)
                    encoder_layer = nn.TransformerEncoderLayer(
                        d_model=hidden_dim,
                        nhead=num_heads,
                        dim_feedforward=hidden_dim * 4,
                        dropout=dropout,
                        batch_first=True
                    )
                    self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
                    self.fc = nn.Linear(hidden_dim, output_dim)
                
                def forward(self, x):
                    x = self.input_projection(x)
                    out = self.transformer(x)
                    out = self.fc(out[:, -1, :])
                    return out
            
            self.model = TransformerNet(
                self.config.input_dim,
                self.config.hidden_dim,
                self.config.num_heads,
                self.config.num_layers,
                self.config.output_dim,
                self.config.dropout
            )
            logger.info("Transformer模型构建成功")
            
        except ImportError:
            logger.warning("PyTorch未安装，使用简化版本")
            self.model = None
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None
    ) -> TrainingResult:
        """训练Transformer模型"""
        result = TrainingResult(success=False)
        
        if self.model is None:
            result.error_message = "模型未构建或PyTorch未安装"
            return result
        
        try:
            import torch
            import torch.nn as nn
            from torch.utils.data import DataLoader, TensorDataset
            
            start_time = datetime.now()
            
            X_train_tensor = torch.FloatTensor(X_train)
            y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1)
            
            train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
            train_loader = DataLoader(
                train_dataset,
                batch_size=self.config.batch_size,
                shuffle=True
            )
            
            criterion = nn.MSELoss()
            optimizer = torch.optim.Adam(
                self.model.parameters(),
                lr=self.config.learning_rate
            )
            
            best_val_loss = float('inf')
            patience_counter = 0
            
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
                
                if X_val is not None and y_val is not None:
                    self.model.eval()
                    with torch.no_grad():
                        X_val_tensor = torch.FloatTensor(X_val)
                        y_val_tensor = torch.FloatTensor(y_val).unsqueeze(1)
                        val_outputs = self.model(X_val_tensor)
                        val_loss = criterion(val_outputs, y_val_tensor).item()
                        result.val_loss.append(val_loss)
                        
                        if val_loss < best_val_loss:
                            best_val_loss = val_loss
                            patience_counter = 0
                            result.best_epoch = epoch
                            result.best_val_loss = val_loss
                        else:
                            patience_counter += 1
                        
                        if patience_counter >= self.config.early_stopping_patience:
                            logger.info(f"Early stopping at epoch {epoch}")
                            break
                
                if epoch % 10 == 0:
                    logger.info(f"Epoch {epoch}: train_loss={train_loss:.6f}")
            
            result.training_time = (datetime.now() - start_time).total_seconds()
            result.success = True
            self.is_trained = True
            
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"Transformer训练失败: {e}")
        
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
                predictions = self.model(X_tensor).numpy().flatten()
            
            return predictions
            
        except Exception as e:
            logger.error(f"预测失败: {e}")
            raise
    
    def save(self, path: str):
        """保存模型"""
        try:
            import torch
            
            os.makedirs(os.path.dirname(path), exist_ok=True)
            torch.save({
                'model_state_dict': self.model.state_dict(),
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
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.is_trained = True
            logger.info(f"模型已从 {path} 加载")
            
        except Exception as e:
            logger.error(f"加载模型失败: {e}")


class MLModel(BaseModel):
    """传统机器学习模型"""
    
    def build(self):
        """构建ML模型"""
        try:
            if self.config.model_type == "xgboost":
                import xgboost as xgb
                self.model = xgb.XGBRegressor(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42
                )
            elif self.config.model_type == "lightgbm":
                import lightgbm as lgb
                self.model = lgb.LGBMRegressor(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42
                )
            elif self.config.model_type == "random_forest":
                from sklearn.ensemble import RandomForestRegressor
                self.model = RandomForestRegressor(
                    n_estimators=100,
                    max_depth=6,
                    random_state=42
                )
            else:
                from sklearn.linear_model import LinearRegression
                self.model = LinearRegression()
            
            logger.info(f"{self.config.model_type}模型构建成功")
            
        except ImportError as e:
            logger.warning(f"依赖库未安装: {e}")
            self.model = None
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None
    ) -> TrainingResult:
        """训练ML模型"""
        result = TrainingResult(success=False)
        
        if self.model is None:
            result.error_message = "模型未构建或依赖库未安装"
            return result
        
        try:
            start_time = datetime.now()
            
            X_train_flat = X_train.reshape(X_train.shape[0], -1)
            
            self.model.fit(X_train_flat, y_train)
            
            train_pred = self.model.predict(X_train_flat)
            train_loss = np.mean((train_pred - y_train) ** 2)
            result.train_loss.append(train_loss)
            
            if X_val is not None and y_val is not None:
                X_val_flat = X_val.reshape(X_val.shape[0], -1)
                val_pred = self.model.predict(X_val_flat)
                val_loss = np.mean((val_pred - y_val) ** 2)
                result.val_loss.append(val_loss)
                result.best_val_loss = val_loss
            
            result.training_time = (datetime.now() - start_time).total_seconds()
            result.success = True
            result.best_epoch = 0
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
    
    def save(self, path: str):
        """保存模型"""
        try:
            import joblib
            
            os.makedirs(os.path.dirname(path), exist_ok=True)
            joblib.dump({
                'model': self.model,
                'config': self.config.to_dict()
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
            self.is_trained = True
            logger.info(f"模型已从 {path} 加载")
            
        except Exception as e:
            logger.error(f"加载模型失败: {e}")


class AIFactorMiner:
    """
    AI因子挖掘器
    
    使用深度学习/机器学习模型挖掘因子，与遗传规划挖掘器并存。
    """
    
    MODEL_MAP = {
        "lstm": LSTMModel,
        "transformer": TransformerModel,
        "xgboost": MLModel,
        "lightgbm": MLModel,
        "random_forest": MLModel,
        "linear": MLModel
    }
    
    def __init__(
        self,
        config: Optional[AIModelConfig] = None,
        model_save_dir: Optional[str] = None
    ):
        """
        初始化AI因子挖掘器
        
        Args:
            config: 模型配置
            model_save_dir: 模型保存目录
        """
        self.config = config or AIModelConfig()
        self.model_save_dir = model_save_dir or "models/ai_factors"
        self.model = None
        self.feature_engineer = FeatureEngineer()
        self.validator = FactorValidator()
        self._build_model()
    
    def _build_model(self):
        """构建模型"""
        model_class = self.MODEL_MAP.get(self.config.model_type)
        if model_class is None:
            raise ValueError(f"不支持的模型类型: {self.config.model_type}")
        
        self.model = model_class(self.config)
        self.model.build()
    
    def prepare_training_data(
        self,
        market_data: pd.DataFrame,
        target_returns: pd.Series,
        seq_length: Optional[int] = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        准备训练数据
        
        Args:
            market_data: 市场数据
            target_returns: 目标收益率
            seq_length: 序列长度
            
        Returns:
            X_train, y_train, X_val, y_val
        """
        seq_length = seq_length or self.config.seq_length
        
        features = self.feature_engineer.prepare_features(market_data)
        features, _ = self.feature_engineer.normalize_features(features)
        
        sequences = self.feature_engineer.create_sequences(features, seq_length)
        
        target = target_returns.values[seq_length - 1:]
        
        min_len = min(len(sequences), len(target))
        sequences = sequences[:min_len]
        target = target[:min_len]
        
        split_idx = int(len(sequences) * 0.8)
        X_train = sequences[:split_idx]
        y_train = target[:split_idx]
        X_val = sequences[split_idx:]
        y_val = target[split_idx:]
        
        return X_train, y_train, X_val, y_val
    
    def mine_factor(
        self,
        market_data: pd.DataFrame,
        target_returns: pd.Series,
        factor_name: str = "ai_factor",
        factor_category: FactorCategory = FactorCategory.TECHNICAL,
        factor_sub_category: FactorSubCategory = FactorSubCategory.TECHNICAL_PATTERN_MOMENTUM,
        validation_threshold: float = 0.02
    ) -> AIFactorResult:
        """
        挖掘AI因子
        
        Args:
            market_data: 市场数据
            target_returns: 目标收益率（未来N日收益率）
            factor_name: 因子名称
            factor_category: 因子类别
            factor_sub_category: 因子子类别
            validation_threshold: 验证阈值（IC绝对值）
            
        Returns:
            AIFactorResult: 挖掘结果
        """
        result = AIFactorResult(success=False)
        
        try:
            logger.info(f"开始挖掘AI因子: {factor_name}")
            
            X_train, y_train, X_val, y_val = self.prepare_training_data(
                market_data, target_returns
            )
            
            logger.info(f"训练数据形状: X_train={X_train.shape}, y_train={y_train.shape}")
            
            training_result = self.model.train(X_train, y_train, X_val, y_val)
            result.training_result = training_result
            
            if not training_result.success:
                result.error_message = f"训练失败: {training_result.error_message}"
                return result
            
            all_features = np.vstack([X_train, X_val])
            factor_values = self.model.predict(all_features)
            
            factor_df = pd.DataFrame({
                'date': market_data.index[self.config.seq_length - 1:][:len(factor_values)],
                'factor_value': factor_values
            })
            factor_df.set_index('date', inplace=True)
            result.factor_values = factor_df
            
            full_target = np.concatenate([y_train, y_val])
            ic = np.corrcoef(factor_values, full_target)[0, 1]
            result.ic = ic if not np.isnan(ic) else 0.0
            
            if abs(result.ic) >= validation_threshold:
                model_path = os.path.join(
                    self.model_save_dir,
                    f"{factor_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
                )
                self.model.save(model_path)
                
                factor_id = f"F_AI_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                factor_metadata = FactorMetadata(
                    id=factor_id,
                    name=factor_name,
                    description=f"AI挖掘因子，模型类型: {self.config.model_type}",
                    formula=f"AI模型({self.config.model_type})",
                    source="AI挖掘",
                    category=factor_category,
                    sub_category=factor_sub_category
                )
                
                registry = get_factor_registry()
                registry.register(factor_metadata)
                
                result.factor_id = factor_id
                result.factor_name = factor_name
                result.success = True
                
                logger.info(f"AI因子挖掘成功: {factor_id}, IC={result.ic:.4f}")
            else:
                result.error_message = f"IC值({result.ic:.4f})低于阈值({validation_threshold})"
                logger.warning(result.error_message)
            
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"AI因子挖掘失败: {e}")
        
        return result
    
    def load_pretrained_model(self, model_path: str):
        """
        加载预训练模型
        
        Args:
            model_path: 模型路径
        """
        self.model.load(model_path)
        logger.info(f"预训练模型已加载: {model_path}")
    
    def generate_factor_values(
        self,
        market_data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        使用已训练模型生成因子值
        
        Args:
            market_data: 市场数据
            
        Returns:
            因子值DataFrame
        """
        if not self.model.is_trained:
            raise ValueError("模型未训练，请先训练或加载模型")
        
        features = self.feature_engineer.prepare_features(market_data)
        features, _ = self.feature_engineer.normalize_features(features)
        sequences = self.feature_engineer.create_sequences(
            features, self.config.seq_length
        )
        
        factor_values = self.model.predict(sequences)
        
        factor_df = pd.DataFrame({
            'date': market_data.index[self.config.seq_length - 1:],
            'factor_value': factor_values
        })
        factor_df.set_index('date', inplace=True)
        
        return factor_df


def create_ai_factor_miner(
    model_type: str = "lstm",
    **kwargs
) -> AIFactorMiner:
    """
    创建AI因子挖掘器的便捷函数
    
    Args:
        model_type: 模型类型
        **kwargs: 其他配置参数
        
    Returns:
        AIFactorMiner实例
    """
    config = AIModelConfig(model_type=model_type, **kwargs)
    return AIFactorMiner(config=config)


_ai_factor_miner_instance = None


def get_ai_factor_miner(
    model_type: str = "lstm",
    **kwargs
) -> AIFactorMiner:
    """
    获取AI因子挖掘器单例
    
    Args:
        model_type: 模型类型
        **kwargs: 其他配置参数
        
    Returns:
        AIFactorMiner实例
    """
    global _ai_factor_miner_instance
    if _ai_factor_miner_instance is None:
        _ai_factor_miner_instance = create_ai_factor_miner(model_type, **kwargs)
    return _ai_factor_miner_instance
