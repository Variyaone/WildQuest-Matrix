"""
时点股票池快照机制

解决幸存者偏差问题，确保回测使用历史时点的真实股票池。
"""

from dataclasses import dataclass, field
from typing import Dict, Set, Optional, List, Any
from datetime import date, datetime
from pathlib import Path
import pandas as pd
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class StockPoolSnapshot:
    """股票池快照"""
    snapshot_date: date
    stock_codes: Set[str]
    pool_type: str
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def contains(self, stock_code: str) -> bool:
        """检查股票是否在池中"""
        return stock_code in self.stock_codes
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'snapshot_date': self.snapshot_date.isoformat(),
            'stock_codes': list(self.stock_codes),
            'pool_type': self.pool_type,
            'source': self.source,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StockPoolSnapshot':
        """从字典创建"""
        return cls(
            snapshot_date=date.fromisoformat(data['snapshot_date']),
            stock_codes=set(data['stock_codes']),
            pool_type=data['pool_type'],
            source=data['source'],
            metadata=data.get('metadata', {})
        )


@dataclass
class StockListingInfo:
    """股票上市信息"""
    stock_code: str
    stock_name: str
    list_date: Optional[date]
    delist_date: Optional[date]
    is_delisted: bool
    
    def is_trading_at(self, target_date: date) -> bool:
        """判断指定日期是否在交易"""
        if self.list_date is None:
            return False
        
        if self.list_date > target_date:
            return False
        
        if self.delist_date is not None and self.delist_date <= target_date:
            return False
        
        return True


