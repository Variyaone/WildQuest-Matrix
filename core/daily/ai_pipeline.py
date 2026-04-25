"""
AI增强每日任务管线

整合AI信号生成和RL策略执行到每日任务流程
"""

import os
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path

from .scheduler import DailyScheduler, Task


def step2_factor_calc_ai() -> Dict[str, Any]:
    """因子计算（含AI因子挖掘）"""
    print("  [Step 2] 因子计算...")
    
    from core.factor import get_factor_engine, get_factor_registry, get_factor_storage
    from core.infrastructure.config import get_data_paths
    import pandas as pd
    
    registry = get_factor_registry()
    engine = get_factor_engine()
    storage = get_factor_storage()
    
    factor_count = registry.get_factor_count()
    print(f"    - 已注册因子: {factor_count} 个")
    
    if factor_count == 0:
        print("    ⚠️ 没有注册因子，跳过计算")
        return {"status": "warning", "factors": 0, "message": "没有注册因子"}
    
    all_factors = registry.list_all()
    factor_ids = [f.id for f in all_factors[:10]]
    
    print(f"    - 计算因子: {len(factor_ids)} 个")
    
    data_paths = get_data_paths()
    stock_files = list(Path(data_paths.stocks_daily_path).glob("*.parquet"))[:5]
    
    if not stock_files:
        print("    ⚠️ 没有找到数据文件，跳过计算")
        return {"status": "warning", "factors": 0, "message": "没有数据文件"}
    
    sample_df = pd.read_parquet(stock_files[0])
    
    data = {
        'close': sample_df['close'],
        'open': sample_df['open'],
        'high': sample_df['high'],
        'low': sample_df['low'],
        'volume': sample_df['volume'],
        'date': sample_df['date'],
        'stock_code': sample_df['stock_code']
    }
    
    success_count = 0
    for factor_id in factor_ids:
        try:
            result = engine.compute_single(factor_id, data)
            if result.success:
                success_count += 1
        except Exception:
            pass
    
    print(f"    - 计算成功: {success_count}/{len(factor_ids)}")
    
    ai_factor_result = None
    try:
        from core.factor import get_ai_factor_miner
        ai_miner = get_ai_factor_miner()
        
        print("    - AI因子挖掘中...")
        
        factor_values = {}
        for factor_id in factor_ids:
            df = storage.load_factor(factor_id)
            if df is not None and not df.empty:
                factor_values[factor_id] = df
        
        if factor_values:
            ai_result = ai_miner.discover_factors(
                factor_values=factor_values,
                target_data=sample_df,
                n_factors=3
            )
            
            if ai_result.success:
                print(f"    - AI挖掘因子: {ai_result.n_factors} 个")
                ai_factor_result = {
                    "success": True,
                    "n_factors": ai_result.n_factors,
                    "factor_ids": ai_result.factor_ids
                }
    except Exception as e:
        print(f"    ⚠️ AI因子挖掘: {e}")
    
    return {
        "status": "success",
        "factors": success_count,
        "total": len(factor_ids),
        "ai_factor_result": ai_factor_result
    }


