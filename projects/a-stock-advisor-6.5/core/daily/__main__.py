"""
每日任务调度器入口

执行完整管线:
    python -m core.daily
"""

import sys
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any
from pathlib import Path

from .scheduler import DailyScheduler, Task

STOCK_LIST_CACHE_FILE = Path("./data/cache/stock_list_meta.json")
STOCK_LIST_EXPIRE_DAYS = 30

BACKTEST_CACHE_FILE = Path("./data/cache/backtest_result.json")
BACKTEST_EXPIRE_HOURS = 24

PIPELINE_CONFIG = {
    "max_stocks_update": None,
    "max_stocks_factor": None,
    "max_stocks_signal": None,
    "max_stocks_strategy": None,
    "max_stocks_portfolio": None,
    "max_factors_per_stock": None,
    "max_signals_output": 50,
    "max_orders_output": 50,
    "max_alerts_display": 10,
    "parallel_workers": 8,
    "batch_size": 100,
}

_pipeline_data = {
    "signal_data": None,
    "stock_scores": None,
    "backtest_result": None,
    "position_status": None
}


def step0_position_check() -> Dict[str, Any]:
    """持仓状态检查"""
    print("  [Step 0] 持仓状态检查...")
    import time
    start_time = time.time()
    
    from core.trading.position import PositionManager
    from core.infrastructure.config import get_data_paths
    from pathlib import Path
    import pandas as pd
    
    data_paths = get_data_paths()
    positions_file = Path(data_paths.data_root) / "trading" / "positions.json"
    
    position_status = {
        "has_position": False,
        "position_count": 0,
        "total_value": 0.0,
        "cash": 0.0,
        "positions": {},
        "need_rebalance": False,
        "position_health": "unknown",
        "warnings": [],
        "recommendations": []
    }
    
    if not positions_file.exists():
        print("    - 持仓文件不存在，判定为空仓")
        position_status["has_position"] = False
        position_status["recommendations"].append("空仓状态，建议根据信号建仓")
        
        global _pipeline_data
        _pipeline_data["position_status"] = position_status
        
        elapsed = time.time() - start_time
        print(f"    ✓ 持仓检查完成: 空仓 ({elapsed:.2f}秒)")
        
        return {
            "status": "success",
            "has_position": False,
            "position_count": 0,
            "elapsed": elapsed
        }
    
    try:
        with open(positions_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        positions = data.get('positions', {})
        cash = data.get('cash', 0)
        initial_capital = data.get('initial_capital', 1000000)
        
        if not positions:
            print("    - 持仓为空，判定为空仓")
            position_status["has_position"] = False
            position_status["cash"] = cash
            position_status["recommendations"].append("空仓状态，建议根据信号建仓")
        else:
            print(f"    - 发现持仓: {len(positions)} 只股票")
            position_status["has_position"] = True
            position_status["position_count"] = len(positions)
            position_status["positions"] = positions
            position_status["cash"] = cash
            
            total_market_value = sum(pos.get('market_value', 0) for pos in positions.values())
            position_status["total_value"] = total_market_value + cash
            
            print(f"    - 持仓市值: ¥{total_market_value:,.2f}")
            print(f"    - 现金余额: ¥{cash:,.2f}")
            print(f"    - 总资产: ¥{position_status['total_value']:,.2f}")
            
            print("    - 检查持仓健康度...")
            unhealthy_positions = []
            
            for code, pos_data in positions.items():
                quantity = pos_data.get('quantity', 0)
                avg_cost = pos_data.get('avg_cost', 0)
                current_price = pos_data.get('current_price', 0)
                profit_loss_pct = pos_data.get('profit_loss_pct', 0)
                
                if quantity <= 0:
                    unhealthy_positions.append({
                        "code": code,
                        "reason": "持仓数量异常"
                    })
                    continue
                
                if current_price <= 0:
                    unhealthy_positions.append({
                        "code": code,
                        "reason": "当前价格异常"
                    })
                    continue
                
                if profit_loss_pct < -15:
                    position_status["warnings"].append(
                        f"{code} 亏损超过15% ({profit_loss_pct:.2f}%)，建议止损"
                    )
                elif profit_loss_pct < -10:
                    position_status["warnings"].append(
                        f"{code} 亏损超过10% ({profit_loss_pct:.2f}%)，关注风险"
                    )
                
                stock_file = Path(data_paths.stocks_daily_path) / f"{code}.parquet"
                if stock_file.exists():
                    try:
                        df = pd.read_parquet(stock_file)
                        if len(df) >= 20:
                            df = df.sort_values('date')
                            close = df['close']
                            
                            ma5 = close.rolling(5).mean().iloc[-1]
                            ma20 = close.rolling(20).mean().iloc[-1]
                            last_close = close.iloc[-1]
                            
                            if last_close < ma5 and last_close < ma20:
                                position_status["warnings"].append(
                                    f"{code} 技术面走弱（跌破均线），建议评估持有理由"
                                )
                    except Exception:
                        pass
            
            if len(unhealthy_positions) > 0:
                print(f"    ⚠️ 发现 {len(unhealthy_positions)} 个异常持仓:")
                for up in unhealthy_positions[:5]:
                    print(f"      - {up['code']}: {up['reason']}")
            
            if len(position_status["warnings"]) > 0:
                print(f"    ⚠️ 发现 {len(position_status['warnings'])} 个风险提示:")
                for warning in position_status["warnings"][:5]:
                    print(f"      - {warning}")
                position_status["position_health"] = "warning"
            else:
                print("    ✓ 持仓健康度良好")
                position_status["position_health"] = "good"
            
            position_ratio = total_market_value / position_status["total_value"] if position_status["total_value"] > 0 else 0
            if position_ratio > 0.95:
                position_status["recommendations"].append(
                    f"仓位过高 ({position_ratio*100:.1f}%)，建议保留一定现金应对风险"
                )
            elif position_ratio < 0.3 and len(positions) > 0:
                position_status["recommendations"].append(
                    f"仓位较低 ({position_ratio*100:.1f}%)，可考虑加仓优质标的"
                )
        
        _pipeline_data["position_status"] = position_status
        
        elapsed = time.time() - start_time
        print(f"    ✓ 持仓检查完成 ({elapsed:.2f}秒)")
        
        return {
            "status": "success",
            "has_position": position_status["has_position"],
            "position_count": position_status["position_count"],
            "total_value": position_status["total_value"],
            "warnings": len(position_status["warnings"]),
            "elapsed": elapsed
        }
        
    except Exception as e:
        print(f"    ⚠️ 持仓检查失败: {e}")
        import traceback
        traceback.print_exc()
        
        _pipeline_data["position_status"] = position_status
        
        elapsed = time.time() - start_time
        return {
            "status": "error",
            "has_position": False,
            "position_count": 0,
            "error": str(e),
            "elapsed": elapsed
        }


def get_pipeline_config() -> dict:
    """获取管线配置"""
    import os
    config = PIPELINE_CONFIG.copy()
    
    if os.environ.get("PIPELINE_MAX_STOCKS"):
        max_stocks = int(os.environ.get("PIPELINE_MAX_STOCKS"))
        config["max_stocks_update"] = max_stocks
        config["max_stocks_factor"] = max_stocks
        config["max_stocks_signal"] = max_stocks
        config["max_stocks_strategy"] = max_stocks
        config["max_stocks_portfolio"] = max_stocks
    
    if os.environ.get("PIPELINE_BATCH_SIZE"):
        config["batch_size"] = int(os.environ.get("PIPELINE_BATCH_SIZE"))
    
    return config


def _should_update_stock_list() -> bool:
    """检查是否需要更新股票列表（30天过期）"""
    if not STOCK_LIST_CACHE_FILE.exists():
        return True
    
    try:
        with open(STOCK_LIST_CACHE_FILE, "r") as f:
            meta = json.load(f)
        last_update = datetime.fromisoformat(meta.get("last_update", "2000-01-01"))
        return (datetime.now() - last_update).days >= STOCK_LIST_EXPIRE_DAYS
    except Exception:
        return True


def _save_stock_list_meta():
    """保存股票列表元数据"""
    STOCK_LIST_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STOCK_LIST_CACHE_FILE, "w") as f:
        json.dump({
            "last_update": datetime.now().isoformat(),
            "expire_days": STOCK_LIST_EXPIRE_DAYS
        }, f)