class StockPoolSnapshotManager:
    """
    股票池快照管理器
    
    管理历史时点的股票池快照，解决幸存者偏差。
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        初始化股票池快照管理器
        
        Args:
            data_dir: 数据目录
        """
        self.data_dir = data_dir or Path("data/stock_pools")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self._snapshots: Dict[str, StockPoolSnapshot] = {}
        self._listing_info: Dict[str, StockListingInfo] = {}
        self._index_constituents: Dict[str, Dict[date, Set[str]]] = {}
        
        self._load_cached_data()
    
    def _load_cached_data(self):
        """加载缓存数据"""
        snapshot_file = self.data_dir / "snapshots.json"
        if snapshot_file.exists():
            try:
                with open(snapshot_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, snap_data in data.items():
                        self._snapshots[key] = StockPoolSnapshot.from_dict(snap_data)
                logger.info(f"加载 {len(self._snapshots)} 个股票池快照")
            except Exception as e:
                logger.warning(f"加载快照缓存失败: {e}")
        
        listing_file = self.data_dir / "listing_info.json"
        if listing_file.exists():
            try:
                with open(listing_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for code, info in data.items():
                        self._listing_info[code] = StockListingInfo(
                            stock_code=code,
                            stock_name=info.get('stock_name', ''),
                            list_date=date.fromisoformat(info['list_date']) if info.get('list_date') else None,
                            delist_date=date.fromisoformat(info['delist_date']) if info.get('delist_date') else None,
                            is_delisted=info.get('is_delisted', False)
                        )
                logger.info(f"加载 {len(self._listing_info)} 个股票上市信息")
            except Exception as e:
                logger.warning(f"加载上市信息缓存失败: {e}")
    
    def _save_cache(self):
        """保存缓存数据"""
        snapshot_file = self.data_dir / "snapshots.json"
        try:
            with open(snapshot_file, 'w', encoding='utf-8') as f:
                json.dump(
                    {k: v.to_dict() for k, v in self._snapshots.items()},
                    f,
                    ensure_ascii=False,
                    indent=2
                )
        except Exception as e:
            logger.error(f"保存快照缓存失败: {e}")
        
        listing_file = self.data_dir / "listing_info.json"
        try:
            with open(listing_file, 'w', encoding='utf-8') as f:
                json.dump(
                    {
                        code: {
                            'stock_name': info.stock_name,
                            'list_date': info.list_date.isoformat() if info.list_date else None,
                            'delist_date': info.delist_date.isoformat() if info.delist_date else None,
                            'is_delisted': info.is_delisted
                        }
                        for code, info in self._listing_info.items()
                    },
                    f,
                    ensure_ascii=False,
                    indent=2
                )
        except Exception as e:
            logger.error(f"保存上市信息缓存失败: {e}")
    
    def register_listing_info(
        self,
        stock_code: str,
        stock_name: str,
        list_date: Optional[date],
        delist_date: Optional[date] = None
    ):
        """
        注册股票上市信息
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            list_date: 上市日期
            delist_date: 退市日期
        """
        self._listing_info[stock_code] = StockListingInfo(
            stock_code=stock_code,
            stock_name=stock_name,
            list_date=list_date,
            delist_date=delist_date,
            is_delisted=(delist_date is not None)
        )
    
    def register_listing_info_batch(self, info_list: List[Dict[str, Any]]):
        """批量注册上市信息"""
        for info in info_list:
            self.register_listing_info(
                stock_code=info['stock_code'],
                stock_name=info.get('stock_name', ''),
                list_date=info.get('list_date'),
                delist_date=info.get('delist_date')
            )
        self._save_cache()
    
    def get_pool_at_date(
        self,
        target_date: date,
        pool_type: str = "全市场",
        use_cache: bool = True
    ) -> StockPoolSnapshot:
        """
        获取指定日期的股票池
        
        Args:
            target_date: 目标日期
            pool_type: 股票池类型（全市场/沪深300/中证500等）
            use_cache: 是否使用缓存
            
        Returns:
            StockPoolSnapshot: 股票池快照
        """
        cache_key = f"{pool_type}_{target_date.isoformat()}"
        
        if use_cache and cache_key in self._snapshots:
            return self._snapshots[cache_key]
        
        if pool_type == "全市场":
            stock_codes = self._get_full_market_at_date(target_date)
        elif pool_type in ["沪深300", "HS300"]:
            stock_codes = self._get_index_constituents_at_date("000300.SH", target_date)
        elif pool_type in ["中证500", "ZZ500"]:
            stock_codes = self._get_index_constituents_at_date("000905.SH", target_date)
        elif pool_type in ["中证1000", "ZZ1000"]:
            stock_codes = self._get_index_constituents_at_date("000852.SH", target_date)
        else:
            logger.warning(f"未知股票池类型: {pool_type}，使用全市场")
            stock_codes = self._get_full_market_at_date(target_date)
        
        snapshot = StockPoolSnapshot(
            snapshot_date=target_date,
            stock_codes=stock_codes,
            pool_type=pool_type,
            source="calculated",
            metadata={
                'stock_count': len(stock_codes),
                'created_at': datetime.now().isoformat()
            }
        )
        
        self._snapshots[cache_key] = snapshot
        self._save_cache()
        
        logger.info(f"生成股票池快照: {target_date} {pool_type} {len(stock_codes)}只")
        
        return snapshot
    
    def _get_full_market_at_date(self, target_date: date) -> Set[str]:
        """获取指定日期的全市场股票"""
        stock_codes = set()
        
        for code, info in self._listing_info.items():
            if info.is_trading_at(target_date):
                stock_codes.add(code)
        
        return stock_codes
    
    def _get_index_constituents_at_date(
        self,
        index_code: str,
        target_date: date
    ) -> Set[str]:
        """
        获取指定日期的指数成分股
        
        Args:
            index_code: 指数代码
            target_date: 目标日期
            
        Returns:
            Set[str]: 成分股代码集合
        """
        if index_code not in self._index_constituents:
            self._load_index_constituents(index_code)
        
        if index_code not in self._index_constituents:
            logger.warning(f"未找到指数 {index_code} 的成分股数据，回退到全市场")
            return self._get_full_market_at_date(target_date)
        
        constituents_by_date = self._index_constituents[index_code]
        
        available_dates = sorted([d for d in constituents_by_date.keys() if d <= target_date], reverse=True)
        
        if not available_dates:
            logger.warning(f"指数 {index_code} 在 {target_date} 之前无成分股数据")
            return self._get_full_market_at_date(target_date)
        
        closest_date = available_dates[0]
        return constituents_by_date[closest_date]
    
    def _load_index_constituents(self, index_code: str):
        """加载指数成分股数据"""
        constituents_file = self.data_dir / f"{index_code}_constituents.json"
        
        if not constituents_file.exists():
            logger.warning(f"指数成分股文件不存在: {constituents_file}")
            return
        
        try:
            with open(constituents_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._index_constituents[index_code] = {
                date.fromisoformat(d): set(codes)
                for d, codes in data.items()
            }
            
            logger.info(f"加载指数 {index_code} 成分股数据: {len(self._index_constituents[index_code])} 个时点")
            
        except Exception as e:
            logger.error(f"加载指数成分股失败: {e}")
    
    def filter_by_pool(
        self,
        df: pd.DataFrame,
        target_date: date,
        pool_type: str = "全市场",
        stock_col: str = "stock_code"
    ) -> pd.DataFrame:
        """
        按股票池过滤DataFrame
        
        Args:
            df: 原始DataFrame
            target_date: 目标日期
            pool_type: 股票池类型
            stock_col: 股票代码列名
            
        Returns:
            pd.DataFrame: 过滤后的DataFrame
        """
        if stock_col not in df.columns:
            logger.warning(f"DataFrame中不存在列: {stock_col}")
            return df
        
        snapshot = self.get_pool_at_date(target_date, pool_type)
        
        mask = df[stock_col].isin(snapshot.stock_codes)
        filtered_df = df[mask].copy()
        
        original_count = len(df)
        filtered_count = len(filtered_df)
        removed_count = original_count - filtered_count
        
        if removed_count > 0:
            logger.info(
                f"股票池过滤: {original_count} → {filtered_count} "
                f"(移除 {removed_count} 只非成分股)"
            )
        
        return filtered_df
    
    def get_pool_statistics(self, pool_type: str = "全市场") -> Dict[str, Any]:
        """获取股票池统计信息"""
        snapshots = [s for s in self._snapshots.values() if s.pool_type == pool_type]
        
        if not snapshots:
            return {
                'pool_type': pool_type,
                'snapshot_count': 0,
                'message': '无快照数据'
            }
        
        stock_counts = [len(s.stock_codes) for s in snapshots]
        
        return {
            'pool_type': pool_type,
            'snapshot_count': len(snapshots),
            'date_range': f"{min(s.snapshot_date for s in snapshots)} ~ {max(s.snapshot_date for s in snapshots)}",
            'avg_stock_count': sum(stock_counts) / len(stock_counts),
            'min_stock_count': min(stock_counts),
            'max_stock_count': max(stock_counts)
        }


def create_snapshot_manager(data_dir: Optional[Path] = None) -> StockPoolSnapshotManager:
    """创建股票池快照管理器"""
    return StockPoolSnapshotManager(data_dir)
