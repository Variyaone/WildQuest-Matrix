"""
自动化运维主控制器
整合监控、诊断、修复、改进，实现全自动运维
"""

import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from .auto_monitor import AutoMonitor, AlertLevel
from .auto_diagnose import AutoDiagnose, DiagnosisSeverity
from .auto_fix import AutoFix, FixStatus
from .auto_improve import AutoImprove, ImprovementType

from ..infrastructure.logging import get_logger
from ..infrastructure.exceptions import AppException

logger = get_logger("automation.auto_ops")


class OpsMode(Enum):
    """运维模式"""
    MONITOR_ONLY = "monitor_only"  # 仅监控
    DIAGNOSE_ONLY = "diagnose_only"  # 仅诊断
    FIX_ONLY = "fix_only"  # 仅修复
    IMPROVE_ONLY = "improve_only"  # 仅改进
    AUTO = "auto"  # 全自动（监控+诊断+修复+改进）


@dataclass
class OpsResult:
    """运维结果"""
    mode: OpsMode
    timestamp: datetime = field(default_factory=datetime.now)
    monitor_results: Dict[str, Any] = field(default_factory=dict)
    diagnoses: List[Dict[str, Any]] = field(default_factory=list)
    fix_results: Dict[str, Any] = field(default_factory=dict)
    improvement_results: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "timestamp": self.timestamp.isoformat(),
            "monitor_results": self.monitor_results,
            "diagnoses": self.diagnoses,
            "fix_results": self.fix_results,
            "improvement_results": self.improvement_results,
            "success": self.success,
            "message": self.message
        }