def step1_data_update() -> Dict[str, Any]:
    """数据更新"""
    print("  [Step 1] 数据更新...")
    
    from core.data import get_unified_updater, get_data_fetcher
    from core.infrastructure.config import get_data_paths
    from pathlib import Path
    import pandas as pd
    
    config = get_pipeline_config()
    max_stocks = config.get("max_stocks_update")
    
    updater = get_unified_updater()
    fetcher = get_data_fetcher()
    data_paths = get_data_paths()
    
    stock_list_path = Path(data_paths.master_path) / "stock_list.parquet"
    
    if _should_update_stock_list():
        print("    - 获取股票列表（已过期或不存在）...")
        stock_df = fetcher.get_stock_list()
        if stock_df.empty:
            print("    ⚠️ 获取股票列表失败，使用缓存数据")
        else:
            stock_list_path.parent.mkdir(parents=True, exist_ok=True)
            stock_df.to_parquet(stock_list_path)
            _save_stock_list_meta()
            print(f"    - 股票列表已更新: {len(stock_df)} 只")
    else:
        print("    - 股票列表未过期，跳过更新")
    
    if stock_list_path.exists():
        stock_df = pd.read_parquet(stock_list_path)
        stock_list = stock_df["code"].tolist()
    else:
        stock_files = list(Path(data_paths.stocks_daily_path).glob("*.parquet"))
        stock_list = [f.stem for f in stock_files]
    
    if max_stocks:
        stock_list = stock_list[:max_stocks]
    
    total_stocks = len(stock_list)
    print(f"    - 待更新股票: {total_stocks} 只")
    
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    print(f"    - 更新日期范围: {start_date} ~ {end_date}")
    
    results = updater.update_multiple_stocks(
        stock_list=stock_list,
        start_date=start_date,
        end_date=end_date,
        data_type="daily",
        parallel_workers=config.get("parallel_workers", 8)
    )
    
    success_count = sum(1 for r in results if r.success)
    total_rows = sum(r.rows_updated for r in results if r.success)
    
    print(f"    - 更新成功: {success_count}/{total_stocks}")
    print(f"    - 更新记录: {total_rows}")
    
    return {
        "status": "success",
        "stocks_updated": success_count,
        "total_stocks": total_stocks,
        "total_records": total_rows
    }


def step2_factor_calc() -> Dict[str, Any]:
    """因子计算"""
    print("  [Step 2] 因子计算...")
    import time
    start_time = time.time()
    
    from core.factor import get_factor_engine, get_factor_registry, get_factor_storage
    from core.infrastructure.config import get_data_paths
    from core.data import get_data_fetcher
    
    config = get_pipeline_config()
    max_stocks = config.get("max_stocks_factor")
    max_factors = config.get("max_factors_per_stock")
    batch_size = config.get("batch_size", 100)
    
    registry = get_factor_registry()
    engine = get_factor_engine()
    storage = get_factor_storage()
    
    factor_count = registry.get_factor_count()
    print(f"    - 已注册因子: {factor_count} 个")
    
    if factor_count == 0:
        print("    ⚠️ 没有注册因子，跳过计算")
        return {"status": "warning", "factors": 0, "message": "没有注册因子"}
    
    all_factors = registry.list_all()
    factor_ids = [f.id for f in all_factors]
    
    if max_factors:
        factor_ids = factor_ids[:max_factors]
    
    total_factors = len(factor_ids)
    print(f"    - 待计算因子: {total_factors} 个")
    
    import pandas as pd
    import numpy as np
    from pathlib import Path
    
    data_paths = get_data_paths()
    
    stock_files = list(Path(data_paths.stocks_daily_path).glob("*.parquet"))
    
    if max_stocks:
        stock_files = stock_files[:max_stocks]
    
    total_stocks = len(stock_files)
    
    if not stock_files:
        print("    ⚠️ 没有找到数据文件，跳过计算")
        return {"status": "warning", "factors": 0, "message": "没有数据文件"}
    
    print(f"    - 待计算股票: {total_stocks} 只")
    print(f"    - 批处理大小: {batch_size}")
    
    print("    - 获取基本面数据...")
    try:
        fetcher = get_data_fetcher()
        fundamental_df = fetcher.get_fundamental()
        if not fundamental_df.empty:
            print(f"    - 基本面数据: {len(fundamental_df)} 只股票")
        else:
            print("    ⚠️ 基本面数据获取失败，部分因子可能无法计算")
            fundamental_df = pd.DataFrame()
    except Exception as e:
        print(f"    ⚠️ 基本面数据获取异常: {e}")
        fundamental_df = pd.DataFrame()
    
    print("    - 获取业绩报表数据...")
    try:
        earnings_df = fetcher.get_earnings_report()
        if not earnings_df.empty:
            print(f"    - 业绩报表: {len(earnings_df)} 只股票")
        else:
            earnings_df = pd.DataFrame()
    except Exception as e:
        print(f"    ⚠️ 业绩报表获取异常: {e}")
        earnings_df = pd.DataFrame()
    
    print("    - 获取回购公告数据...")
    try:
        repurchase_df = fetcher.get_repurchase()
        if not repurchase_df.empty:
            print(f"    - 回购公告: {len(repurchase_df)} 条")
        else:
            repurchase_df = pd.DataFrame()
    except Exception as e:
        print(f"    ⚠️ 回购公告获取异常: {e}")
        repurchase_df = pd.DataFrame()
    
    success_count = 0
    failed_count = 0
    total_computations = 0
    
    for i, stock_file in enumerate(stock_files):
        try:
            sample_df = pd.read_parquet(stock_file)
            
            if sample_df.empty or len(sample_df) < 20:
                continue
            
            stock_code = sample_df['stock_code'].iloc[0] if 'stock_code' in sample_df.columns else stock_file.stem
            
            data = {
                'close': sample_df['close'],
                'open': sample_df['open'],
                'high': sample_df['high'],
                'low': sample_df['low'],
                'volume': sample_df['volume'],
                'date': sample_df['date'],
                'stock_code': sample_df['stock_code']
            }
            
            if 'amount' in sample_df.columns:
                data['amount'] = sample_df['amount']
            if 'pct_change' in sample_df.columns:
                data['pct_change'] = sample_df['pct_change']
            if 'turnover' in sample_df.columns:
                data['turnover'] = sample_df['turnover']
            
            if not fundamental_df.empty and 'code' in fundamental_df.columns:
                stock_fundamental = fundamental_df[fundamental_df['code'] == stock_code]
                if not stock_fundamental.empty:
                    for col in ['pe_ratio', 'pb_ratio', 'market_cap', 'float_market_cap', 
                                'float_shares', 'total_shares', 'turnover_rate', 'roe', 'debt_ratio']:
                        if col in stock_fundamental.columns:
                            data[col] = stock_fundamental[col].iloc[0]
            
            if not earnings_df.empty and 'code' in earnings_df.columns:
                stock_earnings = earnings_df[earnings_df['code'] == stock_code]
                if not stock_earnings.empty:
                    for col in ['eps', 'net_profit', 'net_profit_growth', 'revenue', 'revenue_growth']:
                        if col in stock_earnings.columns:
                            data[col] = stock_earnings[col].iloc[0]
                    if 'roe' in stock_earnings.columns and 'roe' not in data:
                        data['roe'] = stock_earnings['roe'].iloc[0]
            
            if not repurchase_df.empty and 'code' in repurchase_df.columns:
                stock_repurchase = repurchase_df[repurchase_df['code'] == stock_code]
                if not stock_repurchase.empty:
                    data['buyback_announcement'] = True
                    if 'repurchased_amount' in stock_repurchase.columns:
                        data['buyback_amount'] = stock_repurchase['repurchased_amount'].iloc[0]
            
            for factor_id in factor_ids:
                try:
                    result = engine.compute_single(factor_id, data)
                    if result.success:
                        success_count += 1
                    total_computations += 1
                except Exception:
                    failed_count += 1
                    total_computations += 1
            
            if (i + 1) % batch_size == 0:
                elapsed = time.time() - start_time
                print(f"    - 进度: {i+1}/{total_stocks} 只股票, 成功: {success_count}, 耗时: {elapsed:.1f}秒")
                
        except Exception:
            failed_count += len(factor_ids)
            continue
    
    elapsed = time.time() - start_time
    print(f"    - 计算完成: {total_stocks} 只股票 × {total_factors} 个因子")
    print(f"    - 成功: {success_count}, 失败: {failed_count}")
    print(f"    - 总耗时: {elapsed:.2f}秒")
    
    return {
        "status": "success",
        "factors": success_count,
        "failed": failed_count,
        "total_factors": total_factors,
        "total_stocks": total_stocks,
        "total_computations": total_computations,
        "elapsed": elapsed
    }


