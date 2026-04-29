"""
自动化运维定时任务
定期运行监控、诊断、修复、改进
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

from core.automation.auto_ops import AutoOpsController, OpsMode
from core.infrastructure.logging import get_logger

logger = get_logger("automation.scheduler")


class AutoOpsScheduler:
    """自动化运维调度器"""
    
    def __init__(self, workspace_path: str = None):
        self.workspace_path = workspace_path or Path.cwd()
        self.controller = AutoOpsController(workspace_path)
        
        self.schedule_file = self.workspace_path / "data" / "monitor" / "schedule.json"
        self.schedule_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载调度配置
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载调度配置"""
        default_config = {
            "enabled": True,
            "interval_hours": 24,
            "mode": "auto",
            "last_run": None,
            "next_run": None
        }
        
        if self.schedule_file.exists():
            try:
                with open(self.schedule_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    default_config.update(config)
            except Exception as e:
                logger.warning(f"加载调度配置失败: {e}")
        
        return default_config
    
    def _save_config(self):
        """保存调度配置"""
        try:
            with open(self.schedule_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存调度配置失败: {e}")
    
    def should_run(self) -> bool:
        """检查是否应该运行"""
        if not self.config["enabled"]:
            return False
        
        if self.config["last_run"] is None:
            return True
        
        last_run = datetime.fromisoformat(self.config["last_run"])
        next_run = last_run + timedelta(hours=self.config["interval_hours"])
        
        return datetime.now() >= next_run
    
    def run(self) -> Dict[str, Any]:
        """运行定时任务"""
        logger.info("=" * 60)
        logger.info("开始定时自动化运维")
        logger.info("=" * 60)
        
        # 检查是否应该运行
        if not self.should_run():
            logger.info("未到运行时间，跳过")
            
            next_run = datetime.fromisoformat(self.config["last_run"]) + timedelta(hours=self.config["interval_hours"])
            logger.info(f"下次运行时间: {next_run.isoformat()}")
            
            return {
                "status": "skipped",
                "message": "未到运行时间",
                "next_run": next_run.isoformat()
            }
        
        # 运行自动化运维
        mode = OpsMode(self.config["mode"])
        result = self.controller.run_auto_ops(mode)
        
        # 更新配置
        self.config["last_run"] = datetime.now().isoformat()
        self.config["next_run"] = (datetime.now() + timedelta(hours=self.config["interval_hours"])).isoformat()
        self._save_config()
        
        logger.info(f"下次运行时间: {self.config['next_run']}")
        
        return {
            "status": "completed",
            "result": result.to_dict(),
            "next_run": self.config["next_run"]
        }
    
    def update_config(self, enabled: bool = None, interval_hours: int = None, mode: str = None):
        """更新配置"""
        if enabled is not None:
            self.config["enabled"] = enabled
        
        if interval_hours is not None:
            self.config["interval_hours"] = interval_hours
        
        if mode is not None:
            self.config["mode"] = mode
        
        self._save_config()
        
        logger.info(f"调度配置已更新: {self.config}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        status = {
            "enabled": self.config["enabled"],
            "interval_hours": self.config["interval_hours"],
            "mode": self.config["mode"],
            "last_run": self.config["last_run"],
            "next_run": self.config["next_run"]
        }
        
        # 获取运维历史
        history = self.controller.get_ops_history(5)
        status["recent_history"] = history
        
        # 获取状态总结
        summary = self.controller.get_status_summary()
        status["summary"] = summary
        
        return status


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="自动化运维调度器")
    parser.add_argument("--run", action="store_true", help="立即运行")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--enable", action="store_true", help="启用定时任务")
    parser.add_argument("--disable", action="store_true", help="禁用定时任务")
    parser.add_argument("--interval", type=int, help="设置运行间隔（小时）")
    parser.add_argument("--mode", type=str, choices=["monitor_only", "diagnose_only", "fix_only", "improve_only", "auto"],
                       help="设置运维模式")
    
    args = parser.parse_args()
    
    scheduler = AutoOpsScheduler()
    
    if args.status:
        # 查看状态
        status = scheduler.get_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
    
    elif args.enable:
        # 启用定时任务
        scheduler.update_config(enabled=True)
        print("定时任务已启用")
    
    elif args.disable:
        # 禁用定时任务
        scheduler.update_config(enabled=False)
        print("定时任务已禁用")
    
    elif args.interval or args.mode:
        # 更新配置
        scheduler.update_config(interval_hours=args.interval, mode=args.mode)
        print("调度配置已更新")
    
    elif args.run:
        # 立即运行
        result = scheduler.run()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    else:
        # 默认运行
        result = scheduler.run()
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
