"""
策略持久化存储模块

管理策略数据的持久化存储。
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import numpy as np

from .registry import StrategyMetadata, get_strategy_registry
from .backtester import Portfolio, Trade
from ..infrastructure.exceptions import StrategyException


@dataclass
class StrategyStorageResult:
    """策略存储结果"""
    success: bool
    strategy_id: str
    file_path: Optional[str] = None
    rows_stored: int = 0
    error_message: Optional[str] = None


class StrategyStorage:
    """策略存储管理器"""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化策略存储
        
        Args:
            storage_path: 存储根路径
        """
        self.storage_path = storage_path or "./data/strategies"
        self._registry = get_strategy_registry()
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保存储目录存在"""
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)
        
        subdirs = ["portfolios", "trades", "performance", "metadata"]
        for subdir in subdirs:
            Path(os.path.join(self.storage_path, subdir)).mkdir(parents=True, exist_ok=True)
    
    def _get_portfolio_path(self, strategy_id: str) -> str:
        """获取组合数据文件路径"""
        return os.path.join(self.storage_path, "portfolios", f"{strategy_id}.parquet")
    
    def _get_trades_path(self, strategy_id: str) -> str:
        """获取交易记录文件路径"""
        return os.path.join(self.storage_path, "trades", f"{strategy_id}.parquet")
    
    def _get_performance_path(self, strategy_id: str) -> str:
        """获取绩效数据文件路径"""
        return os.path.join(self.storage_path, "performance", f"{strategy_id}.json")
    
    def _get_metadata_path(self, strategy_id: str) -> str:
        """获取元数据文件路径"""
        return os.path.join(self.storage_path, "metadata", f"{strategy_id}.json")
    
    def save_portfolios(
        self,
        strategy_id: str,
        portfolios: List[Portfolio],
        compress: str = "zstd"
    ) -> StrategyStorageResult:
        """保存组合数据"""
        try:
            data = []
            for p in portfolios:
                positions_data = {}
                for code, pos in p.positions.items():
                    positions_data[code] = {
                        "shares": pos.shares,
                        "cost_price": pos.cost_price,
                        "current_price": pos.current_price,
                        "market_value": pos.market_value,
                        "profit_loss": pos.profit_loss,
                        "profit_loss_pct": pos.profit_loss_pct
                    }
                
                data.append({
                    "date": p.date,
                    "cash": p.cash,
                    "positions": json.dumps(positions_data),
                    "total_value": p.total_value,
                    "daily_return": p.daily_return
                })
            
            df = pd.DataFrame(data)
            
            file_path = self._get_portfolio_path(strategy_id)
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            df.to_parquet(file_path, index=False, compression=compress)
            
            return StrategyStorageResult(
                success=True,
                strategy_id=strategy_id,
                file_path=file_path,
                rows_stored=len(portfolios)
            )
            
        except Exception as e:
            return StrategyStorageResult(
                success=False,
                strategy_id=strategy_id,
                error_message=str(e)
            )
    
    def load_portfolios(
        self,
        strategy_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[List[Portfolio]]:
        """加载组合数据"""
        try:
            file_path = self._get_portfolio_path(strategy_id)
            
            if not os.path.exists(file_path):
                return None
            
            df = pd.read_parquet(file_path)
            
            if start_date:
                df = df[df['date'] >= start_date]
            if end_date:
                df = df[df['date'] <= end_date]
            
            portfolios = []
            for _, row in df.iterrows():
                positions_data = json.loads(row['positions']) if isinstance(row['positions'], str) else row['positions']
                
                positions = {}
                for code, pos_data in positions_data.items():
                    from .backtester import Position
                    positions[code] = Position(
                        stock_code=code,
                        shares=pos_data['shares'],
                        cost_price=pos_data['cost_price'],
                        current_price=pos_data['current_price'],
                        market_value=pos_data['market_value'],
                        profit_loss=pos_data['profit_loss'],
                        profit_loss_pct=pos_data['profit_loss_pct']
                    )
                
                portfolios.append(Portfolio(
                    date=row['date'],
                    cash=row['cash'],
                    positions=positions,
                    total_value=row['total_value'],
                    daily_return=row.get('daily_return', 0)
                ))
            
            return portfolios
            
        except Exception as e:
            print(f"加载组合数据失败 {strategy_id}: {e}")
            return None
    
    def save_trades(
        self,
        strategy_id: str,
        trades: List[Trade],
        compress: str = "zstd"
    ) -> StrategyStorageResult:
        """保存交易记录"""
        try:
            data = [t.to_dict() for t in trades]
            
            if not data:
                return StrategyStorageResult(
                    success=True,
                    strategy_id=strategy_id,
                    rows_stored=0
                )
            
            df = pd.DataFrame(data)
            
            file_path = self._get_trades_path(strategy_id)
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            df.to_parquet(file_path, index=False, compression=compress)
            
            return StrategyStorageResult(
                success=True,
                strategy_id=strategy_id,
                file_path=file_path,
                rows_stored=len(trades)
            )
            
        except Exception as e:
            return StrategyStorageResult(
                success=False,
                strategy_id=strategy_id,
                error_message=str(e)
            )
    
    def load_trades(
        self,
        strategy_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[List[Trade]]:
        """加载交易记录"""
        try:
            file_path = self._get_trades_path(strategy_id)
            
            if not os.path.exists(file_path):
                return None
            
            df = pd.read_parquet(file_path)
            
            if start_date:
                df = df[df['date'] >= start_date]
            if end_date:
                df = df[df['date'] <= end_date]
            
            trades = []
            for _, row in df.iterrows():
                trades.append(Trade(
                    date=row['date'],
                    stock_code=row['stock_code'],
                    direction=row['direction'],
                    shares=row['shares'],
                    price=row['price'],
                    amount=row['amount'],
                    commission=row['commission']
                ))
            
            return trades
            
        except Exception as e:
            print(f"加载交易记录失败 {strategy_id}: {e}")
            return None
    
    def save_performance(
        self,
        strategy_id: str,
        performance: Dict[str, Any]
    ) -> StrategyStorageResult:
        """保存绩效数据"""
        try:
            file_path = self._get_performance_path(strategy_id)
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            performance['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(performance, f, ensure_ascii=False, indent=2)
            
            return StrategyStorageResult(
                success=True,
                strategy_id=strategy_id,
                file_path=file_path
            )
            
        except Exception as e:
            return StrategyStorageResult(
                success=False,
                strategy_id=strategy_id,
                error_message=str(e)
            )
    
    def load_performance(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """加载绩效数据"""
        try:
            file_path = self._get_performance_path(strategy_id)
            
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
            
        except Exception as e:
            print(f"加载绩效数据失败 {strategy_id}: {e}")
            return None
    
    def save_strategy_metadata(
        self,
        strategy: StrategyMetadata
    ) -> StrategyStorageResult:
        """保存策略元数据"""
        try:
            file_path = self._get_metadata_path(strategy.id)
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(strategy.to_dict(), f, ensure_ascii=False, indent=2)
            
            return StrategyStorageResult(
                success=True,
                strategy_id=strategy.id,
                file_path=file_path
            )
            
        except Exception as e:
            return StrategyStorageResult(
                success=False,
                strategy_id=strategy.id,
                error_message=str(e)
            )
    
    def load_strategy_metadata(self, strategy_id: str) -> Optional[StrategyMetadata]:
        """加载策略元数据"""
        try:
            file_path = self._get_metadata_path(strategy_id)
            
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return StrategyMetadata.from_dict(data)
            
        except Exception as e:
            print(f"加载策略元数据失败 {strategy_id}: {e}")
            return None
    
    def list_strategy_ids(self) -> List[str]:
        """列出所有已存储的策略ID"""
        portfolios_path = os.path.join(self.storage_path, "portfolios")
        
        if not os.path.exists(portfolios_path):
            return []
        
        strategy_ids = []
        for file in Path(portfolios_path).glob("*.parquet"):
            strategy_ids.append(file.stem)
        
        return sorted(strategy_ids)
    
    def delete_strategy_data(self, strategy_id: str) -> bool:
        """删除策略数据"""
        try:
            files = [
                self._get_portfolio_path(strategy_id),
                self._get_trades_path(strategy_id),
                self._get_performance_path(strategy_id),
                self._get_metadata_path(strategy_id)
            ]
            
            for file_path in files:
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            return True
            
        except Exception as e:
            print(f"删除策略数据失败 {strategy_id}: {e}")
            return False
    
    def get_storage_info(self) -> Dict[str, Any]:
        """获取存储信息"""
        strategy_ids = self.list_strategy_ids()
        
        total_size = 0
        for subdir in ["portfolios", "trades", "performance", "metadata"]:
            subdir_path = os.path.join(self.storage_path, subdir)
            if os.path.exists(subdir_path):
                for file in Path(subdir_path).glob("*"):
                    if file.is_file():
                        total_size += file.stat().st_size
        
        return {
            "storage_path": self.storage_path,
            "total_strategies": len(strategy_ids),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024)
        }


_default_storage: Optional[StrategyStorage] = None


def get_strategy_storage(storage_path: Optional[str] = None) -> StrategyStorage:
    """获取全局策略存储实例"""
    global _default_storage
    if storage_path is not None or _default_storage is None:
        _default_storage = StrategyStorage(storage_path)
    return _default_storage


def reset_strategy_storage():
    """重置全局策略存储"""
    global _default_storage
    _default_storage = None
