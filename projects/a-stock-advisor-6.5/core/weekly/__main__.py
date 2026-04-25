"""
周常任务调度器入口

执行完整管线:
    python -m core.weekly
"""

import sys
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any
from pathlib import Path

from ..daily.scheduler import DailyScheduler, Task

PIPELINE_CONFIG = {
    "max_stocks_factor": None,
    "max_stocks_signal": None,
    "max_stocks_backtest": None,
    "parallel_workers": 8,
    "batch_size": 100,
}

_pipeline_data = {
    "factor_data": None,
    "signal_data": None,
    "backtest_result": None,
    "decay_result": None
}


def step1_weekly_factor_calculation() -> Dict[str, Any]:
    """周线因子计算"""
    print("  [Step 1] 周线因子计算...")
    import time
    start_time = time.time()
    
    global _pipeline_data
    
    try:
        from core.daily.factor_calculator import create_default_factor_calculator, FactorFrequency
        from core.infrastructure.config import get_data_paths
        from pathlib import Path
        import pandas as pd
        
        # 创建因子计算器
        calculator = create_default_factor_calculator()
        
        # 获取周线因子
        weekly_factors = [
            fid for fid, freq in calculator.FACTOR_FREQUENCY_MAP.items()
            if freq == FactorFrequency.WEEKLY
        ]
        
        print(f"    - 找到 {len(weekly_factors)} 个周线因子: {weekly_factors}")
        
        # 计算周线因子
        result = calculator.calculate(
            factor_ids=weekly_factors,
            force=True  # 强制计算
        )
        
        _pipeline_data["factor_data"] = result
        
        elapsed = time.time() - start_time
        print(f"    ✓ 周线因子计算完成 ({elapsed:.2f}秒)")
        
        return {
            "status": "success",
            "factors_calculated": result.factors_calculated,
            "factors_skipped": result.factors_skipped,
            "factors_failed": result.factors_failed,
            "total_rows": result.total_rows,
            "elapsed": elapsed
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"    ✗ 周线因子计算失败: {e} ({elapsed:.2f}秒)")
        return {
            "status": "failed",
            "error": str(e),
            "elapsed": elapsed
        }


def step2_weekly_signal_generation() -> Dict[str, Any]:
    """周线信号生成"""
    print("  [Step 2] 周线信号生成...")
    import time
    start_time = time.time()
    
    global _pipeline_data
    
    try:
        from core.daily.signal_generator import create_default_signal_generator, SignalFrequency
        from core.infrastructure.config import get_data_paths
        
        # 创建信号生成器
        generator = create_default_signal_generator()
        
        # 获取周线信号
        weekly_signals = [
            sid for sid, freq in generator.SIGNAL_FREQUENCY_MAP.items()
            if freq == SignalFrequency.WEEKLY
        ]
        
        print(f"    - 找到 {len(weekly_signals)} 个周线信号: {weekly_signals}")
        
        # 生成周线信号
        result = generator.generate(
            signal_ids=weekly_signals,
            force=True,  # 强制生成
            factor_data=_pipeline_data.get("factor_data")
        )
        
        _pipeline_data["signal_data"] = result
        
        elapsed = time.time() - start_time
        print(f"    ✓ 周线信号生成完成 ({elapsed:.2f}秒)")
        
        return {
            "status": "success",
            "signals_generated": result.signals_generated,
            "signals_skipped": result.signals_skipped,
            "signals_failed": result.signals_failed,
            "total_stocks": result.total_stocks,
            "elapsed": elapsed
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"    ✗ 周线信号生成失败: {e} ({elapsed:.2f}秒)")
        return {
            "status": "failed",
            "error": str(e),
            "elapsed": elapsed
        }


