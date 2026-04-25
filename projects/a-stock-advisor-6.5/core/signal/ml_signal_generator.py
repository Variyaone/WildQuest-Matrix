"""
ML Signal Generator Module

Integrates ML models into the signal generation pipeline.
Provides ML-enhanced signal generation capabilities.
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..factor.ml_models import (
    ModelType,
    ModelConfig,
    TrainingResult,
    PredictionResult,
    ModelFactory,
    MLEnhancedFactorEngine,
    get_ml_engine,
)
from ..infrastructure.logging import get_logger
from ..infrastructure.config import get_data_paths


@dataclass
class MLSignalConfig:
    ml_signal_id: str
    name: str
    model_type: ModelType
    features: List[str]
    label: str = "label"
    
    train_lookback: int = 252
    predict_threshold: float = 0.0
    
    rebalance_freq: str = "daily"
    
    top_n: int = 30
    
    hyperparams: Dict[str, Any] = field(default_factory=dict)
    
    model_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ml_signal_id": self.ml_signal_id,
            "name": self.name,
            "model_type": self.model_type.value,
            "features": self.features,
            "label": self.label,
            "train_lookback": self.train_lookback,
            "predict_threshold": self.predict_threshold,
            "rebalance_freq": self.rebalance_freq,
            "top_n": self.top_n,
            "hyperparams": self.hyperparams,
            "model_path": self.model_path,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MLSignalConfig":
        data["model_type"] = ModelType(data["model_type"])
        return cls(**data)


@dataclass
class MLSignalResult:
    success: bool
    signal_id: str
    
    predictions: Optional[np.ndarray] = None
    selected_stocks: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)
    
    model_metrics: Dict[str, float] = field(default_factory=dict)
    feature_importance: Dict[str, float] = field(default_factory=dict)
    
    training_time: float = 0.0
    prediction_time: float = 0.0
    
    error_message: Optional[str] = None
    
    def to_dataframe(self) -> pd.DataFrame:
        if not self.selected_stocks:
            return pd.DataFrame()
        
        return pd.DataFrame({
            "stock_code": self.selected_stocks,
            "score": [self.scores.get(s, 0.0) for s in self.selected_stocks],
            "signal_strength": [abs(self.scores.get(s, 0.0)) for s in self.selected_stocks],
        })


class MLSignalGenerator:
    """
    ML-Enhanced Signal Generator
    
    Generates trading signals using machine learning models.
    Integrates seamlessly with the existing signal pipeline.
    
    Workflow:
    1. Prepare training data from factor values
    2. Train ML model on historical data
    3. Generate predictions for current data
    4. Convert predictions to trading signals
    5. Rank and select top stocks
    
    Example:
        >>> generator = MLSignalGenerator()
        >>> generator.register_ml_signal(
        ...     ml_signal_id="ml_momentum",
        ...     name="ML Momentum Strategy",
        ...     model_type=ModelType.LIGHTGBM,
        ...     features=["momentum_20", "volatility_20", "turnover_rate"],
        ... )
        >>> result = generator.generate_signal("ml_momentum", factor_data, train_data)
    """
    
    def __init__(
        self,
        model_dir: Optional[str] = None,
        config_path: Optional[str] = None,
        logger_name: str = "signal.ml_generator"
    ):
        self.data_paths = get_data_paths()
        self.model_dir = model_dir or os.path.join(self.data_paths.data_root, "ml_models")
        self.config_path = config_path or os.path.join(
            self.data_paths.data_root, "config", "ml_signals.json"
        )
        self.logger = get_logger(logger_name)
        
        self._ml_engine = get_ml_engine(self.model_dir)
        self._signal_configs: Dict[str, MLSignalConfig] = {}
        self._trained_models: Dict[str, str] = {}
        
        self._load_configs()
    
    def _load_configs(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                for signal_id, config in data.get("ml_signals", {}).items():
                    self._signal_configs[signal_id] = MLSignalConfig.from_dict(config)
                
                self.logger.info(f"加载 ML 信号配置: {len(self._signal_configs)} 个")
            except Exception as e:
                self.logger.warning(f"加载 ML 信号配置失败: {e}")
    
    def _save_configs(self):
        try:
            Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "ml_signals": {
                    sid: config.to_dict()
                    for sid, config in self._signal_configs.items()
                },
                "last_update": datetime.now().isoformat(),
            }
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"保存 ML 信号配置失败: {e}")
    
    def register_ml_signal(
        self,
        ml_signal_id: str,
        name: str,
        model_type: ModelType,
        features: List[str],
        label: str = "label",
        train_lookback: int = 252,
        predict_threshold: float = 0.0,
        top_n: int = 30,
        hyperparams: Optional[Dict[str, Any]] = None,
    ) -> str:
        config = MLSignalConfig(
            ml_signal_id=ml_signal_id,
            name=name,
            model_type=model_type,
            features=features,
            label=label,
            train_lookback=train_lookback,
            predict_threshold=predict_threshold,
            top_n=top_n,
            hyperparams=hyperparams or {},
        )
        
        self._signal_configs[ml_signal_id] = config
        
        self._save_configs()
        
        self.logger.info(f"注册 ML 信号: {ml_signal_id} ({model_type.value})")
        
        return ml_signal_id
    
    def _ensure_model_created(self, ml_signal_id: str) -> str:
        if ml_signal_id not in self._signal_configs:
            raise ValueError(f"ML 信号未注册: {ml_signal_id}")
        
        model_id = f"ml_{ml_signal_id}"
        
        if model_id not in self._ml_engine.list_models():
            config = self._signal_configs[ml_signal_id]
            
            model_config = ModelConfig(
                model_type=config.model_type,
                name=model_id,
                features=config.features,
                label=config.label,
                hyperparams=config.hyperparams or {},
                save_dir=self.model_dir,
            )
            
            model = ModelFactory.create(model_config)
            self._ml_engine.register_model(model)
        
        return model_id
    
    def train_model(
        self,
        ml_signal_id: str,
        train_data: pd.DataFrame,
        valid_data: Optional[pd.DataFrame] = None,
    ) -> TrainingResult:
        import time
        start_time = time.time()
        
        if ml_signal_id not in self._signal_configs:
            return TrainingResult(
                success=False,
                model_id=ml_signal_id,
                model_type=ModelType.LIGHTGBM,
                error_message=f"ML 信号未注册: {ml_signal_id}",
            )
        
        config = self._signal_configs[ml_signal_id]
        
        try:
            model_id = self._ensure_model_created(ml_signal_id)
        except ImportError as e:
            return TrainingResult(
                success=False,
                model_id=ml_signal_id,
                model_type=config.model_type,
                error_message=f"依赖未安装: {str(e)}",
            )
        
        result = self._ml_engine.train_model(model_id, train_data, valid_data)
        
        if result.success:
            self._trained_models[ml_signal_id] = model_id
            
            config.model_path = f"{self.model_dir}/{model_id}.model"
            self._save_configs()
        
        self.logger.info(
            f"ML 模型训练完成: {ml_signal_id}, "
            f"耗时={time.time() - start_time:.2f}秒"
        )
        
        return result
    
    def generate_signal(
        self,
        ml_signal_id: str,
        predict_data: pd.DataFrame,
        train_data: Optional[pd.DataFrame] = None,
        force_train: bool = False,
    ) -> MLSignalResult:
        import time
        start_time = time.time()
        
        if ml_signal_id not in self._signal_configs:
            return MLSignalResult(
                success=False,
                signal_id=ml_signal_id,
                error_message=f"ML 信号未注册: {ml_signal_id}",
            )
        
        config = self._signal_configs[ml_signal_id]
        
        try:
            model_id = self._ensure_model_created(ml_signal_id)
        except ImportError as e:
            return MLSignalResult(
                success=False,
                signal_id=ml_signal_id,
                error_message=f"依赖未安装: {str(e)}",
            )
        
        if force_train and train_data is not None:
            train_result = self.train_model(ml_signal_id, train_data)
            if not train_result.success:
                return MLSignalResult(
                    success=False,
                    signal_id=ml_signal_id,
                    error_message=f"模型训练失败: {train_result.error_message}",
                )
        
        if model_id not in self._ml_engine.list_models():
            return MLSignalResult(
                success=False,
                signal_id=ml_signal_id,
                error_message="模型未训练，请先训练模型",
            )
        
        pred_start = time.time()
        pred_result = self._ml_engine.predict(model_id, predict_data)
        
        if not pred_result.success:
            return MLSignalResult(
                success=False,
                signal_id=ml_signal_id,
                error_message=f"预测失败: {pred_result.error_message}",
            )
        
        predictions = pred_result.predictions
        
        stock_codes = predict_data.get("stock_code", pd.Series(range(len(predictions)))).tolist()
        
        scores = dict(zip(stock_codes, predictions))
        
        filtered_scores = {
            s: v for s, v in scores.items()
            if v > config.predict_threshold
        }
        
        sorted_stocks = sorted(
            filtered_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        selected = sorted_stocks[:config.top_n]
        
        feature_importance = self._ml_engine.get_feature_importance(model_id)
        
        result = MLSignalResult(
            success=True,
            signal_id=ml_signal_id,
            predictions=predictions,
            selected_stocks=[s[0] for s in selected],
            scores={s[0]: s[1] for s in selected},
            feature_importance=feature_importance,
            prediction_time=time.time() - pred_start,
        )
        
        self.logger.info(
            f"ML 信号生成完成: {ml_signal_id}, "
            f"选中股票={len(selected)}, "
            f"耗时={time.time() - start_time:.2f}秒"
        )
        
        return result
    
    def generate_ensemble_signal(
        self,
        ml_signal_ids: List[str],
        predict_data: pd.DataFrame,
        weights: Optional[List[float]] = None,
        top_n: int = 30,
    ) -> MLSignalResult:
        import time
        start_time = time.time()
        
        if not ml_signal_ids:
            return MLSignalResult(
                success=False,
                signal_id="ensemble",
                error_message="没有指定 ML 信号",
            )
        
        model_ids = [f"ml_{sid}" for sid in ml_signal_ids]
        
        ensemble_result = self._ml_engine.combine_predictions(
            model_ids,
            predict_data,
            weights,
        )
        
        if not ensemble_result.success:
            return MLSignalResult(
                success=False,
                signal_id="ensemble",
                error_message=f"集成预测失败: {ensemble_result.error_message}",
            )
        
        predictions = ensemble_result.predictions
        stock_codes = predict_data.get("stock_code", pd.Series(range(len(predictions)))).tolist()
        scores = dict(zip(stock_codes, predictions))
        
        sorted_stocks = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        selected = sorted_stocks[:top_n]
        
        result = MLSignalResult(
            success=True,
            signal_id="ensemble",
            predictions=predictions,
            selected_stocks=[s[0] for s in selected],
            scores={s[0]: s[1] for s in selected},
            prediction_time=time.time() - start_time,
        )
        
        self.logger.info(
            f"集成 ML 信号生成完成: {len(ml_signal_ids)} 个模型, "
            f"选中股票={len(selected)}"
        )
        
        return result
    
    def get_signal_config(self, ml_signal_id: str) -> Optional[MLSignalConfig]:
        return self._signal_configs.get(ml_signal_id)
    
    def list_ml_signals(self) -> List[str]:
        return list(self._signal_configs.keys())
    
    def get_feature_importance(self, ml_signal_id: str) -> Dict[str, float]:
        try:
            model_id = self._ensure_model_created(ml_signal_id)
            return self._ml_engine.get_feature_importance(model_id)
        except Exception:
            return {}
    
    def save_model(self, ml_signal_id: str) -> bool:
        if ml_signal_id not in self._trained_models:
            return False
        
        model_id = self._trained_models[ml_signal_id]
        model = self._ml_engine.get_model(model_id)
        
        if model is None:
            return False
        
        model_path = f"{self.model_dir}/{model_id}.model"
        return model.save(model_path)
    
    def load_model(self, ml_signal_id: str) -> bool:
        if ml_signal_id not in self._signal_configs:
            return False
        
        config = self._signal_configs[ml_signal_id]
        
        if config.model_path is None or not os.path.exists(config.model_path):
            return False
        
        try:
            model_id = self._ensure_model_created(ml_signal_id)
        except ImportError:
            return False
        
        model = self._ml_engine.get_model(model_id)
        
        if model.load(config.model_path):
            self._trained_models[ml_signal_id] = model_id
            return True
        
        return False


def prepare_training_data(
    factor_data: pd.DataFrame,
    returns_data: pd.DataFrame,
    features: List[str],
    label: str = "label",
    forward_period: int = 5,
) -> pd.DataFrame:
    training_data = factor_data.copy()
    
    training_data = training_data.sort_values(["stock_code", "date"])
    
    training_data[label] = training_data.groupby("stock_code")["close"].pct_change(forward_period).shift(-forward_period)
    
    training_data = training_data.dropna(subset=features + [label])
    
    return training_data


def create_default_ml_signal_generator() -> MLSignalGenerator:
    generator = MLSignalGenerator()
    
    return generator


_default_ml_generator: Optional[MLSignalGenerator] = None


def get_ml_signal_generator() -> MLSignalGenerator:
    global _default_ml_generator
    if _default_ml_generator is None:
        _default_ml_generator = create_default_ml_signal_generator()
    return _default_ml_generator


def reset_ml_signal_generator():
    global _default_ml_generator
    _default_ml_generator = None