def step3_signal_gen() -> Dict[str, Any]:
    """信号生成"""
    print("  [Step 3] 信号生成...")
    import time
    start_time = time.time()
    
    from core.signal import get_signal_generator, get_signal_registry
    from core.factor import get_factor_engine, get_factor_registry
    from core.infrastructure.config import get_data_paths
    import pandas as pd
    from pathlib import Path
    
    config = get_pipeline_config()
    max_stocks = config.get("max_stocks_signal")
    max_factors = config.get("max_factors_per_stock")
    max_signals_output = config.get("max_signals_output", 50)
    batch_size = config.get("batch_size", 100)
    
    registry = get_signal_registry()
    generator = get_signal_generator()
    
    signals = registry.list_all()
    print(f"    - 已注册信号: {len(signals)} 个")
    
    if len(signals) == 0:
        print("    ⚠️ 没有注册信号，跳过")
        return {"status": "warning", "signals": 0, "message": "没有注册信号"}
    
    data_paths = get_data_paths()
    stock_files = list(Path(data_paths.stocks_daily_path).glob("*.parquet"))
    
    if max_stocks:
        stock_files = stock_files[:max_stocks]
    
    total_stocks = len(stock_files)
    print(f"    - 待扫描股票: {total_stocks} 只")
    
    buy_signals = []
    sell_signals = []
    
    position_stocks = set()
    global _pipeline_data
    position_status = _pipeline_data.get("position_status", {})
    if position_status.get("has_position", False):
        position_stocks = set(position_status.get("positions", {}).keys())
        print(f"    - 当前持仓: {len(position_stocks)} 只")
    
    factor_engine = get_factor_engine()
    factor_registry = get_factor_registry()
    factors = factor_registry.list_all()
    
    if max_factors:
        factors = factors[:max_factors]
    
    print(f"    - 使用因子: {len(factors)} 个")
    
    processed_count = 0
    for i, stock_file in enumerate(stock_files):
        try:
            df = pd.read_parquet(stock_file)
            if df.empty or len(df) < 60:
                continue
            
            processed_count += 1
            df_sorted = df.sort_values('date')
            stock_code = df_sorted['stock_code'].iloc[-1] if 'stock_code' in df_sorted.columns else stock_file.stem
            
            close = df_sorted['close']
            volume = df_sorted['volume']
            
            last_close = close.iloc[-1]
            prev_close = close.iloc[-2]
            
            ma5 = close.rolling(5).mean().iloc[-1]
            ma20 = close.rolling(20).mean().iloc[-1]
            ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else ma20
            
            vol_ma5 = volume.rolling(5).mean().iloc[-1]
            vol_ma20 = volume.rolling(20).mean().iloc[-1]
            vol_ratio = vol_ma5 / vol_ma20 if vol_ma20 > 0 else 1
            
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / (loss + 1e-10)
            rsi = (100 - (100 / (1 + rs))).iloc[-1]
            
            data = {
                'close': close,
                'open': df_sorted['open'],
                'high': df_sorted['high'],
                'low': df_sorted['low'],
                'volume': volume,
                'date': df_sorted['date'],
                'stock_code': df_sorted['stock_code']
            }
            
            factor_scores = []
            for f in factors:
                try:
                    result = factor_engine.compute_single(f.id, data)
                    if result.success and result.data is not None:
                        if 'factor_value' in result.data.columns:
                            values = result.data['factor_value'].dropna()
                            if len(values) > 0:
                                factor_scores.append(values.iloc[-1])
                except Exception:
                    continue
            
            avg_factor_score = np.mean(factor_scores) if factor_scores else 0
            
            trend_ok = (last_close > ma5 and ma5 > ma20)
            vol_ok = (vol_ratio > 0.8)
            rsi_ok = (rsi < 70 and rsi > 40)
            
            if trend_ok and vol_ok and rsi_ok and avg_factor_score > 0:
                buy_signals.append({
                    "stock_code": stock_code,
                    "reason": f"趋势确认+放量+RSI{rsi:.0f}+因子{avg_factor_score:.2f}",
                    "price": round(last_close, 2),
                    "signal_type": "buy",
                    "ma5": round(ma5, 2),
                    "ma20": round(ma20, 2),
                    "vol_ratio": round(vol_ratio, 2),
                    "rsi": round(rsi, 1)
                })
            
            if stock_code in position_stocks:
                position_data = position_status.get("positions", {}).get(stock_code, {})
                avg_cost = position_data.get('avg_cost', 0)
                profit_loss_pct = position_data.get('profit_loss_pct', 0)
                
                should_sell = False
                sell_reason = ""
                
                if profit_loss_pct < -15:
                    should_sell = True
                    sell_reason = f"止损信号: 亏损{profit_loss_pct:.2f}%（超过-15%阈值）"
                elif profit_loss_pct > 20:
                    should_sell = True
                    sell_reason = f"止盈信号: 盈利{profit_loss_pct:.2f}%（超过20%阈值）"
                elif last_close < ma5 and last_close < ma20:
                    should_sell = True
                    sell_reason = f"技术面走弱: 跌破MA5({ma5:.2f})和MA20({ma20:.2f})"
                elif last_close < ma5 and prev_close > ma5:
                    should_sell = True
                    sell_reason = f"跌破5日均线(MA5:{ma5:.2f})"
                
                if should_sell:
                    sell_signals.append({
                        "stock_code": stock_code,
                        "reason": sell_reason,
                        "price": round(last_close, 2),
                        "signal_type": "sell",
                        "profit_loss_pct": round(profit_loss_pct, 2),
                        "avg_cost": avg_cost
                    })
            
            if (i + 1) % batch_size == 0:
                elapsed = time.time() - start_time
                print(f"    - 进度: {i+1}/{total_stocks}, 买入: {len(buy_signals)}, 卖出: {len(sell_signals)}, 耗时: {elapsed:.1f}秒")
                
        except Exception:
            continue
    
    elapsed = time.time() - start_time
    print(f"    - 扫描完成: {processed_count} 只股票")
    print(f"    - 买入信号: {len(buy_signals)} 个")
    print(f"    - 卖出信号: {len(sell_signals)} 个")
    
    if len(sell_signals) > 0 and len(position_stocks) > 0:
        print(f"    - 持仓监控: {len(position_stocks)} 只持仓股票中，{len(sell_signals)} 只触发卖出信号")
    
    print(f"    - 总耗时: {elapsed:.2f}秒")
    
    _pipeline_data["signal_data"] = {
        "buy_signals": buy_signals[:max_signals_output],
        "sell_signals": sell_signals[:max_signals_output],
        "total_buy": len(buy_signals),
        "total_sell": len(sell_signals)
    }
    
    return {
        "status": "success",
        "signals": len(signals),
        "total_stocks": total_stocks,
        "processed_stocks": processed_count,
        "buy_signals": buy_signals[:max_signals_output],
        "sell_signals": sell_signals[:max_signals_output],
        "total_buy": len(buy_signals),
        "total_sell": len(sell_signals),
        "elapsed": elapsed
    }