def step3_signal_gen_ai() -> Dict[str, Any]:
    """信号生成（含AI增强信号）"""
    print("  [Step 3] 信号生成...")
    
    from core.signal import get_signal_registry
    from core.infrastructure.config import get_data_paths
    import pandas as pd
    
    registry = get_signal_registry()
    signals = registry.list_all()
    print(f"    - 已注册信号: {len(signals)} 个")
    
    data_paths = get_data_paths()
    stock_files = list(Path(data_paths.stocks_daily_path).glob("*.parquet"))[:50]
    
    buy_signals = []
    sell_signals = []
    
    use_ai_signal = True
    ai_signals = []
    ai_confidence = 0.0
    
    if use_ai_signal:
        try:
            from core.signal import get_enhanced_signal_generator
            from core.factor import get_factor_engine, get_factor_registry
            
            ai_generator = get_enhanced_signal_generator()
            factor_engine = get_factor_engine()
            factor_registry = get_factor_registry()
            factors = factor_registry.list_all()[:5]
            
            print("    - AI增强信号生成中...")
            
            factor_values_list = []
            stock_codes_list = []
            
            for stock_file in stock_files[:20]:
                try:
                    df = pd.read_parquet(stock_file)
                    if df.empty or len(df) < 60:
                        continue
                    
                    df_sorted = df.sort_values('date')
                    stock_code = df_sorted['stock_code'].iloc[-1] if 'stock_code' in df_sorted.columns else stock_file.stem
                    stock_codes_list.append(stock_code)
                    
                    stock_factor_values = {}
                    for f in factors:
                        try:
                            data = {
                                'close': df_sorted['close'],
                                'open': df_sorted['open'],
                                'high': df_sorted['high'],
                                'low': df_sorted['low'],
                                'volume': df_sorted['volume'],
                                'date': df_sorted['date'],
                                'stock_code': df_sorted['stock_code']
                            }
                            result = factor_engine.compute_single(f.id, data)
                            if result.success and result.data is not None:
                                if 'factor_value' in result.data.columns:
                                    values = result.data['factor_value'].dropna()
                                    if len(values) > 0:
                                        stock_factor_values[f.id] = values.iloc[-1]
                        except Exception:
                            continue
                    
                    factor_values_list.append(stock_factor_values)
                except Exception:
                    continue
            
            if factor_values_list:
                factor_df = pd.DataFrame(factor_values_list, index=stock_codes_list)
                
                ai_result = ai_generator.generate(
                    factor_values=factor_df,
                    date=datetime.now().strftime("%Y-%m-%d"),
                    use_ensemble=True
                )
                
                if ai_result.success:
                    ai_confidence = ai_result.details.get("confidence", 0.5)
                    print(f"    - AI信号置信度: {ai_confidence:.2f}")
                    
                    for s in ai_result.signals[:15]:
                        ai_signals.append({
                            "stock_code": s.stock_code,
                            "strength": round(s.strength, 4),
                            "direction": s.direction,
                            "confidence": round(s.confidence if hasattr(s, 'confidence') else ai_confidence, 2),
                            "source": s.source if hasattr(s, 'source') else "ai",
                            "reason": f"AI信号(置信度:{ai_confidence:.2f})"
                        })
                    
                    print(f"    - AI信号: {len(ai_signals)} 个")
        except Exception as e:
            print(f"    ⚠️ AI信号生成: {e}")
    
    print("    - 传统信号生成中...")
    
    from core.signal import get_signal_generator
    from core.factor import get_factor_engine, get_factor_registry
    
    generator = get_signal_generator()
    factor_engine = get_factor_engine()
    factor_registry = get_factor_registry()
    factors = factor_registry.list_all()[:5]
    
    for stock_file in stock_files:
        try:
            df = pd.read_parquet(stock_file)
            if df.empty or len(df) < 60:
                continue
            
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
                    "rsi": round(rsi, 1),
                    "source": "traditional"
                })
            elif last_close < ma5 and prev_close > ma5:
                sell_signals.append({
                    "stock_code": stock_code,
                    "reason": f"跌破5日均线(MA5:{ma5:.2f})",
                    "price": round(last_close, 2),
                    "signal_type": "sell",
                    "source": "traditional"
                })
        except Exception:
            continue
    
    print(f"    - 传统买入信号: {len(buy_signals)} 个")
    print(f"    - 传统卖出信号: {len(sell_signals)} 个")
    
    combined_buy_signals = ai_signals + buy_signals
    seen = set()
    unique_signals = []
    for s in combined_buy_signals:
        if s["stock_code"] not in seen:
            seen.add(s["stock_code"])
            unique_signals.append(s)
    
    print(f"    - 合并后买入信号: {len(unique_signals)} 个")
    
    from . import _pipeline_data
    _pipeline_data["signal_data"] = {
        "buy_signals": unique_signals[:15],
        "sell_signals": sell_signals[:10],
        "ai_confidence": ai_confidence
    }
    
    return {
        "status": "success",
        "signals": len(signals),
        "buy_signals": len(unique_signals),
        "sell_signals": len(sell_signals),
        "ai_signals": len(ai_signals),
        "ai_confidence": ai_confidence
    }