def step3_weekly_backtest() -> Dict[str, Any]:
    """策略周回测"""
    print("  [Step 3] 策略周回测...")
    import time
    start_time = time.time()
    
    global _pipeline_data
    
    try:
        from core.backtest.engine import BacktestEngine, BacktestConfig
        from core.infrastructure.config import get_data_paths
        from pathlib import Path
        import pandas as pd
        from datetime import datetime, timedelta
        
        # 创建回测配置
        config = BacktestConfig(
            frequency='w',  # 周线
            start_date=datetime.now() - timedelta(days=365),  # 回测1年
            end_date=datetime.now(),
            initial_capital=1000000,
            slippage_rate=0.002,
            commission_rate=0.0003
        )
        
        # 创建回测引擎
        backtest_engine = BacktestEngine(config=config)
        
        # 加载数据
        data_paths = get_data_paths()
        stock_files = list(Path(data_paths.stocks_daily_path).glob('*.parquet'))
        
        if not stock_files:
            print("    - 警告: 没有找到股票数据")
            return {
                "status": "failed",
                "error": "没有找到股票数据",
                "elapsed": time.time() - start_time
            }
        
        # 读取第一只股票的数据作为示例
        df = pd.read_parquet(stock_files[0])
        
        # 设置数据
        backtest_engine.set_data(df)
        
        # 创建一个简单的策略函数
        def simple_strategy(data):
            """简单的买入持有策略"""
            if len(data) < 2:
                return []
            
            # 买入第一只股票
            return [{'stock_code': df['stock_code'].iloc[0], 'action': 'buy', 'weight': 1.0}]
        
        # 设置策略
        backtest_engine.set_strategy(simple_strategy)
        
        # 运行回测
        backtest_result = backtest_engine.run()
        
        _pipeline_data["backtest_result"] = backtest_result
        
        elapsed = time.time() - start_time
        print(f"    ✓ 策略周回测完成 ({elapsed:.2f}秒)")
        
        return {
            "status": "success",
            "backtest_success": backtest_result.success,
            "annual_return": backtest_result.metrics.annual_return if backtest_result.success else None,
            "sharpe_ratio": backtest_result.metrics.sharpe_ratio if backtest_result.success else None,
            "max_drawdown": backtest_result.metrics.max_drawdown if backtest_result.success else None,
            "elapsed": elapsed
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"    ✗ 策略周回测失败: {e} ({elapsed:.2f}秒)")
        return {
            "status": "failed",
            "error": str(e),
            "elapsed": elapsed
        }


def step4_factor_decay_check() -> Dict[str, Any]:
    """因子衰减检查"""
    print("  [Step 4] 因子衰减检查...")
    import time
    start_time = time.time()
    
    global _pipeline_data
    
    try:
        from core.monitor.factor_decay import FactorDecayMonitor, FactorMetrics
        from core.infrastructure.config import get_data_paths
        from pathlib import Path
        
        # 创建因子衰减监控器
        monitor = FactorDecayMonitor()
        
        # 加载历史数据
        monitor.load()
        
        # 获取所有因子状态
        all_status = monitor.get_all_status()
        
        # 获取衰减因子
        decaying_factors = monitor.get_decaying_factors()
        
        # 生成衰减报告
        decay_report = monitor.generate_decay_report()
        
        _pipeline_data["decay_result"] = {
            "all_status": all_status,
            "decaying_factors": decaying_factors,
            "decay_report": decay_report
        }
        
        elapsed = time.time() - start_time
        print(f"    ✓ 因子衰减检查完成 ({elapsed:.2f}秒)")
        print(f"    - 总因子数: {len(all_status)}")
        print(f"    - 衰减因子数: {len(decaying_factors)}")
        
        return {
            "status": "success",
            "total_factors": len(all_status),
            "decaying_factors": len(decaying_factors),
            "decay_report": decay_report,
            "elapsed": elapsed
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"    ✗ 因子衰减检查失败: {e} ({elapsed:.2f}秒)")
        return {
            "status": "failed",
            "error": str(e),
            "elapsed": elapsed
        }


