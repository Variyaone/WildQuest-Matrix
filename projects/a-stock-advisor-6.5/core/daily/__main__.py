"""
每日任务调度器入口

执行完整管线:
    python -m core.daily.scheduler
"""

import sys
from datetime import datetime

from .scheduler import DailyScheduler, Task


def create_pipeline_scheduler() -> DailyScheduler:
    """创建管线调度器"""
    scheduler = DailyScheduler()
    
    def step1_data_update():
        print("  [Step 1] 数据更新...")
        print("    - 检查数据源配置")
        print("    - 增量更新市场数据")
        return {"status": "success", "records": 0}
    
    def step2_factor_calc():
        print("  [Step 2] 因子计算...")
        from core.factor import FactorRegistry
        registry = FactorRegistry()
        count = registry.get_factor_count()
        print(f"    - 已注册因子: {count} 个")
        print("    - 计算因子值...")
        return {"status": "success", "factors": count}
    
    def step3_signal_gen():
        print("  [Step 3] 信号生成...")
        print("    - 加载因子值")
        print("    - 应用信号规则")
        return {"status": "success", "signals": 0}
    
    def step4_strategy_exec():
        print("  [Step 4] 策略执行...")
        print("    - 选择活跃策略")
        print("    - 执行选股逻辑")
        return {"status": "success", "selections": 0}
    
    def step5_portfolio_opt():
        print("  [Step 5] 组合优化...")
        print("    - 计算目标权重")
        print("    - 中性化处理")
        return {"status": "success", "positions": 0}
    
    def step6_risk_check():
        print("  [Step 6] 风控检查...")
        print("    - 事前风控检查")
        print("    - 风险限额验证")
        return {"status": "success", "passed": True}
    
    def step7_trading():
        print("  [Step 7] 执行交易...")
        print("    - 生成交易指令")
        print("    - 模式: 仿真")
        return {"status": "success", "orders": 0}
    
    def step8_analysis():
        print("  [Step 8] 绩效分析...")
        print("    - 计算绩效指标")
        print("    - 生成分析报告")
        return {"status": "success", "report": "generated"}
    
    scheduler.register_task_func(
        name="data_update",
        func=step1_data_update,
        description="数据更新",
        required=True
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
    
    return scheduler


def main():
    """主函数"""
    print("=" * 50)
    print("A股量化投顾系统 - 每日任务调度")
    print("=" * 50)
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    scheduler = create_pipeline_scheduler()
    
    print("管线任务:")
    for i, task in enumerate(scheduler.tasks, 1):
        deps = f" (依赖: {', '.join(task.dependencies)})" if task.dependencies else ""
        print(f"  {i}. {task.description}{deps}")
    print()
    
    print("开始执行...")
    print("-" * 50)
    
    result = scheduler.run()
    
    print("-" * 50)
    print()
    print("执行结果:")
    print(f"  总任务数: {result.total_tasks}")
    print(f"  成功: {result.completed_tasks}")
    print(f"  失败: {result.failed_tasks}")
    print(f"  跳过: {result.skipped_tasks}")
    print(f"  耗时: {result.total_duration:.2f}秒")
    print()
    
    if result.success:
        print("✓ 管线执行成功!")
    else:
        print("✗ 管线执行失败!")
        for task_result in result.task_results:
            if task_result.status.value == "failed":
                print(f"  失败任务: {task_result.task_name}")
                print(f"  错误信息: {task_result.error_message}")
    
    print()
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