class AutoOpsController:
    """自动化运维控制器"""
    
    def __init__(self, workspace_path: str = None):
        self.workspace_path = workspace_path or Path.cwd()
        self.monitor = AutoMonitor(workspace_path)
        self.diagnose = AutoDiagnose(workspace_path)
        self.fix = AutoFix(workspace_path)
        self.improve = AutoImprove(workspace_path)
        
        self.results_file = self.workspace_path / "data" / "monitor" / "ops_results.json"
        self.results_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info("自动化运维控制器初始化完成")
    
    def run_monitor(self) -> Dict[str, Any]:
        """运行监控"""
        logger.info("步骤 1/4: 运行监控")
        return self.monitor.run_full_check()
    
    def run_diagnose(self, monitor_results: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """运行诊断"""
        logger.info("步骤 2/4: 运行诊断")
        
        diagnoses = self.diagnose.run_full_diagnosis()
        
        return [d.to_dict() for d in diagnoses]
    
    def run_fix(self, diagnoses: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """运行修复"""
        logger.info("步骤 3/4: 运行修复")
        
        # 只修复高优先级问题
        high_priority_diagnoses = [
            d for d in (diagnoses or [])
            if d.get("severity") in ["high", "critical"]
        ]
        
        results = self.fix.run_auto_fixes(high_priority_diagnoses)
        
        return results
    
    def run_improve(self) -> Dict[str, Any]:
        """运行改进"""
        logger.info("步骤 4/4: 运行改进")
        return self.improve.run_improvement_cycle()
    
    def run_auto_ops(self, mode: OpsMode = OpsMode.AUTO) -> OpsResult:
        """运行自动化运维"""
        logger.info("=" * 60)
        logger.info(f"开始自动化运维 (模式: {mode.value})")
        logger.info("=" * 60)
        
        result = OpsResult(mode=mode)
        
        try:
            # 1. 监控
            if mode in [OpsMode.MONITOR_ONLY, OpsMode.AUTO]:
                result.monitor_results = self.run_monitor()
                
                # 检查是否有严重问题
                active_alerts = result.monitor_results.get("active_alerts", 0)
                if active_alerts > 0:
                    logger.warning(f"发现 {active_alerts} 个活跃告警")
            
            # 2. 诊断
            if mode in [OpsMode.DIAGNOSE_ONLY, OpsMode.AUTO]:
                result.diagnoses = self.run_diagnose(result.monitor_results)
                
                if result.diagnoses:
                    logger.info(f"诊断出 {len(result.diagnoses)} 个问题")
            
            # 3. 修复
            if mode in [OpsMode.FIX_ONLY, OpsMode.AUTO]:
                result.fix_results = self.run_fix(result.diagnoses)
                
                success_count = result.fix_results.get("summary", {}).get("success", 0)
                if success_count > 0:
                    logger.info(f"成功修复 {success_count} 个问题")
            
            # 4. 改进
            if mode in [OpsMode.IMPROVE_ONLY, OpsMode.AUTO]:
                # 只有在没有严重问题时才运行改进
                critical_issues = [
                    d for d in result.diagnoses
                    if d.get("severity") == "critical"
                ]
                
                if not critical_issues:
                    result.improvement_results = self.run_improve()
                    
                    success_count = result.improvement_results.get("summary", {}).get("success", 0)
                    if success_count > 0:
                        logger.info(f"成功执行 {success_count} 项改进")
                else:
                    logger.warning("存在严重问题，跳过改进步骤")
                    result.improvement_results = {
                        "message": "存在严重问题，跳过改进步骤"
                    }
            
            result.success = True
            result.message = "自动化运维完成"
            
        except Exception as e:
            logger.error(f"自动化运维失败: {e}")
            result.success = False
            result.message = f"自动化运维失败: {str(e)}"
        
        # 保存结果
        self._save_result(result)
        
        logger.info("=" * 60)
        logger.info(f"自动化运维完成: {result.message}")
        logger.info("=" * 60)
        
        return result
    
    def _save_result(self, result: OpsResult):
        """保存运维结果"""
        try:
            results = []
            if self.results_file.exists():
                with open(self.results_file, 'r', encoding='utf-8') as f:
                    results = json.load(f)
            
            results.append(result.to_dict())
            
            # 只保留最近100条记录
            if len(results) > 100:
                results = results[-100:]
            
            with open(self.results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"保存运维结果失败: {e}")
    
    def get_ops_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取运维历史"""
        if not self.results_file.exists():
            return []
        
        try:
            with open(self.results_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            return results[-limit:]
            
        except Exception as e:
            logger.error(f"读取运维历史失败: {e}")
            return []
    
    def get_status_summary(self) -> Dict[str, Any]:
        """获取状态总结"""
        # 获取活跃告警
        active_alerts = self.monitor.get_active_alerts()
        
        # 获取最新诊断
        diagnoses = self.diagnose.get_top_diagnoses(5)
        
        # 获取改进总结
        improvement_summary = self.improve.get_improvement_summary()
        
        # 获取当前指标
        current_metrics = self.improve.get_current_metrics()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "active_alerts": {
                "total": len(active_alerts),
                "critical": len([a for a in active_alerts if a.level == AlertLevel.CRITICAL]),
                "error": len([a for a in active_alerts if a.level == AlertLevel.ERROR]),
                "warning": len([a for a in active_alerts if a.level == AlertLevel.WARNING])
            },
            "top_diagnoses": [d.to_dict() for d in diagnoses],
            "improvement_summary": improvement_summary,
            "current_metrics": current_metrics
        }
    
    def run_scheduled_ops(self, interval_hours: int = 24):
        """运行定时运维"""
        logger.info(f"启动定时运维，间隔: {interval_hours} 小时")
        
        while True:
            try:
                # 运行自动化运维
                result = self.run_auto_ops(OpsMode.AUTO)
                
                # 等待下一次运行
                logger.info(f"等待 {interval_hours} 小时后运行下一次运维")
                
                # 这里应该使用异步等待
                # 暂时使用同步等待
                import time
                time.sleep(interval_hours * 3600)
                
            except KeyboardInterrupt:
                logger.info("收到中断信号，停止定时运维")
                break
            except Exception as e:
                logger.error(f"定时运维出错: {e}")
                import time
                time.sleep(3600)  # 出错后等待1小时再重试


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="自动化运维控制器")
    parser.add_argument("--mode", type=str, default="auto",
                       choices=["monitor_only", "diagnose_only", "fix_only", "improve_only", "auto"],
                       help="运维模式")
    parser.add_argument("--scheduled", action="store_true", help="运行定时运维")
    parser.add_argument("--interval", type=int, default=24, help="定时运维间隔（小时）")
    
    args = parser.parse_args()
    
    controller = AutoOpsController()
    
    if args.scheduled:
        # 运行定时运维
        controller.run_scheduled_ops(args.interval)
    else:
        # 运行单次运维
        mode = OpsMode(args.mode)
        result = controller.run_auto_ops(mode)
        
        print(f"运维结果: {result.message}")
        print(f"成功: {result.success}")
        
        if result.monitor_results:
            print(f"\n监控结果:")
            print(f"  活跃告警: {result.monitor_results.get('active_alerts', 0)}")
        
        if result.diagnoses:
            print(f"\n诊断结果: {len(result.diagnoses)} 个问题")
            for diag in result.diagnoses[:3]:
                print(f"  - {diag['issue']} ({diag['severity']})")
        
        if result.fix_results:
            summary = result.fix_results.get("summary", {})
            print(f"\n修复结果:")
            print(f"  成功: {summary.get('success', 0)}/{summary.get('total', 0)}")
        
        if result.improvement_results:
            summary = result.improvement_results.get("summary", {})
            print(f"\n改进结果:")
            print(f"  成功: {summary.get('success', 0)}/{summary.get('total', 0)}")


if __name__ == "__main__":
    main()