def step5_weekly_report_generation() -> Dict[str, Any]:
    """周报生成"""
    print("  [Step 5] 周报生成...")
    import time
    start_time = time.time()
    
    global _pipeline_data
    
    try:
        from core.monitor.report import ReportGenerator
        from core.infrastructure.config import get_data_paths
        from pathlib import Path
        from datetime import datetime
        
        # 创建报告生成器
        report_generator = ReportGenerator()
        
        # 准备数据
        data = {
            "factor_data": _pipeline_data.get("factor_data"),
            "signal_data": _pipeline_data.get("signal_data"),
            "backtest_result": _pipeline_data.get("backtest_result"),
            "decay_result": _pipeline_data.get("decay_result")
        }
        
        # 生成周报
        report = report_generator.generate_weekly_report(
            target_date=datetime.now().strftime("%Y-%m-%d"),
            data=data
        )
        
        # 保存报告
        report_path = report_generator._save_report(report)
        
        elapsed = time.time() - start_time
        print(f"    ✓ 周报生成完成: {report_path} ({elapsed:.2f}秒)")
        
        return {
            "status": "success",
            "report_path": report_path,
            "report_id": report.report_id,
            "elapsed": elapsed
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"    ✗ 周报生成失败: {e} ({elapsed:.2f}秒)")
        return {
            "status": "failed",
            "error": str(e),
            "elapsed": elapsed
        }


def step6_weekly_backup() -> Dict[str, Any]:
    """周备份"""
    print("  [Step 6] 周备份...")
    import time
    start_time = time.time()
    
    try:
        from core.daily.backup import DailyBackup, BackupType
        from core.infrastructure.config import get_data_paths
        from datetime import datetime
        
        # 创建备份管理器
        backup_manager = DailyBackup()
        
        # 执行周备份
        backup_result = backup_manager.backup(
            backup_type=BackupType.WEEKLY,
            date=datetime.now(),
            include_core=True,
            include_business=True,
            include_reports=True
        )
        
        elapsed = time.time() - start_time
        
        if backup_result.success:
            print(f"    ✓ 周备份完成: {backup_result.backup_path} ({elapsed:.2f}秒)")
            print(f"    - 备份大小: {backup_result.backup_size/1024/1024:.2f}MB")
            print(f"    - 文件数: {backup_result.files_count}")
            
            return {
                "status": "success",
                "backup_path": backup_result.backup_path,
                "backup_size": backup_result.backup_size,
                "files_count": backup_result.files_count,
                "verified": backup_result.verified,
                "elapsed": elapsed
            }
        else:
            print(f"    ✗ 周备份失败: {backup_result.error_message} ({elapsed:.2f}秒)")
            
            return {
                "status": "failed",
                "error": backup_result.error_message,
                "elapsed": elapsed
            }
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"    ✗ 周备份失败: {e} ({elapsed:.2f}秒)")
        return {
            "status": "failed",
            "error": str(e),
            "elapsed": elapsed
        }


def main():
    """主函数"""
    print("=" * 50)
    print("WildQuest Matrix - 周常任务调度")
    print("=" * 50)
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 检查是否是周一
    today = datetime.now()
    if today.weekday() != 0:  # 0 = Monday
        print("⚠️  警告: 今天不是周一，周常任务通常在周一执行")
        print()
    
    # 定义管线步骤
    pipeline_steps = [
        ("周线因子计算", step1_weekly_factor_calculation),
        ("周线信号生成", step2_weekly_signal_generation),
        ("策略周回测", step3_weekly_backtest),
        ("因子衰减检查", step4_factor_decay_check),
        ("周报生成", step5_weekly_report_generation),
        ("周备份", step6_weekly_backup),
    ]
    
    # 执行管线
    results = {}
    for step_name, step_func in pipeline_steps:
        print(f"\n{'=' * 50}")
        print(f"执行: {step_name}")
        print('=' * 50)
        
        result = step_func()
        results[step_name] = result
        
        if result["status"] == "failed":
            print(f"\n⚠️  {step_name} 失败，停止执行")
            break
    
    # 汇总结果
    print("\n" + "=" * 50)
    print("周常任务执行汇总")
    print("=" * 50)
    
    success_count = sum(1 for r in results.values() if r["status"] == "success")
    total_count = len(results)
    
    print(f"成功: {success_count}/{total_count}")
    print()
    
    for step_name, result in results.items():
        status_icon = "✓" if result["status"] == "success" else "✗"
        elapsed = result.get("elapsed", 0)
        print(f"{status_icon} {step_name}: {elapsed:.2f}秒")
    
    print()
    print("周常任务执行完成")
    
    return 0 if success_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())