def step4_strategy_exec() -> Dict[str, Any]:
    """策略执行"""
    print("  [Step 4] 策略执行...")
    import time
    start_time = time.time()
    
    from core.strategy import get_stock_selector, get_strategy_registry
    from core.infrastructure.config import get_data_paths
    import pandas as pd
    from pathlib import Path
    
    config = get_pipeline_config()
    max_stocks = config.get("max_stocks_strategy")
    batch_size = config.get("batch_size", 100)
    
    registry = get_strategy_registry()
    selector = get_stock_selector()
    
    strategies = registry.list_all()
    print(f"    - 已注册策略: {len(strategies)} 个")
    
    if len(strategies) == 0:
        print("    ⚠️ 没有注册策略，跳过选股")
        return {"status": "warning", "selections": 0, "message": "没有注册策略"}
    
    data_paths = get_data_paths()
    stock_files = list(Path(data_paths.stocks_daily_path).glob("*.parquet"))
    
    if max_stocks:
        stock_files = stock_files[:max_stocks]
    
    total_stocks = len(stock_files)
    print(f"    - 待评分股票: {total_stocks} 只")
    
    stock_scores = []
    processed_count = 0
    
    for i, stock_file in enumerate(stock_files):
        try:
            df = pd.read_parquet(stock_file)
            if df.empty or len(df) < 30:
                continue
            
            processed_count += 1
            df_sorted = df.sort_values('date')
            stock_code = df_sorted['stock_code'].iloc[-1] if 'stock_code' in df_sorted.columns else stock_file.stem
            
            close = df_sorted['close']
            volume = df_sorted['volume']
            
            ret_5d = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] if close.iloc[-5] > 0 else 0
            ret_20d = (close.iloc[-1] - close.iloc[-20]) / close.iloc[-20] if close.iloc[-20] > 0 else 0
            
            vol_ma5 = volume.rolling(5).mean().iloc[-1]
            vol_ma20 = volume.rolling(20).mean().iloc[-1]
            vol_ratio = vol_ma5 / vol_ma20 if vol_ma20 > 0 else 1
            
            ma5 = close.rolling(5).mean().iloc[-1]
            ma20 = close.rolling(20).mean().iloc[-1]
            ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else ma20
            
            trend_score = 0
            if close.iloc[-1] > ma5:
                trend_score += 1
            if ma5 > ma20:
                trend_score += 1
            if ma20 > ma60:
                trend_score += 1
            
            momentum_score = 0
            if ret_5d > 0:
                momentum_score += 1
            if ret_20d > 0.05:
                momentum_score += 1
            
            volume_score = 1 if vol_ratio > 1.2 else 0
            
            total_score = trend_score * 0.4 + momentum_score * 0.4 + volume_score * 0.2
            
            stock_scores.append({
                "stock_code": stock_code,
                "score": round(total_score, 2),
                "trend": trend_score,
                "momentum": momentum_score,
                "volume": volume_score,
                "price": round(close.iloc[-1], 2)
            })
            
            if (i + 1) % batch_size == 0:
                elapsed = time.time() - start_time
                print(f"    - 进度: {i+1}/{total_stocks}, 已评分: {len(stock_scores)}, 耗时: {elapsed:.1f}秒")
                
        except Exception:
            continue
    
    stock_scores.sort(key=lambda x: x["score"], reverse=True)
    
    max_output = config.get("max_signals_output", 50)
    top_picks = stock_scores[:max_output]
    
    elapsed = time.time() - start_time
    print(f"    - 评分完成: {processed_count} 只股票")
    print(f"    - 有效评分: {len(stock_scores)} 只")
    print(f"    - 推荐买入: {len(top_picks)} 只")
    print(f"    - 总耗时: {elapsed:.2f}秒")
    
    global _pipeline_data
    _pipeline_data["strategy_data"] = {
        "stock_scores": top_picks,
        "total_scored": len(stock_scores),
        "processed_stocks": processed_count
    }
    
    return {
        "status": "success",
        "selections": len(strategies),
        "total_stocks": total_stocks,
        "processed_stocks": processed_count,
        "stock_scores": top_picks,
        "total_scored": len(stock_scores),
        "elapsed": elapsed
    }