def step4_strategy_exec_ai() -> Dict[str, Any]:
    """策略执行（含RL策略）"""
    print("  [Step 4] 策略执行...")
    
    from core.strategy import get_stock_selector, get_strategy_registry
    from core.infrastructure.config import get_data_paths
    import pandas as pd
    
    registry = get_strategy_registry()
    selector = get_stock_selector()
    
    strategies = registry.list_all()
    print(f"    - 已注册策略: {len(strategies)} 个")
    
    if len(strategies) == 0:
        print("    ⚠️ 没有注册策略，跳过选股")
        return {"status": "warning", "selections": 0, "message": "没有注册策略"}
    
    data_paths = get_data_paths()
    stock_files = list(Path(data_paths.stocks_daily_path).glob("*.parquet"))[:100]
    
    stock_scores = []
    
    for stock_file in stock_files:
        try:
            df = pd.read_parquet(stock_file)
            if df.empty or len(df) < 30:
                continue
            
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
        except Exception:
            continue
    
    stock_scores.sort(key=lambda x: x["score"], reverse=True)
    top_picks = stock_scores[:10]
    
    print(f"    - 选股完成: {len(stock_scores)} 只股票评分")
    print(f"    - 推荐买入: {len(top_picks)} 只")
    
    rl_portfolio = None
    try:
        from core.strategy import get_rl_strategy
        from . import _pipeline_data
        
        signal_data = _pipeline_data.get("signal_data", {})
        buy_signals = signal_data.get("buy_signals", [])
        
        if buy_signals:
            rl_strategy = get_rl_strategy()
            
            signal_dict = {s["stock_code"]: s.get("strength", s.get("score", 0.5)) for s in buy_signals}
            
            print("    - RL策略优化持仓中...")
            
            rl_result = rl_strategy.execute(
                signals=signal_dict,
                current_portfolio={},
                market_data=None
            )
            
            if rl_result.success:
                rl_portfolio = rl_result.target_portfolio
                print(f"    - RL策略持仓: {len(rl_portfolio)} 只")
                
                for stock, weight in sorted(rl_portfolio.items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"      {stock}: {weight:.2%}")
    except Exception as e:
        print(f"    ⚠️ RL策略执行: {e}")
    
    from . import _pipeline_data
    _pipeline_data["strategy_data"] = {
        "stock_scores": top_picks,
        "rl_portfolio": rl_portfolio
    }
    
    return {
        "status": "success",
        "selections": len(strategies),
        "stock_scores": top_picks,
        "rl_portfolio": rl_portfolio
    }


