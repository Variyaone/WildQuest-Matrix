"""
独立回测验证步骤

作为管线的前置步骤运行，结果缓存供后续报告生成使用。
策略回测结果在保质期内有效，只有策略参数变化或数据版本变化时才需要重新回测。
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field

from .backtest_validator import validate_strategy, BacktestValidationResult
from ..infrastructure.logging import get_logger

BACKTEST_CACHE_FILE = Path("./data/cache/backtest_result.json")
BACKTEST_EXPIRE_DAYS = 7

STRATEGY_PARAMS_FILE = Path("./data/cache/strategy_params_hash.json")


@dataclass
class BacktestCacheMeta:
    """回测缓存元数据"""
    last_run: datetime
    expire_days: int
    strategy_hash: str
    data_version: str
    result: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "last_run": self.last_run.isoformat(),
            "expire_days": self.expire_days,
            "strategy_hash": self.strategy_hash,
            "data_version": self.data_version,
            "result": self.result
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BacktestCacheMeta':
        expire_days = data.get("expire_days", BACKTEST_EXPIRE_DAYS)
        if "expire_hours" in data:
            expire_days = data["expire_hours"] / 24.0
        
        return cls(
            last_run=datetime.fromisoformat(data.get("last_run", "2000-01-01")),
            expire_days=expire_days,
            strategy_hash=data.get("strategy_hash", "default"),
            data_version=data.get("data_version", "default"),
            result=data.get("result", {})
        )


def _get_strategy_params_hash() -> str:
    """
    计算策略参数的哈希值
    
    基于以下因素：
    1. 策略代码文件的关键参数
    2. 因子配置
    3. 风控参数
    """
    hash_components = []
    
    strategy_files = [
        "./core/daily/backtest_validator.py",
        "./core/strategy/",
        "./core/factor/",
    ]
    
    for path in strategy_files:
        p = Path(path)
        if p.is_file():
            try:
                content = p.read_text(encoding='utf-8')
                hash_components.append(content)
            except Exception:
                pass
        elif p.is_dir():
            for f in p.glob("**/*.py"):
                try:
                    content = f.read_text(encoding='utf-8')
                    hash_components.append(content)
                except Exception:
                    pass
    
    combined = "\n".join(hash_components)
    return hashlib.md5(combined.encode('utf-8')).hexdigest()[:16]


def _get_data_version() -> str:
    """
    获取数据版本标识
    
    基于最新数据日期
    """
    try:
        data_paths = Path("./data/master/stocks/daily")
        if data_paths.exists():
            parquet_files = list(data_paths.glob("*.parquet"))[:10]
            latest_dates = []
            for f in parquet_files:
                try:
                    import pandas as pd
                    df = pd.read_parquet(f)
                    if 'date' in df.columns and not df.empty:
                        latest = df['date'].max()
                        latest_dates.append(str(latest)[:10])
                except Exception:
                    pass
            if latest_dates:
                return max(latest_dates)
    except Exception:
        pass
    
    return datetime.now().strftime('%Y-%m-%d')


def _load_cache() -> Optional[BacktestCacheMeta]:
    """加载回测缓存"""
    if not BACKTEST_CACHE_FILE.exists():
        return None
    
    try:
        with open(BACKTEST_CACHE_FILE, "r", encoding='utf-8') as f:
            data = json.load(f)
        return BacktestCacheMeta.from_dict(data)
    except Exception:
        return None


def _save_cache(meta: BacktestCacheMeta):
    """保存回测缓存"""
    BACKTEST_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BACKTEST_CACHE_FILE, "w", encoding='utf-8') as f:
        json.dump(meta.to_dict(), f, indent=2, ensure_ascii=False)


def is_backtest_cache_valid() -> bool:
    """
    检查回测缓存是否有效
    
    有效条件：
    1. 缓存文件存在
    2. 未超过保质期（默认7天）
    3. 策略参数未变化（可选）
    4. 数据版本一致或更新（可选）
    """
    cache = _load_cache()
    if cache is None:
        return False
    
    now = datetime.now()
    expire_date = cache.last_run + timedelta(days=cache.expire_days)
    
    if now > expire_date:
        return False
    
    if cache.strategy_hash and cache.strategy_hash != "default":
        current_strategy_hash = _get_strategy_params_hash()
        if cache.strategy_hash != current_strategy_hash:
            return False
    
    return True
    
    return True


def get_backtest_cache_age_hours() -> float:
    """获取缓存已存在的小时数"""
    cache = _load_cache()
    if cache is None:
        return float('inf')
    
    elapsed = datetime.now() - cache.last_run
    return elapsed.total_seconds() / 3600


def get_backtest_cache_remaining_hours() -> float:
    """获取缓存剩余有效小时数"""
    cache = _load_cache()
    if cache is None:
        return 0.0
    
    expire_date = cache.last_run + timedelta(days=cache.expire_days)
    remaining = expire_date - datetime.now()
    return max(0, remaining.total_seconds() / 3600)


def get_cached_backtest_result() -> Optional[Dict[str, Any]]:
    """获取缓存的回测结果"""
    cache = _load_cache()
    if cache is None:
        return None
    return cache.result


def run_backtest_validation(force: bool = False) -> Dict[str, Any]:
    """
    执行回测验证
    
    Args:
        force: 是否强制执行（忽略缓存）
        
    Returns:
        回测结果字典
    """
    logger = get_logger("daily.backtest_validation")
    
    if not force and is_backtest_cache_valid():
        cache = _load_cache()
        age_hours = get_backtest_cache_age_hours()
        remaining_hours = get_backtest_cache_remaining_hours()
        
        print(f"    ✓ 使用缓存回测结果（已缓存 {age_hours:.1f} 小时，剩余 {remaining_hours:.1f} 小时）")
        print(f"      - 年化收益: {cache.result.get('annual_return', 0):.2f}%")
        print(f"      - 夏普比率: {cache.result.get('sharpe_ratio', 0):.2f}")
        print(f"      - 最大回撤: {cache.result.get('max_drawdown', 0):.2f}%")
        print(f"      - 胜率: {cache.result.get('win_rate', 0):.2f}%")
        
        return cache.result
    
    print("    - 执行策略回测验证...")
    
    result = validate_strategy()
    
    if result.success:
        strategy_hash = _get_strategy_params_hash()
        data_version = _get_data_version()
        
        cache_meta = BacktestCacheMeta(
            last_run=datetime.now(),
            expire_days=BACKTEST_EXPIRE_DAYS,
            strategy_hash=strategy_hash,
            data_version=data_version,
            result=result.to_dict()
        )
        
        _save_cache(cache_meta)
        
        print(f"      ✓ 回测年化收益: {result.annual_return*100:.2f}%")
        print(f"      ✓ 夏普比率: {result.sharpe_ratio:.2f}")
        print(f"      ✓ 最大回撤: {result.max_drawdown*100:.2f}%")
        print(f"      ✓ 胜率: {result.win_rate*100:.2f}%")
        print(f"      ✓ 总交易次数: {result.total_trades}")
        print(f"    ✓ 回测结果已缓存（有效期 {BACKTEST_EXPIRE_DAYS} 天）")
        
        return result.to_dict()
    else:
        print(f"      ⚠️ 回测验证失败: {result.error_message}")
        return result.to_dict()


def step0_backtest_validation() -> Dict[str, Any]:
    """
    Step 0: 回测验证（独立前置步骤）
    
    作为管线第一个步骤执行，结果缓存供后续使用。
    """
    print("  [Step 0] 策略回测验证...")
    import time
    start_time = time.time()
    
    result = run_backtest_validation()
    
    elapsed = time.time() - start_time
    
    return {
        "status": "success" if result.get("success", False) else "failed",
        "backtest_result": result,
        "elapsed": elapsed,
        "cache_remaining_hours": get_backtest_cache_remaining_hours()
    }