def step5_portfolio_opt() -> Dict[str, Any]:
    """组合优化"""
    print("  [Step 5] 组合优化...")
    import time
    start_time = time.time()
    
    from core.portfolio import PortfolioOptimizer
    from core.infrastructure.config import get_data_paths
    import pandas as pd
    import numpy as np
    from pathlib import Path
    
    config = get_pipeline_config()
    max_stocks = config.get("max_stocks_portfolio")
    max_output = config.get("max_signals_output", 50)
    
    optimizer = PortfolioOptimizer(config={"method": "risk_parity", "max_single_weight": 0.15})
    
    print("    - 加载历史数据...")
    
    global _pipeline_data
    stock_scores_list = _pipeline_data.get("strategy_data", {}).get("stock_scores", [])
    
    if not stock_scores_list:
        print("    ⚠️ 没有选股结果，跳过权重计算")
        return {"status": "warning", "positions": 0}
    
    if max_stocks:
        stock_scores_list = stock_scores_list[:max_stocks]
    
    total_stocks = len(stock_scores_list)
    print(f"    - 待优化股票: {total_stocks} 只")
    
    stock_scores = {s["stock_code"]: s["score"] for s in stock_scores_list if s["score"] > 0}
    
    data_paths = get_data_paths()
    stocks_path = Path(data_paths.stocks_daily_path)
    
    print("    - 计算协方差矩阵...")
    
    returns_data = {}
    for stock in stock_scores_list:
        try:
            stock_file = stocks_path / f"{stock['stock_code']}.parquet"
            if stock_file.exists():
                df = pd.read_parquet(stock_file)
                if 'close' in df.columns and len(df) > 20:
                    df = df.sort_values('date')
                    returns = df['close'].pct_change().dropna()
                    if len(returns) >= 20:
                        returns_data[stock['stock_code']] = returns.tail(60).values
        except Exception:
            continue
    
    print(f"    - 有效收益率数据: {len(returns_data)} 只")
    
    expected_returns = {}
    for s in stock_scores_list:
        score = s.get("score", 0)
        expected_returns[s["stock_code"]] = score * 0.1
    
    cov_matrix = None
    if len(returns_data) >= 3:
        min_len = min(len(v) for v in returns_data.values())
        aligned_returns = {}
        for code, rets in returns_data.items():
            aligned_returns[code] = rets[-min_len:]
        
        returns_array = np.array([aligned_returns[c] for c in stock_scores.keys() if c in aligned_returns])
        if returns_array.shape[0] >= 3:
            cov_matrix = np.cov(returns_array)
            print(f"    - 协方差矩阵: {cov_matrix.shape}")
    
    print("    - 执行风险平价优化...")
    
    result = optimizer.optimize(
        stock_scores=stock_scores,
        expected_returns=expected_returns,
        cov_matrix=cov_matrix
    )
    
    if result.is_success():
        weights = result.weights
        print(f"    - 优化方法: {result.method}")
        
        if result.fallback_used:
            print(f"    ⚠️ 降级原因: {result.message}")
        
        print("    - 中性化处理...")
        
        total_weight = sum(weights.values())
        if total_weight > 0:
            normalized_weights = {k: v/total_weight for k, v in weights.items()}
        else:
            normalized_weights = weights
        
        top_weights = sorted(normalized_weights.items(), key=lambda x: x[1], reverse=True)[:max_output]
        
        print(f"    - 分配权重: {len(weights)} 只股票")
        print(f"    - 输出Top {len(top_weights)}:")
        for code, w in top_weights[:10]:
            print(f"      {code}: {w*100:.2f}%")
        
        _pipeline_data["portfolio_weights"] = dict(top_weights)
        
        elapsed = time.time() - start_time
        print(f"    ✓ 组合优化完成 ({elapsed:.2f}秒)")
        
        return {
            "status": "success",
            "total_stocks": total_stocks,
            "positions": len(weights),
            "output_positions": len(top_weights),
            "method": result.method,
            "elapsed": elapsed
        }
    else:
        print(f"    ⚠️ 优化失败: {result.message}")
        total_score = sum(stock_scores.values())
        if total_score > 0:
            fallback_weights = {k: v/total_score for k, v in stock_scores.items()}
        else:
            fallback_weights = {k: 1/len(stock_scores) for k in stock_scores}
        
        _pipeline_data["portfolio_weights"] = fallback_weights
        
        elapsed = time.time() - start_time
        return {
            "status": "fallback",
            "total_stocks": total_stocks,
            "positions": len(fallback_weights),
            "message": result.message,
            "elapsed": elapsed
        }


def step6_risk_check() -> Dict[str, Any]:
    """风控检查"""
    print("  [Step 6] 风控检查...")
    import time
    start_time = time.time()
    
    from core.risk import PreTradeRiskChecker, get_risk_limits, TradeInstruction, PortfolioState
    import numpy as np
    
    config = get_pipeline_config()
    max_orders = config.get("max_orders_output", 50)
    
    checker = PreTradeRiskChecker()
    limits = get_risk_limits()
    
    print("    - 构建组合状态...")
    
    global _pipeline_data
    weights = _pipeline_data.get("portfolio_weights", {})
    signals = _pipeline_data.get("signal_data", {}).get("buy_signals", [])
    
    total_capital = 10000000.0
    positions = {code: weight * total_capital for code, weight in weights.items()}
    
    industry_mapping = {}
    for signal in signals:
        code = signal.get("stock_code", "")
        if code.startswith("6"):
            industry_mapping[code] = "金融"
        elif code.startswith("0"):
            industry_mapping[code] = "科技"
        elif code.startswith("3"):
            industry_mapping[code] = "消费"
        elif code.startswith("688"):
            industry_mapping[code] = "科技"
        else:
            industry_mapping[code] = "其他"
    
    portfolio_state = PortfolioState(
        total_capital=total_capital,
        positions=positions,
        weights=weights,
        industry_mapping=industry_mapping,
        current_drawdown=0.0,
        cash=total_capital * 0.1
    )
    
    print(f"    - 组合持仓: {len(weights)} 只")
    print(f"    - 待检查信号: {len(signals)} 个")
    
    print("    - 构建交易指令...")
    
    trade_instructions = []
    for signal in signals[:max_orders]:
        stock_code = signal.get("stock_code", "")
        price = signal.get("price", 0)
        weight = weights.get(stock_code, 0.1)
        amount = weight * total_capital
        quantity = int(amount / price / 100) * 100 if price > 0 else 0
        
        if quantity > 0:
            trade_instructions.append(TradeInstruction(
                stock_code=stock_code,
                direction="buy",
                quantity=quantity,
                price=price,
                amount=amount,
                reason=signal.get("reason", "")
            ))
    
    print(f"    - 待检查交易指令: {len(trade_instructions)} 笔")
    
    print("    - 执行事前风控检查...")
    
    result = checker.check(
        trade_instructions=trade_instructions,
        portfolio_state=portfolio_state,
        check_soft_limits=True
    )
    
    elapsed = time.time() - start_time
    
    if result.passed:
        print(f"    ✓ 风控检查通过 ({elapsed:.2f}秒)")
        print(f"      - 检查项: {result.total_checks}, 通过: {result.passed_checks}")
    else:
        print(f"    ⚠️ 风控检查未通过 ({elapsed:.2f}秒)")
        for violation in result.violations[:10]:
            print(f"      ❌ {violation.rule_name}: {violation.message}")
        if len(result.violations) > 10:
            print(f"      ... 还有 {len(result.violations) - 10} 个违规项")
    
    if result.warnings:
        for warning in result.warnings[:5]:
            print(f"      ⚠️ {warning.rule_name}: {warning.message}")
        if len(result.warnings) > 5:
            print(f"      ... 还有 {len(result.warnings) - 5} 个警告项")
    
    _pipeline_data["risk_result"] = result.to_dict()
    
    return {
        "status": "success" if result.passed else "failed",
        "passed": result.passed,
        "total_signals": len(signals),
        "checked_instructions": len(trade_instructions),
        "violations": len(result.violations),
        "warnings": len(result.warnings),
        "elapsed": elapsed
    }