def step7_trading_ai() -> Dict[str, Any]:
    """执行交易（含RL执行器）"""
    print("  [Step 7] 执行交易...")
    
    from core.trading import OrderManager
    import numpy as np
    
    from . import _pipeline_data
    signals = _pipeline_data.get("signal_data", {}).get("buy_signals", [])
    weights = _pipeline_data.get("portfolio_weights", {})
    rl_portfolio = _pipeline_data.get("strategy_data", {}).get("rl_portfolio", {})
    
    orders = []
    
    try:
        order_manager = OrderManager()
        print("    - 生成交易指令...")
        
        if rl_portfolio:
            print("    - 使用RL策略持仓")
            for stock_code, weight in rl_portfolio.items():
                signal = next((s for s in signals if s["stock_code"] == stock_code), {})
                price = signal.get("price", 0)
                
                if weight > 0.01:
                    orders.append({
                        "stock_code": stock_code,
                        "action": "BUY",
                        "price": price,
                        "weight": round(weight, 4),
                        "reason": signal.get("reason", "RL策略推荐"),
                        "signal_type": "rl_buy",
                        "source": "rl_strategy"
                    })
        else:
            print("    - 使用信号推送")
            for signal in signals[:10]:
                stock_code = signal.get("stock_code", "")
                price = signal.get("price", 0)
                weight = weights.get(stock_code, 0.1)
                
                if weight > 0.01:
                    orders.append({
                        "stock_code": stock_code,
                        "action": "BUY",
                        "price": price,
                        "weight": round(weight, 4),
                        "reason": signal.get("reason", ""),
                        "signal_type": signal.get("signal_type", "buy"),
                        "source": signal.get("source", "traditional")
                    })
        
        use_rl_execution = True
        if use_rl_execution and orders:
            try:
                from core.trading import get_rl_executor
                
                rl_executor = get_rl_executor()
                print("    - RL执行器优化订单...")
                
                optimized_orders = []
                for order in orders[:5]:
                    try:
                        from core.trading import TradeOrder, OrderSide, OrderType
                        
                        trade_order = TradeOrder(
                            order_id=f"ORD_{order['stock_code']}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                            stock_code=order["stock_code"],
                            side=OrderSide.BUY,
                            order_type=OrderType.LIMIT,
                            quantity=int(1000 * order["weight"]),
                            price=order["price"],
                            strategy_id="ai_pipeline"
                        )
                        
                        split_result = rl_executor.split_order(
                            order=trade_order,
                            market_data=None,
                            method="rl"
                        )
                        
                        if split_result.success:
                            optimized_orders.append({
                                **order,
                                "execution_method": "rl",
                                "sub_orders": len(split_result.sub_orders)
                            })
                        else:
                            optimized_orders.append({
                                **order,
                                "execution_method": "standard"
                            })
                    except Exception:
                        optimized_orders.append({
                            **order,
                            "execution_method": "standard"
                        })
                
                orders = optimized_orders
                print(f"    - RL执行优化: {len([o for o in orders if o.get('execution_method') == 'rl'])} 笔")
            except Exception as e:
                print(f"    ⚠️ RL执行器: {e}")
        
        _pipeline_data["orders"] = orders
        print(f"    - 生成订单: {len(orders)} 笔")
        
    except Exception as e:
        print(f"    ⚠️ 订单管理器初始化: {e}")
    
    return {
        "status": "success",
        "orders": len(orders)
    }


def create_ai_pipeline_scheduler() -> DailyScheduler:
    """创建AI增强管线调度器"""
    from . import step1_data_update, step5_portfolio_opt, step6_risk_check, step8_analysis
    
    scheduler = DailyScheduler()
    
    scheduler.register_task_func(
        name="data_update",
        func=step1_data_update,
        description="数据更新",
        required=True
    )
    
    scheduler.register_task_func(
        name="factor_calc",
        func=step2_factor_calc_ai,
        description="因子计算(含AI挖掘)",
        required=True,
        dependencies=["data_update"]
    )
    
    scheduler.register_task_func(
        name="signal_gen",
        func=step3_signal_gen_ai,
        description="信号生成(含AI增强)",
        required=True,
        dependencies=["factor_calc"]
    )
    
    scheduler.register_task_func(
        name="strategy_exec",
        func=step4_strategy_exec_ai,
        description="策略执行(含RL策略)",
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
        func=step7_trading_ai,
        description="执行交易(含RL执行)",
        required=True,
        dependencies=["risk_check"]
    )
    
    scheduler.register_task_func(
        name="analysis",
        func=step8_analysis,
        description="绩效分析与报告",
        required=False,
        dependencies=["trading"]
    )
    
    return scheduler


def run_ai_pipeline():
    """运行AI增强管线"""
    print("=" * 60)
    print("AI增强每日任务管线")
    print("=" * 60)
    print()
    
    scheduler = create_ai_pipeline_scheduler()
    result = scheduler.run()
    
    print()
    print("=" * 60)
    print("管线执行完成")
    print("=" * 60)
    
    return result


if __name__ == "__main__":
    run_ai_pipeline()
