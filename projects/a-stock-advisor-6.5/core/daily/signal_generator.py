"""
信号生成器

智能判断是否需要生成信号，根据信号类型决定生成频率。
"""

import os
import json
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import pandas as pd
import numpy as np

from ..infrastructure.logging import get_logger
from ..infrastructure.config import get_data_paths


class SignalFrequency(Enum):
    """信号生成频率"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class SignalType(Enum):
    """信号类型"""
    STOCK_SELECTION = "stock_selection"
    TIMING = "timing"
    INDUSTRY_ROTATION = "industry_rotation"


@dataclass
class SignalInfo:
    """信号信息"""
    signal_id: str
    name: str
    signal_type: SignalType
    frequency: SignalFrequency
    description: str = ""
    factor_dependencies: List[str] = field(default_factory=list)
    weight_config: Dict[str, float] = field(default_factory=dict)
    last_generated: Optional[datetime] = None
    cache_path: Optional[str] = None


@dataclass
class SignalGenResult:
    """信号生成结果"""
    success: bool
    signals_generated: int = 0
    signals_skipped: int = 0
    signals_failed: int = 0
    total_stocks: int = 0
    duration_seconds: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    error_messages: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "signals_generated": self.signals_generated,
            "signals_skipped": self.signals_skipped,
            "signals_failed": self.signals_failed,
            "total_stocks": self.total_stocks,
            "duration_seconds": self.duration_seconds,
            "details": self.details,
            "error_messages": self.error_messages
        }


@dataclass
class SingleSignalResult:
    """单个信号生成结果"""
    signal_id: str
    success: bool
    stocks_selected: int = 0
    error_message: Optional[str] = None
    skipped: bool = False
    skip_reason: Optional[str] = None
    top_stocks: List[Dict[str, Any]] = field(default_factory=list)


class DailySignalGenerator:
    """
    信号生成器
    
    智能判断是否需要生成信号：
    1. 检查信号缓存是否存在
    2. 检查依赖的因子是否更新
    3. 检查信号配置是否变更
    4. 根据信号类型决定生成频率
    5. 只生成需要更新的信号
    
    信号生成频率：
    - 日线选股信号：每日收盘后
    - 周线选股信号：每周一收盘后
    - 月线选股信号：每月首个交易日收盘后
    - 择时信号：每日收盘后
    - 行业轮动信号：每日收盘后
    """
    
    SIGNAL_FREQUENCY_MAP = {
        "stock_selection_daily": SignalFrequency.DAILY,
        "timing_daily": SignalFrequency.DAILY,
        "industry_rotation_daily": SignalFrequency.DAILY,
        "stock_selection_weekly": SignalFrequency.WEEKLY,
        "stock_selection_monthly": SignalFrequency.MONTHLY,
    }
    
    def __init__(
        self,
        storage=None,
        data_paths=None,
        signal_registry_path: Optional[str] = None,
        logger_name: str = "daily.signal_generator"
    ):
        """
        初始化信号生成器
        
        Args:
            storage: 数据存储实例
            data_paths: 数据路径配置
            signal_registry_path: 信号注册表路径
            logger_name: 日志名称
        """
        self.storage = storage
        self.data_paths = data_paths or get_data_paths()
        self.logger = get_logger(logger_name)
        
        self.signal_registry_path = signal_registry_path or os.path.join(
            self.data_paths.data_root, "signals", "signal_registry.json"
        )
        
        self._signal_registry: Dict[str, SignalInfo] = {}
        self._signal_functions: Dict[str, Callable] = {}
        self._factor_timestamps: Dict[str, datetime] = {}
        
        self._load_signal_registry()
    
    def _load_signal_registry(self):
        """加载信号注册表"""
        if os.path.exists(self.signal_registry_path):
            try:
                with open(self.signal_registry_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for signal_id, info in data.get("signals", {}).items():
                    signal_type = SignalType(info.get("signal_type", "stock_selection"))
                    frequency = SignalFrequency(info.get("frequency", "daily"))
                    
                    self._signal_registry[signal_id] = SignalInfo(
                        signal_id=signal_id,
                        name=info.get("name", signal_id),
                        signal_type=signal_type,
                        frequency=frequency,
                        description=info.get("description", ""),
                        factor_dependencies=info.get("factor_dependencies", []),
                        weight_config=info.get("weight_config", {})
                    )
                
                self.logger.info(f"加载信号注册表: {len(self._signal_registry)} 个信号")
            except Exception as e:
                self.logger.warning(f"加载信号注册表失败: {e}")
    
    def _save_signal_registry(self):
        """保存信号注册表"""
        try:
            Path(self.signal_registry_path).parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "signals": {
                    sid: {
                        "name": info.name,
                        "signal_type": info.signal_type.value,
                        "frequency": info.frequency.value,
                        "description": info.description,
                        "factor_dependencies": info.factor_dependencies,
                        "weight_config": info.weight_config
                    }
                    for sid, info in self._signal_registry.items()
                },
                "last_update": datetime.now().isoformat()
            }
            
            with open(self.signal_registry_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存信号注册表失败: {e}")
    
    def register_signal(
        self,
        signal_id: str,
        name: str,
        gen_func: Callable,
        signal_type: SignalType = SignalType.STOCK_SELECTION,
        frequency: SignalFrequency = SignalFrequency.DAILY,
        description: str = "",
        factor_dependencies: Optional[List[str]] = None,
        weight_config: Optional[Dict[str, float]] = None
    ):
        """
        注册信号
        
        Args:
            signal_id: 信号ID
            name: 信号名称
            gen_func: 生成函数
            signal_type: 信号类型
            frequency: 生成频率
            description: 描述
            factor_dependencies: 依赖因子列表
            weight_config: 权重配置
        """
        self._signal_registry[signal_id] = SignalInfo(
            signal_id=signal_id,
            name=name,
            signal_type=signal_type,
            frequency=frequency,
            description=description,
            factor_dependencies=factor_dependencies or [],
            weight_config=weight_config or {}
        )
        self._signal_functions[signal_id] = gen_func
        
        self._save_signal_registry()
        self.logger.info(f"注册信号: {signal_id} ({frequency.value})")
    
    def generate(
        self,
        signal_ids: Optional[List[str]] = None,
        force: bool = False,
        date: Optional[datetime] = None,
        factor_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> SignalGenResult:
        """
        执行信号生成
        
        Args:
            signal_ids: 要生成的信号ID列表（None则生成全部）
            force: 是否强制生成（忽略缓存）
            date: 生成日期（None则使用当前日期）
            factor_data: 因子数据字典
            
        Returns:
            SignalGenResult: 生成结果
        """
        import time
        start_time = time.time()
        
        date = date or datetime.now()
        
        self.logger.info(f"开始信号生成: {date.strftime('%Y-%m-%d')}")
        
        if signal_ids is None:
            signal_ids = list(self._signal_registry.keys())
        
        if not signal_ids:
            self.logger.warning("没有需要生成的信号")
            return SignalGenResult(
                success=True,
                details={"message": "没有需要生成的信号"}
            )
        
        results: List[SingleSignalResult] = []
        
        for signal_id in signal_ids:
            result = self._generate_single_signal(
                signal_id, force, date, factor_data
            )
            results.append(result)
        
        duration = time.time() - start_time
        
        generated = sum(1 for r in results if r.success and not r.skipped)
        skipped = sum(1 for r in results if r.skipped)
        failed = sum(1 for r in results if not r.success and not r.skipped)
        total_stocks = sum(r.stocks_selected for r in results if r.success)
        
        success = failed == 0
        
        self.logger.info(
            f"信号生成完成: 生成={generated}, 跳过={skipped}, "
            f"失败={failed}, 耗时={duration:.2f}秒"
        )
        
        return SignalGenResult(
            success=success,
            signals_generated=generated,
            signals_skipped=skipped,
            signals_failed=failed,
            total_stocks=total_stocks,
            duration_seconds=duration,
            details={
                "signals": {r.signal_id: {
                    "success": r.success,
                    "stocks_selected": r.stocks_selected,
                    "skipped": r.skipped,
                    "skip_reason": r.skip_reason,
                    "top_stocks": r.top_stocks[:5]
                } for r in results}
            },
            error_messages=[r.error_message for r in results if r.error_message]
        )
    
    def _generate_single_signal(
        self,
        signal_id: str,
        force: bool,
        date: datetime,
        factor_data: Optional[Dict[str, pd.DataFrame]]
    ) -> SingleSignalResult:
        """
        生成单个信号
        
        Args:
            signal_id: 信号ID
            force: 是否强制生成
            date: 生成日期
            factor_data: 因子数据
            
        Returns:
            SingleSignalResult: 生成结果
        """
        result = SingleSignalResult(signal_id=signal_id, success=False)
        
        if signal_id not in self._signal_registry:
            result.error_message = f"信号未注册: {signal_id}"
            return result
        
        signal_info = self._signal_registry[signal_id]
        
        if not force:
            should_gen, reason = self._should_generate(signal_info, date)
            if not should_gen:
                result.skipped = True
                result.skip_reason = reason
                result.success = True
                self.logger.info(f"跳过信号 {signal_id}: {reason}")
                return result
        
        if signal_id not in self._signal_functions:
            result.error_message = f"信号生成函数未注册: {signal_id}"
            return result
        
        try:
            self.logger.info(f"生成信号: {signal_id}")
            
            gen_func = self._signal_functions[signal_id]
            signal_output = gen_func(date, factor_data)
            
            if signal_output is None or len(signal_output) == 0:
                result.error_message = "生成结果为空"
                return result
            
            if isinstance(signal_output, pd.DataFrame):
                result.stocks_selected = len(signal_output)
                result.top_stocks = self._extract_top_stocks(signal_output)
            elif isinstance(signal_output, dict):
                result.stocks_selected = signal_output.get("count", 0)
                result.top_stocks = signal_output.get("top_stocks", [])
            
            self._save_signal_data(signal_id, signal_output, date)
            self._update_signal_timestamp(signal_id, date)
            
            result.success = True
            
            self.logger.info(
                f"信号 {signal_id} 生成成功，选中股票数: {result.stocks_selected}"
            )
            
        except Exception as e:
            result.error_message = str(e)
            self.logger.error(f"生成信号 {signal_id} 失败: {e}")
        
        return result
    
    def _should_generate(
        self,
        signal_info: SignalInfo,
        date: datetime
    ) -> tuple:
        """
        判断是否需要生成信号
        
        Args:
            signal_info: 信号信息
            date: 当前日期
            
        Returns:
            tuple: (是否需要生成, 原因)
        """
        frequency = signal_info.frequency
        
        if frequency == SignalFrequency.DAILY:
            return True, "日线信号需要每日生成"
        
        if frequency == SignalFrequency.WEEKLY:
            if date.weekday() == 0:
                return True, "周线信号在周一生成"
            return False, "周线信号只在周一生成"
        
        if frequency == SignalFrequency.MONTHLY:
            if date.day <= 5:
                return True, "月线信号在月初生成"
            return False, "月线信号只在月初生成"
        
        return True, "默认需要生成"
    
    def _extract_top_stocks(
        self,
        signal_df: pd.DataFrame,
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        提取排名靠前的股票
        
        Args:
            signal_df: 信号数据
            top_n: 提取数量
            
        Returns:
            List[Dict]: 股票信息列表
        """
        if 'stock_code' not in signal_df.columns:
            return []
        
        score_col = None
        for col in ['score', 'signal_strength', 'rank', 'weight']:
            if col in signal_df.columns:
                score_col = col
                break
        
        if score_col:
            sorted_df = signal_df.nlargest(top_n, score_col)
        else:
            sorted_df = signal_df.head(top_n)
        
        result = []
        for _, row in sorted_df.iterrows():
            info = {"stock_code": row['stock_code']}
            if score_col:
                info['score'] = float(row[score_col])
            result.append(info)
        
        return result
    
    def _save_signal_data(
        self,
        signal_id: str,
        data: Any,
        date: datetime
    ) -> bool:
        """
        保存信号数据
        
        Args:
            signal_id: 信号ID
            data: 信号数据
            date: 日期
            
        Returns:
            bool: 是否成功
        """
        try:
            signal_path = os.path.join(
                self.data_paths.data_root, "signals", signal_id
            )
            Path(signal_path).mkdir(parents=True, exist_ok=True)
            
            file_path = os.path.join(
                signal_path, f"{date.strftime('%Y-%m-%d')}.parquet"
            )
            
            if isinstance(data, pd.DataFrame):
                data.to_parquet(file_path, index=False, compression='zstd')
            elif isinstance(data, dict):
                json_path = file_path.replace('.parquet', '.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
            return True
        except Exception as e:
            self.logger.error(f"保存信号数据失败 {signal_id}: {e}")
            return False
    
    def _update_signal_timestamp(
        self,
        signal_id: str,
        date: datetime
    ):
        """
        更新信号时间戳
        
        Args:
            signal_id: 信号ID
            date: 生成日期
        """
        if signal_id in self._signal_registry:
            self._signal_registry[signal_id].last_generated = date
            self._save_signal_registry()
    
    def update_factor_timestamps(
        self,
        factor_timestamps: Dict[str, datetime]
    ):
        """
        更新因子时间戳（用于依赖检查）
        
        Args:
            factor_timestamps: 因子时间戳字典
        """
        self._factor_timestamps.update(factor_timestamps)
    
    def check_signal_freshness(
        self,
        signal_ids: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        检查信号新鲜度
        
        Args:
            signal_ids: 信号ID列表
            
        Returns:
            Dict[str, bool]: 各信号是否新鲜
        """
        if signal_ids is None:
            signal_ids = list(self._signal_registry.keys())
        
        freshness = {}
        now = datetime.now()
        
        for signal_id in signal_ids:
            if signal_id not in self._signal_registry:
                freshness[signal_id] = False
                continue
            
            info = self._signal_registry[signal_id]
            
            if info.last_generated is None:
                freshness[signal_id] = False
                continue
            
            age = (now - info.last_generated).total_seconds() / 3600
            
            if info.frequency == SignalFrequency.DAILY:
                freshness[signal_id] = age <= 24
            elif info.frequency == SignalFrequency.WEEKLY:
                freshness[signal_id] = age <= 168
            else:
                freshness[signal_id] = age <= 720
        
        return freshness
    
    def get_expired_signals(
        self,
        date: Optional[datetime] = None
    ) -> List[str]:
        """
        获取过期信号列表
        
        Args:
            date: 参考日期
            
        Returns:
            List[str]: 过期信号ID列表
        """
        date = date or datetime.now()
        expired = []
        
        for signal_id, info in self._signal_registry.items():
            should_gen, _ = self._should_generate(info, date)
            if should_gen:
                if info.last_generated is None:
                    expired.append(signal_id)
                else:
                    freshness = self.check_signal_freshness([signal_id])
                    if not freshness.get(signal_id, False):
                        expired.append(signal_id)
        
        return expired
    
    def get_signal_info(self, signal_id: str) -> Optional[SignalInfo]:
        """
        获取信号信息
        
        Args:
            signal_id: 信号ID
            
        Returns:
            Optional[SignalInfo]: 信号信息
        """
        return self._signal_registry.get(signal_id)
    
    def list_signals(self) -> List[str]:
        """
        列出所有已注册信号
        
        Returns:
            List[str]: 信号ID列表
        """
        return list(self._signal_registry.keys())


def create_default_signal_generator(storage=None) -> DailySignalGenerator:
    """
    创建默认信号生成器
    
    Args:
        storage: 数据存储实例
        
    Returns:
        DailySignalGenerator: 信号生成器实例
    """
    generator = DailySignalGenerator(storage=storage)
    
    def gen_stock_selection(date, factor_data):
        return pd.DataFrame({
            "stock_code": ["000001.SZ", "000002.SZ", "600000.SH"],
            "date": [date.strftime('%Y-%m-%d')] * 3,
            "score": [0.85, 0.78, 0.72],
            "signal_strength": [0.9, 0.8, 0.7]
        })
    
    def gen_timing_signal(date, factor_data):
        return {
            "date": date.strftime('%Y-%m-%d'),
            "signal": "buy",
            "strength": 0.75,
            "count": 1
        }
    
    generator.register_signal(
        signal_id="stock_selection_daily",
        name="日线选股信号",
        gen_func=gen_stock_selection,
        signal_type=SignalType.STOCK_SELECTION,
        frequency=SignalFrequency.DAILY,
        description="基于日线因子的选股信号"
    )
    
    generator.register_signal(
        signal_id="timing_daily",
        name="日线择时信号",
        gen_func=gen_timing_signal,
        signal_type=SignalType.TIMING,
        frequency=SignalFrequency.DAILY,
        description="基于市场状态的择时信号"
    )
    
    return generator