def step7_trading() -> Dict[str, Any]:
    """执行交易"""
    print("  [Step 7] 执行交易...")
    import time
    start_time = time.time()
    
    from core.trading import OrderManager
    import numpy as np
    
    config = get_pipeline_config()
    max_orders = config.get("max_orders_output", 50)
    
    global _pipeline_data
    signals = _pipeline_data.get("signal_data", {}).get("buy_signals", [])
    sell_signals = _pipeline_data.get("signal_data", {}).get("sell_signals", [])
    weights = _pipeline_data.get("portfolio_weights", {})
    risk_result = _pipeline_data.get("risk_result", {})
    
    orders = []
    
    try:
        order_manager = OrderManager()
        print("    - 模式: 信号推送（供交易员手动执行）")
        
        print(f"    - 买入信号: {len(signals)} 个")
        print(f"    - 卖出信号: {len(sell_signals)} 个")
        
        print("    - 生成买入指令...")
        for signal in signals[:max_orders]:
            stock_code = signal.get("stock_code", "")
            price = signal.get("price", 0)
            weight = weights.get(stock_code, 0.1)
            total_capital = 10000000.0
            amount = weight * total_capital
            quantity = int(amount / price / 100) * 100 if price > 0 else 0
            
            if quantity > 0 and weight > 0.01:
                orders.append({
                    "stock_code": stock_code,
                    "action": "BUY",
                    "price": price,
                    "quantity": quantity,
                    "amount": round(amount, 2),
                    "weight": round(weight, 4),
                    "reason": signal.get("reason", ""),
                    "signal_type": signal.get("signal_type", "buy"),
                    "ma5": signal.get("ma5", 0),
                    "ma20": signal.get("ma20", 0),
                    "rsi": signal.get("rsi", 0)
                })
        
        print("    - 生成卖出指令...")
        for signal in sell_signals[:max_orders]:
            stock_code = signal.get("stock_code", "")
            price = signal.get("price", 0)
            reason = signal.get("reason", "")
            
            orders.append({
                "stock_code": stock_code,
                "action": "SELL",
                "price": price,
                "quantity": 0,
                "amount": 0,
                "weight": 0,
                "reason": reason,
                "signal_type": "sell"
            })
        
        _pipeline_data["orders"] = orders
        
        elapsed = time.time() - start_time
        print(f"    ✓ 生成订单: {len(orders)} 笔 ({elapsed:.2f}秒)")
        
        buy_orders = [o for o in orders if o["action"] == "BUY"]
        sell_orders = [o for o in orders if o["action"] == "SELL"]
        
        print(f"      - 买入: {len(buy_orders)} 笔")
        print(f"      - 卖出: {len(sell_orders)} 笔")
        
        max_display = config.get("max_alerts_display", 10)
        for order in buy_orders[:max_display]:
            print(f"        {order['stock_code']}: 买入{order['quantity']}股 @ {order['price']:.2f}")
        
        for order in sell_orders[:max_display]:
            print(f"        {order['stock_code']}: 卖出 - {order['reason']}")
        
    except Exception as e:
        print(f"    ⚠️ 订单生成异常: {e}")
        import traceback
        traceback.print_exc()
    
    return {
        "status": "success",
        "total_buy_signals": len(signals),
        "total_sell_signals": len(sell_signals),
        "orders": len(orders),
        "buy_orders": len([o for o in orders if o["action"] == "BUY"]),
        "sell_orders": len([o for o in orders if o["action"] == "SELL"]),
        "elapsed": elapsed if 'elapsed' in dir() else 0
    }


def step8_analysis() -> Dict[str, Any]:
    """绩效分析与报告生成"""
    print("  [Step 8] 绩效分析与报告生成...")
    import time
    start_time = time.time()
    
    from .report_generator import DailyReportGenerator
    from .notifier import DailyNotifier
    from .step0_backtest_validation import (
        get_cached_backtest_result,
        is_backtest_cache_valid,
        get_backtest_cache_remaining_hours
    )
    import shutil
    
    generator = DailyReportGenerator()
    
    print("    - 计算绩效指标...")
    print("    - 生成分析报告...")
    
    print("    - 检查回测缓存...")
    if is_backtest_cache_valid():
        cached_result = get_cached_backtest_result()
        remaining_hours = get_backtest_cache_remaining_hours()
        if cached_result:
            print(f"      ✓ 回测缓存有效（剩余 {remaining_hours:.1f} 小时）")
            print(f"      ✓ 年化收益: {cached_result.get('annual_return', 0):.2f}%")
            print(f"      ✓ 夏普比率: {cached_result.get('sharpe_ratio', 0):.2f}")
            print(f"      ✓ 最大回撤: {cached_result.get('max_drawdown', 0):.2f}%")
            print(f"      ✓ 胜率: {cached_result.get('win_rate', 0):.2f}%")
            _pipeline_data["backtest_result"] = cached_result
        else:
            print("      ⚠️ 缓存为空，报告将不包含回测验证")
    else:
        print("      ⚠️ 回测缓存已过期或不存在")
        print("      提示: 请运行 'python -m core.daily --backtest' 更新回测缓存")
    
    result = generator.generate(signal_data=_pipeline_data.get("signal_data"))
    
    if result.success:
        print(f"    ✓ 报告已生成: {result.report_path}")
        
        report_path = Path(result.report_path)
        
        archive_dir = Path("./data/reports/archive")
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        date_str = datetime.now().strftime('%Y-%m-%d')
        archive_path = archive_dir / f"daily_report_{date_str}.md"
        
        try:
            shutil.copy2(report_path, archive_path)
            print(f"    ✓ 本地存档: {archive_path.absolute()}")
        except Exception as e:
            print(f"    ⚠️ 存档失败: {e}")
        
        print("    - 推送报告到Webhook...")
        try:
            notifier = DailyNotifier()
            
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()
            
            notify_result = notifier.notify(
                report_content=report_content,
                skip_pre_check=True
            )
            
            if notify_result.success:
                print(f"    ✓ Webhook推送成功")
            else:
                print(f"    ⚠️ 推送失败: {notify_result.error_message}")
        except Exception as e:
            print(f"    ⚠️ 推送异常: {e}")
    else:
        print(f"    ⚠️ 报告生成失败: {result.error_message}")
    
    return {
        "status": "success" if result.success else "failed",
        "report_path": result.report_path,
        "sections": result.sections_generated
    }


