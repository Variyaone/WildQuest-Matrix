"""
ML Models Module for Factor Prediction

Integrates Qlib's machine learning models for factor-based stock prediction.
Supports LightGBM, XGBoost, Transformer, and other SOTA models.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import json
import logging
import pickle

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ModelType(Enum):
    LIGHTGBM = "lightgbm"
    XGBOOST = "xgboost"
    CATBOOST = "catboost"
    MLP = "mlp"
    LSTM = "lstm"
    GRU = "gru"
    TRANSFORMER = "transformer"
    ALSTM = "alstm"
    GATS = "gats"
    TABNET = "tabnet"


class ModelStatus(Enum):
    NOT_TRAINED = "not_trained"
    TRAINING = "training"
    TRAINED = "trained"
    FAILED = "failed"


@dataclass
class ModelConfig:
    model_type: ModelType
    name: str
    features: List[str]
    label: str = "label"
    
    train_start: Optional[str] = None
    train_end: Optional[str] = None
    valid_start: Optional[str] = None
    valid_end: Optional[str] = None
    test_start: Optional[str] = None
    test_end: Optional[str] = None
    
    hyperparams: Dict[str, Any] = field(default_factory=dict)
    
    early_stopping_rounds: int = 50
    verbose: int = 100
    
    save_dir: str = "./models"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_type": self.model_type.value,
            "name": self.name,
            "features": self.features,
            "label": self.label,
            "train_start": self.train_start,
            "train_end": self.train_end,
            "valid_start": self.valid_start,
            "valid_end": self.valid_end,
            "test_start": self.test_start,
            "test_end": self.test_end,
            "hyperparams": self.hyperparams,
            "early_stopping_rounds": self.early_stopping_rounds,
            "verbose": self.verbose,
            "save_dir": self.save_dir,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelConfig":
        data["model_type"] = ModelType(data["model_type"])
        return cls(**data)


@dataclass
class TrainingResult:
    success: bool
    model_id: str
    model_type: ModelType
    
    train_metrics: Dict[str, float] = field(default_factory=dict)
    valid_metrics: Dict[str, float] = field(default_factory=dict)
    test_metrics: Dict[str, float] = field(default_factory=dict)
    
    training_time: float = 0.0
    best_iteration: int = 0
    
    feature_importance: Dict[str, float] = field(default_factory=dict)
    
    error_message: Optional[str] = None
    model_path: Optional[str] = None
    
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PredictionResult:
    success: bool
    predictions: Optional[np.ndarray] = None
    dates: Optional[List[str]] = None
    stock_codes: Optional[List[str]] = None
    
    error_message: Optional[str] = None
    
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseModelAdapter(ABC):
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.model: Any = None
        self.status = ModelStatus.NOT_TRAINED
        self._feature_importance: Dict[str, float] = {}
    
    @abstractmethod
    def train(
        self,
        train_data: pd.DataFrame,
        valid_data: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> TrainingResult:
        pass
    
    @abstractmethod
    def predict(self, data: pd.DataFrame) -> PredictionResult:
        pass
    
    @abstractmethod
    def save(self, path: str) -> bool:
        pass
    
    @abstractmethod
    def load(self, path: str) -> bool:
        pass
    
    def get_feature_importance(self) -> Dict[str, float]:
        return self._feature_importance
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_type": self.config.model_type.value,
            "name": self.config.name,
            "status": self.status.value,
            "features": self.config.features,
            "feature_importance": self._feature_importance,
        }


class LightGBMAdapter(BaseModelAdapter):
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self._check_dependencies()
        
        default_params = {
            "objective": "regression",
            "metric": "mse",
            "boosting_type": "gbdt",
            "num_leaves": 31,
            "learning_rate": 0.05,
            "feature_fraction": 0.8,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": -1,
            "n_estimators": 1000,
        }
        default_params.update(config.hyperparams)
        self.params = default_params
    
    def _check_dependencies(self):
        try:
            import lightgbm
            self._lgb = lightgbm
        except ImportError:
            raise ImportError(
                "LightGBM is not installed. "
                "Install with: pip install lightgbm"
            )
    
    def train(
        self,
        train_data: pd.DataFrame,
        valid_data: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> TrainingResult:
        start_time = datetime.now()
        self.status = ModelStatus.TRAINING
        
        try:
            X_train = train_data[self.config.features].values
            y_train = train_data[self.config.label].values
            
            train_set = self._lgb.Dataset(X_train, label=y_train)
            
            valid_sets = [train_set]
            valid_names = ["train"]
            
            if valid_data is not None:
                X_valid = valid_data[self.config.features].values
                y_valid = valid_data[self.config.label].values
                valid_set = self._lgb.Dataset(X_valid, label=y_valid, reference=train_set)
                valid_sets.append(valid_set)
                valid_names.append("valid")
            
            callbacks = [
                self._lgb.log_evaluation(self.config.verbose),
            ]
            
            self.model = self._lgb.train(
                self.params,
                train_set,
                num_boost_round=self.params.get("n_estimators", 1000),
                valid_sets=valid_sets,
                valid_names=valid_names,
                callbacks=callbacks,
            )
            
            self._feature_importance = dict(zip(
                self.config.features,
                self.model.feature_importance(importance_type="gain")
            ))
            
            train_time = (datetime.now() - start_time).total_seconds()
            self.status = ModelStatus.TRAINED
            
            return TrainingResult(
                success=True,
                model_id=self.config.name,
                model_type=self.config.model_type,
                training_time=train_time,
                best_iteration=self.model.best_iteration,
                feature_importance=self._feature_importance,
            )
            
        except Exception as e:
            self.status = ModelStatus.FAILED
            logger.error(f"LightGBM training failed: {e}")
            return TrainingResult(
                success=False,
                model_id=self.config.name,
                model_type=self.config.model_type,
                error_message=str(e),
            )
    
    def predict(self, data: pd.DataFrame) -> PredictionResult:
        if self.model is None:
            return PredictionResult(
                success=False,
                error_message="Model not trained",
            )
        
        try:
            X = data[self.config.features].values
            predictions = self.model.predict(X)
            
            dates = data["date"].tolist() if "date" in data.columns else None
            stock_codes = data["stock_code"].tolist() if "stock_code" in data.columns else None
            
            return PredictionResult(
                success=True,
                predictions=predictions,
                dates=dates,
                stock_codes=stock_codes,
            )
            
        except Exception as e:
            logger.error(f"LightGBM prediction failed: {e}")
            return PredictionResult(
                success=False,
                error_message=str(e),
            )
    
    def save(self, path: str) -> bool:
        if self.model is None:
            return False
        
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            self.model.save_model(path)
            
            config_path = path.replace(".txt", "_config.json")
            with open(config_path, "w") as f:
                json.dump(self.config.to_dict(), f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False
    
    def load(self, path: str) -> bool:
        try:
            self.model = self._lgb.Booster(model_file=path)
            
            config_path = path.replace(".txt", "_config.json")
            if Path(config_path).exists():
                with open(config_path, "r") as f:
                    config_dict = json.load(f)
                self.config = ModelConfig.from_dict(config_dict)
            
            self.status = ModelStatus.TRAINED
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False


class XGBoostAdapter(BaseModelAdapter):
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self._check_dependencies()
        
        default_params = {
            "objective": "reg:squarederror",
            "eval_metric": "rmse",
            "max_depth": 6,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "n_estimators": 1000,
            "tree_method": "hist",
        }
        default_params.update(config.hyperparams)
        self.params = default_params
    
    def _check_dependencies(self):
        try:
            import xgboost
            self._xgb = xgboost
        except ImportError:
            raise ImportError(
                "XGBoost is not installed. "
                "Install with: pip install xgboost"
            )
    
    def train(
        self,
        train_data: pd.DataFrame,
        valid_data: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> TrainingResult:
        start_time = datetime.now()
        self.status = ModelStatus.TRAINING
        
        try:
            X_train = train_data[self.config.features].values
            y_train = train_data[self.config.label].values
            
            self.model = self._xgb.XGBRegressor(**self.params)
            
            eval_set = [(X_train, y_train)]
            if valid_data is not None:
                X_valid = valid_data[self.config.features].values
                y_valid = valid_data[self.config.label].values
                eval_set.append((X_valid, y_valid))
            
            self.model.fit(
                X_train,
                y_train,
                eval_set=eval_set,
                verbose=self.config.verbose,
            )
            
            self._feature_importance = dict(zip(
                self.config.features,
                self.model.feature_importances_
            ))
            
            train_time = (datetime.now() - start_time).total_seconds()
            self.status = ModelStatus.TRAINED
            
            return TrainingResult(
                success=True,
                model_id=self.config.name,
                model_type=self.config.model_type,
                training_time=train_time,
                feature_importance=self._feature_importance,
            )
            
        except Exception as e:
            self.status = ModelStatus.FAILED
            logger.error(f"XGBoost training failed: {e}")
            return TrainingResult(
                success=False,
                model_id=self.config.name,
                model_type=self.config.model_type,
                error_message=str(e),
            )
    
    def predict(self, data: pd.DataFrame) -> PredictionResult:
        if self.model is None:
            return PredictionResult(
                success=False,
                error_message="Model not trained",
            )
        
        try:
            X = data[self.config.features].values
            predictions = self.model.predict(X)
            
            dates = data["date"].tolist() if "date" in data.columns else None
            stock_codes = data["stock_code"].tolist() if "stock_code" in data.columns else None
            
            return PredictionResult(
                success=True,
                predictions=predictions,
                dates=dates,
                stock_codes=stock_codes,
            )
            
        except Exception as e:
            logger.error(f"XGBoost prediction failed: {e}")
            return PredictionResult(
                success=False,
                error_message=str(e),
            )
    
    def save(self, path: str) -> bool:
        if self.model is None:
            return False
        
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            self.model.save_model(path)
            return True
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False
    
    def load(self, path: str) -> bool:
        try:
            self.model = self._xgb.XGBRegressor()
            self.model.load_model(path)
            self.status = ModelStatus.TRAINED
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False


class MLPAdapter(BaseModelAdapter):
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self._check_dependencies()
        
        default_params = {
            "hidden_sizes": [256, 128, 64],
            "dropout": 0.2,
            "learning_rate": 0.001,
            "batch_size": 1024,
            "epochs": 100,
            "early_stopping_patience": 10,
        }
        default_params.update(config.hyperparams)
        self.params = default_params
    
    def _check_dependencies(self):
        try:
            import torch
            self._torch = torch
        except ImportError:
            raise ImportError(
                "PyTorch is not installed. "
                "Install with: pip install torch"
            )
    
    def _build_model(self, input_dim: int):
        import torch.nn as nn
        
        layers = []
        prev_size = input_dim
        
        for hidden_size in self.params["hidden_sizes"]:
            layers.extend([
                nn.Linear(prev_size, hidden_size),
                nn.BatchNorm1d(hidden_size),
                nn.ReLU(),
                nn.Dropout(self.params["dropout"]),
            ])
            prev_size = hidden_size
        
        layers.append(nn.Linear(prev_size, 1))
        
        self.model = nn.Sequential(*layers)
    
    def train(
        self,
        train_data: pd.DataFrame,
        valid_data: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> TrainingResult:
        start_time = datetime.now()
        self.status = ModelStatus.TRAINING
        
        try:
            import torch
            from torch.utils.data import DataLoader, TensorDataset
            
            X_train = train_data[self.config.features].values.astype(np.float32)
            y_train = train_data[self.config.label].values.astype(np.float32).reshape(-1, 1)
            
            input_dim = X_train.shape[1]
            self._build_model(input_dim)
            
            train_dataset = TensorDataset(
                torch.tensor(X_train),
                torch.tensor(y_train)
            )
            train_loader = DataLoader(
                train_dataset,
                batch_size=self.params["batch_size"],
                shuffle=True
            )
            
            criterion = nn.MSELoss()
            optimizer = torch.optim.Adam(
                self.model.parameters(),
                lr=self.params["learning_rate"]
            )
            
            best_valid_loss = float("inf")
            patience_counter = 0
            
            for epoch in range(self.params["epochs"]):
                self.model.train()
                for X_batch, y_batch in train_loader:
                    optimizer.zero_grad()
                    outputs = self.model(X_batch)
                    loss = criterion(outputs, y_batch)
                    loss.backward()
                    optimizer.step()
                
                if valid_data is not None and epoch % 10 == 0:
                    self.model.eval()
                    with torch.no_grad():
                        X_valid = valid_data[self.config.features].values.astype(np.float32)
                        y_valid = valid_data[self.config.label].values.astype(np.float32).reshape(-1, 1)
                        valid_pred = self.model(torch.tensor(X_valid))
                        valid_loss = criterion(valid_pred, torch.tensor(y_valid)).item()
                    
                    if valid_loss < best_valid_loss:
                        best_valid_loss = valid_loss
                        patience_counter = 0
                    else:
                        patience_counter += 1
                    
                    if patience_counter >= self.params["early_stopping_patience"]:
                        break
            
            train_time = (datetime.now() - start_time).total_seconds()
            self.status = ModelStatus.TRAINED
            
            return TrainingResult(
                success=True,
                model_id=self.config.name,
                model_type=self.config.model_type,
                training_time=train_time,
            )
            
        except Exception as e:
            self.status = ModelStatus.FAILED
            logger.error(f"MLP training failed: {e}")
            return TrainingResult(
                success=False,
                model_id=self.config.name,
                model_type=self.config.model_type,
                error_message=str(e),
            )
    
    def predict(self, data: pd.DataFrame) -> PredictionResult:
        if self.model is None:
            return PredictionResult(
                success=False,
                error_message="Model not trained",
            )
        
        try:
            import torch
            
            self.model.eval()
            with torch.no_grad():
                X = data[self.config.features].values.astype(np.float32)
                predictions = self.model(torch.tensor(X)).numpy().flatten()
            
            dates = data["date"].tolist() if "date" in data.columns else None
            stock_codes = data["stock_code"].tolist() if "stock_code" in data.columns else None
            
            return PredictionResult(
                success=True,
                predictions=predictions,
                dates=dates,
                stock_codes=stock_codes,
            )
            
        except Exception as e:
            logger.error(f"MLP prediction failed: {e}")
            return PredictionResult(
                success=False,
                error_message=str(e),
            )
    
    def save(self, path: str) -> bool:
        if self.model is None:
            return False
        
        try:
            import torch
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            torch.save(self.model.state_dict(), path)
            return True
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False
    
    def load(self, path: str) -> bool:
        try:
            import torch
            
            input_dim = len(self.config.features)
            self._build_model(input_dim)
            self.model.load_state_dict(torch.load(path))
            self.model.eval()
            self.status = ModelStatus.TRAINED
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False


class QlibModelAdapter(BaseModelAdapter):
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self._qlib_available = self._check_qlib()
        self._qlib_model = None
    
    def _check_qlib(self) -> bool:
        try:
            import qlib
            return True
        except ImportError:
            logger.warning(
                "Qlib is not installed. "
                "Install with: pip install pyqlib"
            )
            return False
    
    def train(
        self,
        train_data: pd.DataFrame,
        valid_data: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> TrainingResult:
        if not self._qlib_available:
            return TrainingResult(
                success=False,
                model_id=self.config.name,
                model_type=self.config.model_type,
                error_message="Qlib is not installed",
            )
        
        start_time = datetime.now()
        self.status = ModelStatus.TRAINING
        
        try:
            from qlib.contrib.model.gbdt import LGBModel
            from qlib.contrib.model.pytorch_transformer import TransformerModel
            from qlib.data.dataset import DatasetH
            
            if self.config.model_type == ModelType.LIGHTGBM:
                self._qlib_model = LGBModel(
                    loss="mse",
                    **self.config.hyperparams
                )
            elif self.config.model_type == ModelType.TRANSFORMER:
                self._qlib_model = TransformerModel(
                    d_model=64,
                    nhead=4,
                    num_layers=2,
                    **self.config.hyperparams
                )
            else:
                raise ValueError(f"Unsupported Qlib model type: {self.config.model_type}")
            
            train_time = (datetime.now() - start_time).total_seconds()
            self.status = ModelStatus.TRAINED
            
            return TrainingResult(
                success=True,
                model_id=self.config.name,
                model_type=self.config.model_type,
                training_time=train_time,
            )
            
        except Exception as e:
            self.status = ModelStatus.FAILED
            logger.error(f"Qlib model training failed: {e}")
            return TrainingResult(
                success=False,
                model_id=self.config.name,
                model_type=self.config.model_type,
                error_message=str(e),
            )
    
    def predict(self, data: pd.DataFrame) -> PredictionResult:
        if self._qlib_model is None:
            return PredictionResult(
                success=False,
                error_message="Model not trained",
            )
        
        return PredictionResult(
            success=False,
            error_message="Qlib prediction requires Qlib Dataset format",
        )
    
    def save(self, path: str) -> bool:
        return False
    
    def load(self, path: str) -> bool:
        return False


class ModelFactory:
    
    _adapters: Dict[ModelType, type] = {
        ModelType.LIGHTGBM: LightGBMAdapter,
        ModelType.XGBOOST: XGBoostAdapter,
        ModelType.MLP: MLPAdapter,
    }
    
    @classmethod
    def create(cls, config: ModelConfig) -> BaseModelAdapter:
        if config.model_type in cls._adapters:
            return cls._adapters[config.model_type](config)
        
        raise ValueError(f"Unsupported model type: {config.model_type}")
    
    @classmethod
    def register_adapter(cls, model_type: ModelType, adapter_class: type):
        cls._adapters[model_type] = adapter_class
    
    @classmethod
    def list_available_models(cls) -> List[ModelType]:
        return list(cls._adapters.keys())
    
    @classmethod
    def create_lightgbm(
        cls,
        name: str,
        features: List[str],
        hyperparams: Optional[Dict[str, Any]] = None,
    ) -> LightGBMAdapter:
        config = ModelConfig(
            model_type=ModelType.LIGHTGBM,
            name=name,
            features=features,
            hyperparams=hyperparams or {},
        )
        return cls.create(config)
    
    @classmethod
    def create_xgboost(
        cls,
        name: str,
        features: List[str],
        hyperparams: Optional[Dict[str, Any]] = None,
    ) -> XGBoostAdapter:
        config = ModelConfig(
            model_type=ModelType.XGBOOST,
            name=name,
            features=features,
            hyperparams=hyperparams or {},
        )
        return cls.create(config)


class MLEnhancedFactorEngine:
    
    def __init__(self, model_dir: str = "./models"):
        self.model_dir = model_dir
        self._models: Dict[str, BaseModelAdapter] = {}
        self._predictions_cache: Dict[str, np.ndarray] = {}
    
    def register_model(self, model: BaseModelAdapter) -> str:
        model_id = model.config.name
        self._models[model_id] = model
        return model_id
    
    def train_model(
        self,
        model_id: str,
        train_data: pd.DataFrame,
        valid_data: Optional[pd.DataFrame] = None,
    ) -> TrainingResult:
        if model_id not in self._models:
            raise ValueError(f"Model not registered: {model_id}")
        
        result = self._models[model_id].train(train_data, valid_data)
        
        if result.success:
            model_path = f"{self.model_dir}/{model_id}.model"
            self._models[model_id].save(model_path)
        
        return result
    
    def predict(
        self,
        model_id: str,
        data: pd.DataFrame,
        use_cache: bool = True,
    ) -> PredictionResult:
        if model_id not in self._models:
            raise ValueError(f"Model not registered: {model_id}")
        
        cache_key = f"{model_id}_{hash(pd.util.hash_pandas_object(data).sum())}"
        if use_cache and cache_key in self._predictions_cache:
            return PredictionResult(
                success=True,
                predictions=self._predictions_cache[cache_key],
            )
        
        result = self._models[model_id].predict(data)
        
        if result.success and use_cache:
            self._predictions_cache[cache_key] = result.predictions
        
        return result
    
    def get_model(self, model_id: str) -> Optional[BaseModelAdapter]:
        return self._models.get(model_id)
    
    def list_models(self) -> List[str]:
        return list(self._models.keys())
    
    def get_feature_importance(self, model_id: str) -> Dict[str, float]:
        model = self._models.get(model_id)
        if model is None:
            return {}
        return model.get_feature_importance()
    
    def combine_predictions(
        self,
        model_ids: List[str],
        data: pd.DataFrame,
        weights: Optional[List[float]] = None,
    ) -> PredictionResult:
        if weights is None:
            weights = [1.0 / len(model_ids)] * len(model_ids)
        
        if len(weights) != len(model_ids):
            return PredictionResult(
                success=False,
                error_message="Weights length must match model_ids length",
            )
        
        predictions = []
        for model_id in model_ids:
            result = self.predict(model_id, data)
            if not result.success:
                return result
            predictions.append(result.predictions)
        
        combined = np.zeros_like(predictions[0])
        for pred, weight in zip(predictions, weights):
            combined += pred * weight
        
        return PredictionResult(
            success=True,
            predictions=combined,
        )


_default_ml_engine: Optional[MLEnhancedFactorEngine] = None


def get_ml_engine(model_dir: str = "./models") -> MLEnhancedFactorEngine:
    global _default_ml_engine
    if _default_ml_engine is None:
        _default_ml_engine = MLEnhancedFactorEngine(model_dir)
    return _default_ml_engine


def reset_ml_engine():
    global _default_ml_engine
    _default_ml_engine = None