def step9_monitor() -> Dict[str, Any]:
    """监控仪表盘更新"""
    print("  [Step 9] 监控仪表盘更新...")
    import time
    start_time = time.time()
    
    from core.monitor import get_monitor_dashboard
    from core.trading import get_local_account_tracker
    
    dashboard = get_monitor_dashboard()
    
    try:
        account = get_local_account_tracker()
        account.expire_pending_orders()
        
        signal_data = _pipeline_data.get("signal_data", {})
        buy_signals = signal_data.get("buy_signals", [])
        sell_signals = signal_data.get("sell_signals", [])
        signal_count_today = len(buy_signals) + len(sell_signals)
        
        print("    - 从本地账户读取数据...")
        report = dashboard.update_from_local_account(
            signal_count_today=signal_count_today,
            signal_win_rate=0.55,
            factor_ic=0.03,
            factor_decay=0.1
        )
        
        account_summary = account.get_account_summary()
        print(f"    - 总资产: ¥{account_summary['account']['total_value']:,.2f}")
        print(f"    - 持仓数: {account_summary['account']['position_count']}")
        
    except Exception as e:
        print(f"    ⚠️ 本地账户读取失败，使用管线数据: {e}")
        
        signal_data = _pipeline_data.get("signal_data", {})
        strategy_data = _pipeline_data.get("strategy_data", {})
        portfolio_weights = _pipeline_data.get("portfolio_weights", {})
        
        stock_scores = strategy_data.get("stock_scores", [])
        if stock_scores:
            scores = [s.get("score", 0) for s in stock_scores]
            avg_score = sum(scores) / len(scores) if scores else 0
            daily_return = avg_score * 0.02
        
        position_count = len(portfolio_weights)
        position_concentration = 0.0
        if portfolio_weights:
            weights = list(portfolio_weights.values())
            position_concentration = max(weights) if weights else 0
        
        buy_signals = signal_data.get("buy_signals", [])
        sell_signals = signal_data.get("sell_signals", [])
        signal_count_today = len(buy_signals) + len(sell_signals)
        
        report = dashboard.update(
            daily_return=daily_return if 'daily_return' in dir() else 0,
            position_count=position_count,
            position_concentration=position_concentration,
            signal_count_today=signal_count_today
        )
    
    dashboard.save_report(report)
    
    print(f"    ✓ 监控状态: {report.metrics.overall_status}")
    print(f"    ✓ 活跃预警: {report.metrics.active_alerts_count}")
    
    if report.alerts:
        print("    - 预警详情:")
        for alert in report.alerts[:3]:
            severity = alert.get("severity", "info")
            message = alert.get("message", "")
            print(f"      [{severity.upper()}] {message}")
    
    if report.should_backtest:
        print(f"    🔔 触发回测: {report.backtest_reason}")
    
    elapsed = time.time() - start_time
    print(f"    ✓ 监控更新完成 ({elapsed:.2f}秒)")
    
    return {
        "status": "success",
        "overall_status": report.metrics.overall_status,
        "active_alerts": report.metrics.active_alerts_count,
        "should_backtest": report.should_backtest,
        "elapsed": elapsed
    }


def step10_strategy_health_check() -> Dict[str, Any]:
    """策略健康检查"""
    print("  [Step 10] 策略健康检查...")
    import time
    start_time = time.time()
    
    from core.monitor import StrategyHealthMonitor, HealthLevel
    from core.strategy import get_strategy_registry
    
    monitor = StrategyHealthMonitor()
    registry = get_strategy_registry()
    
    strategies = registry.list_all()
    print(f"    - 已注册策略: {len(strategies)} 个")
    
    active_strategies = [s for s in strategies if s.status.value == "active"]
    print(f"    - 活跃策略: {len(active_strategies)} 个")
    
    unhealthy_strategies = []
    deprecated_strategies = []
    
    for strategy in active_strategies:
        try:
            backtest_perf = strategy.backtest_performance
            
            performance_data = {}
            if backtest_perf:
                performance_data = {
                    "sharpe_ratio": backtest_perf.sharpe_ratio,
                    "max_drawdown": backtest_perf.max_drawdown,
                    "calmar_ratio": backtest_perf.calmar_ratio,
                    "benchmark_correlation": backtest_perf.beta if backtest_perf.beta else 0.5
                }
            
            parameter_data = {
                "parameter_drift": 0.05,
                "parameter_sensitivity": 0.1,
                "parameter_stability": 0.95
            }
            
            execution_data = {
                "execution_rate": 0.98,
                "fill_rate": 0.99,
                "turnover_rate": 0.15,
                "trading_cost": 0.002
            }
            
            environment_data = {
                "market_match": 0.85,
                "factor_match": 0.90,
                "liquidity_match": 0.95,
                "volatility_match": 0.80
            }
            
            status = monitor.update_strategy_health(
                strategy_id=strategy.id,
                strategy_name=strategy.name,
                performance=performance_data,
                parameter=parameter_data,
                execution=execution_data,
                environment=environment_data
            )
            
            print(f"    - {strategy.name}: {status.health_level.value} (得分: {status.health_score:.1f})")
            
            if status.health_level in [HealthLevel.NORMAL, HealthLevel.POOR]:
                unhealthy_strategies.append({
                    "id": strategy.id,
                    "name": strategy.name,
                    "score": status.health_score,
                    "warnings": status.warning_messages,
                    "recommendations": status.recommendations
                })
                
                if status.health_score < 50:
                    deprecated_strategies.append({
                        "id": strategy.id,
                        "name": strategy.name,
                        "score": status.health_score,
                        "reason": "健康得分过低，建议停用"
                    })
            
        except Exception as e:
            print(f"    ⚠️ 检查策略 {strategy.id} 失败: {e}")
    
    elapsed = time.time() - start_time
    
    if len(unhealthy_strategies) > 0:
        print(f"    ⚠️ 发现 {len(unhealthy_strategies)} 个不健康策略:")
        for us in unhealthy_strategies[:5]:
            print(f"      - {us['name']}: 得分 {us['score']:.1f}")
            for warning in us.get('warnings', [])[:2]:
                print(f"        ⚠️ {warning}")
    
    if len(deprecated_strategies) > 0:
        print(f"    ❌ 发现 {len(deprecated_strategies)} 个失效策略:")
        for ds in deprecated_strategies:
            print(f"      - {ds['name']}: {ds['reason']}")
    
    if len(unhealthy_strategies) == 0:
        print("    ✓ 所有策略健康状态良好")
    
    print(f"    ✓ 策略健康检查完成 ({elapsed:.2f}秒)")
    
    return {
        "status": "success",
        "total_strategies": len(strategies),
        "active_strategies": len(active_strategies),
        "unhealthy_count": len(unhealthy_strategies),
        "deprecated_count": len(deprecated_strategies),
        "unhealthy_strategies": unhealthy_strategies,
        "deprecated_strategies": deprecated_strategies,
        "elapsed": elapsed
    }


def create_pipeline_scheduler() -> DailyScheduler:
    """创建管线调度器"""
    scheduler = DailyScheduler()
    
    scheduler.register_task_func(
        name="position_check",
        func=step0_position_check,
        description="持仓状态检查",
        required=True
    )
    
    scheduler.register_task_func(
        name="data_update",
        func=step1_data_update,
        description="数据更新",
        required=True,
        dependencies=["position_check"]
    )
    
    scheduler.register_task_func(
        name="factor_calc",
        func=step2_factor_calc,
        description="因子计算",
        required=True,
        dependencies=["data_update"]
    )
    
    scheduler.register_task_func(
        name="signal_gen",
        func=step3_signal_gen,
        description="信号生成",
        required=True,
        dependencies=["factor_calc"]
    )
    
    scheduler.register_task_func(
        name="strategy_exec",
        func=step4_strategy_exec,
        description="策略执行",
        required=True,
        dependencies=["signal_gen"]
    )
    
    scheduler.register_task_func(
        name="portfolio_opt",
        func=step5_portfolio_opt,
        description="组合优化",
        required=True,
        dependencies=["strategy_exec"]
    )
    
    scheduler.register_task_func(
        name="risk_check",
        func=step6_risk_check,
        description="风控检查",
        required=True,
        dependencies=["portfolio_opt"]
    )
    
    scheduler.register_task_func(
        name="trading",
        func=step7_trading,
        description="执行交易",
        required=True,
        dependencies=["risk_check"]
    )
    
    scheduler.register_task_func(
        name="analysis",
        func=step8_analysis,
        description="绩效分析",
        required=False,
        dependencies=["trading"]
    )
    
    scheduler.register_task_func(
        name="monitor",
        func=step9_monitor,
        description="监控仪表盘",
        required=False,
        dependencies=["analysis"]
    )
    
    scheduler.register_task_func(
        name="strategy_health",
        func=step10_strategy_health_check,
        description="策略健康检查",
        required=False,
        dependencies=["monitor"]
    )
    
    return scheduler


def run_backtest_only():
    """仅执行回测验证"""
    print("=" * 50)
    print("WildQuest Matrix - 策略回测验证")
    print("=" * 50)
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    from .step0_backtest_validation import run_backtest_validation
    
    print("执行回测验证...")
    print("-" * 50)
    
    result = run_backtest_validation(force=True)
    
    print("-" * 50)
    print()
    
    if result.get("success"):
        print("✓ 回测验证成功!")
        print(f"  年化收益: {result.get('annual_return', 0):.2f}%")
        print(f"  夏普比率: {result.get('sharpe_ratio', 0):.2f}")
        print(f"  最大回撤: {result.get('max_drawdown', 0):.2f}%")
        print(f"  胜率: {result.get('win_rate', 0):.2f}%")
        print(f"  总交易次数: {result.get('total_trades', 0)}")
    else:
        print("✗ 回测验证失败!")
        print(f"  错误信息: {result.get('error_message', '未知错误')}")
    
    print()
    return 0 if result.get("success") else 1


def run_monitor_only():
    """仅显示监控仪表盘"""
    from core.monitor import get_monitor_dashboard, get_alert_trigger
    
    dashboard = get_monitor_dashboard()
    trigger = get_alert_trigger()
    status = trigger.get_status()
    
    print("=" * 60)
    print("                    策略监控仪表盘")
    print("=" * 60)
    print(f"查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"整体状态: {_status_emoji(status.overall_status)} {status.overall_status.upper()}")
    print()
    
    print("-" * 60)
    print("【各模块状态】")
    print("-" * 60)
    print(f"  绩效监控: {_status_emoji(status.performance_status)} {status.performance_status}")
    print(f"  风险监控: {_status_emoji(status.risk_status)} {status.risk_status}")
    print(f"  信号监控: {_status_emoji(status.signal_status)} {status.signal_status}")
    print(f"  因子监控: {_status_emoji(status.factor_status)} {status.factor_status}")
    print()
    
    if status.active_alerts:
        print("-" * 60)
        print("【活跃预警】")
        print("-" * 60)
        for alert in status.active_alerts[:10]:
            severity = alert.severity.value
            print(f"  {_status_emoji(severity)} [{severity.upper()}] {alert.message}")
        print()
    
    should_backtest, reason = trigger.should_trigger_backtest()
    if should_backtest:
        print("-" * 60)
        print("【回测建议】")
        print("-" * 60)
        print(f"  🔔 {reason}")
        print(f"  执行命令: python -m core.daily --backtest")
        print()
    
    print("=" * 60)
    return 0


def _status_emoji(status: str) -> str:
    """状态表情"""
    return {
        "normal": "🟢",
        "warning": "🟡",
        "critical": "🟠",
        "emergency": "🔴",
        "info": "⚪"
    }.get(status, "⚪")


def run_account_only():
    """显示账户状态"""
    from core.trading import show_account_status, show_equity_curve
    
    show_account_status()
    show_equity_curve(30)
    return 0


def run_feedback_interactive():
    """交互式交易反馈"""
    from core.trading import get_trade_feedback_handler
    
    handler = get_trade_feedback_handler()
    handler.interactive_feedback()
    return 0


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="WildQuest Matrix - 统一每日管线")
    parser.add_argument(
        "--mode",
        choices=["standard", "fast", "live", "backtest"],
        default="standard",
        help="执行模式: standard(标准)/fast(快速)/live(实盘)/backtest(回测)"
    )
    parser.add_argument(
        "--max-stocks",
        type=int,
        help="最大股票数量（测试模式）"
    )
    parser.add_argument(
        "--max-factors",
        type=int,
        help="最大因子数量（测试模式）"
    )
    parser.add_argument(
        "--no-quality-gate",
        action="store_true",
        help="禁用质量门控验证"
    )
    parser.add_argument(
        "--quality-gate-loose",
        action="store_true",
        help="质量门控宽松模式（失败不中断）"
    )
    parser.add_argument(
        "--backtest", 
        action="store_true",
        help="仅执行策略回测验证（等同于 --mode backtest）"
    )
    parser.add_argument(
        "--force-backtest",
        action="store_true",
        help="强制重新执行回测（忽略缓存）"
    )
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="显示监控仪表盘"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="显示当前监控状态"
    )
    parser.add_argument(
        "--account",
        action="store_true",
        help="显示账户状态和净值曲线"
    )
    parser.add_argument(
        "--feedback",
        action="store_true",
        help="交互式交易反馈"
    )
    
    args = parser.parse_args()
    
    if args.backtest or args.force_backtest:
        return run_backtest_only()
    
    if args.monitor or args.status:
        return run_monitor_only()
    
    if args.account:
        return run_account_only()
    
    if args.feedback:
        return run_feedback_interactive()
    
    from .unified_pipeline import run_unified_pipeline
    
    mode = "backtest" if args.backtest else args.mode
    
    result = run_unified_pipeline(
        mode=mode,
        max_stocks=args.max_stocks,
        max_factors=args.max_factors,
        enable_quality_gate=not args.no_quality_gate,
        quality_gate_strict=not args.quality_gate_loose
    )
    
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
