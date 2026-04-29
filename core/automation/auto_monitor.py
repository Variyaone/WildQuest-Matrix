"""
自动监控系统
持续监控策略表现，自动发现问题
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from ..infrastructure.logging import get_logger
from ..infrastructure.exceptions import AppException

logger = get_logger("automation.auto_monitor")


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """告警信息"""
    level: AlertLevel
    category: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "category": self.category,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved
        }


class AutoMonitor:
    """自动监控器"""
    
    def __init__(self, workspace_path: str = None):
        self.workspace_path = workspace_path or Path.cwd()
        self.alerts: List[Alert] = []
        self.alerts_file = self.workspace_path / "data" / "monitor" / "alerts.json"
        self.alerts_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载历史告警
        self._load_alerts()
    
    def _load_alerts(self):
        """加载历史告警"""
        if self.alerts_file.exists():
            try:
                with open(self.alerts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for alert_data in data:
                        alert = Alert(
                            level=AlertLevel(alert_data["level"]),
                            category=alert_data["category"],
                            message=alert_data["message"],
                            details=alert_data.get("details", {}),
                            timestamp=datetime.fromisoformat(alert_data["timestamp"]),
                            resolved=alert_data.get("resolved", False)
                        )
                        self.alerts.append(alert)
                logger.info(f"加载了 {len(self.alerts)} 条历史告警")
            except Exception as e:
                logger.warning(f"加载历史告警失败: {e}")
    
    def _save_alerts(self):
        """保存告警"""
        try:
            with open(self.alerts_file, 'w', encoding='utf-8') as f:
                json.dump([alert.to_dict() for alert in self.alerts], f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存告警失败: {e}")
    
    def add_alert(self, level: AlertLevel, category: str, message: str, details: Dict[str, Any] = None):
        """添加告警"""
        alert = Alert(
            level=level,
            category=category,
            message=message,
            details=details or {}
        )
        self.alerts.append(alert)
        self._save_alerts()
        
        # 记录日志
        log_func = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical
        }[level]
        
        log_func(f"[{category}] {message}")
        if details:
            log_func(f"详情: {details}")
    
    def get_active_alerts(self, level: AlertLevel = None) -> List[Alert]:
        """获取未解决的告警"""
        alerts = [a for a in self.alerts if not a.resolved]
        if level:
            alerts = [a for a in alerts if a.level == level]
        return alerts
    
    def resolve_alert(self, alert_index: int):
        """解决告警"""
        if 0 <= alert_index < len(self.alerts):
            self.alerts[alert_index].resolved = True
            self._save_alerts()
            logger.info(f"已解决告警: {self.alerts[alert_index].message}")
    
    def check_pipeline_data(self) -> Dict[str, Any]:
        """检查管线数据"""
        pipeline_file = self.workspace_path / "data" / "pipeline_data.json"
        
        if not pipeline_file.exists():
            self.add_alert(
                AlertLevel.ERROR,
                "data",
                "管线数据文件不存在",
                {"file": str(pipeline_file)}
            )
            return {"status": "error", "message": "管线数据文件不存在"}
        
        try:
            with open(pipeline_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            issues = []
            
            # 检查风险违规
            risk_check_result = data.get("risk_check_result", {})
            if risk_check_result.get("passed") == False:
                violations = risk_check_result.get("violations", "[]")
                issues.append(f"风险检查未通过: {violations}")
                
                self.add_alert(
                    AlertLevel.ERROR,
                    "risk",
                    "风险检查未通过",
                    {"violations": violations}
                )
            
            # 检查持仓
            position_status = data.get("position_status", {})
            if position_status.get("has_position") and position_status.get("position_count", 0) == 0:
                issues.append("持仓状态不一致")
                self.add_alert(
                    AlertLevel.WARNING,
                    "position",
                    "持仓状态不一致",
                    position_status
                )
            
            # 检查因子数据
            active_factor_ids = data.get("active_factor_ids", [])
            if len(active_factor_ids) < 10:
                issues.append(f"活跃因子数量过少: {len(active_factor_ids)}")
                self.add_alert(
                    AlertLevel.WARNING,
                    "factor",
                    f"活跃因子数量过少: {len(active_factor_ids)}",
                    {"factor_count": len(active_factor_ids)}
                )
            
            return {
                "status": "ok" if not issues else "warning",
                "issues": issues,
                "data": data
            }
            
        except Exception as e:
            self.add_alert(
                AlertLevel.ERROR,
                "data",
                f"读取管线数据失败: {str(e)}",
                {"error": str(e)}
            )
            return {"status": "error", "message": str(e)}
    
    def check_quality_gates(self) -> Dict[str, Any]:
        """检查质量门控"""
        quality_dir = self.workspace_path / "data" / "quality_gates"
        
        if not quality_dir.exists():
            self.add_alert(
                AlertLevel.WARNING,
                "quality",
                "质量门控目录不存在",
                {"dir": str(quality_dir)}
            )
            return {"status": "warning", "message": "质量门控目录不存在"}
        
        # 获取最新的质量门控日志
        gate_logs = sorted(quality_dir.glob("gate_log_*.json"), reverse=True)
        
        if not gate_logs:
            self.add_alert(
                AlertLevel.WARNING,
                "quality",
                "没有质量门控日志",
                {}
            )
            return {"status": "warning", "message": "没有质量门控日志"}
        
        latest_log = gate_logs[0]
        
        try:
            with open(latest_log, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            issues = []
            
            for log in logs:
                stage = log.get("stage")
                passed = log.get("passed", True)
                
                if not passed:
                    failures = log.get("failures", [])
                    issues.append(f"{stage} 未通过: {failures}")
                    
                    self.add_alert(
                        AlertLevel.ERROR,
                        "quality",
                        f"{stage} 质量门控未通过",
                        {"stage": stage, "failures": failures}
                    )
            
            return {
                "status": "ok" if not issues else "error",
                "issues": issues,
                "latest_log": str(latest_log)
            }
            
        except Exception as e:
            self.add_alert(
                AlertLevel.ERROR,
                "quality",
                f"读取质量门控日志失败: {str(e)}",
                {"error": str(e)}
            )
            return {"status": "error", "message": str(e)}
    
    def check_backtest_quality(self) -> Dict[str, Any]:
        """检查回测质量"""
        reports_dir = self.workspace_path / "data" / "reports"
        
        if not reports_dir.exists():
            self.add_alert(
                AlertLevel.WARNING,
                "backtest",
                "回测报告目录不存在",
                {"dir": str(reports_dir)}
            )
            return {"status": "warning", "message": "回测报告目录不存在"}
        
        # 查找最新的性能指标
        metric_files = sorted(reports_dir.glob("performance_metrics_*.json"), reverse=True)
        
        if not metric_files:
            self.add_alert(
                AlertLevel.WARNING,
                "backtest",
                "没有回测性能指标",
                {}
            )
            return {"status": "warning", "message": "没有回测性能指标"}
        
        latest_metrics = metric_files[0]
        
        try:
            with open(latest_metrics, 'r', encoding='utf-8') as f:
                metrics = json.load(f)
            
            issues = []
            
            # 检查关键指标
            sharpe = metrics.get("sharpe_ratio", {}).get("value", 0)
            if sharpe < 1.0:
                issues.append(f"夏普比率过低: {sharpe:.2f}")
                self.add_alert(
                    AlertLevel.WARNING,
                    "backtest",
                    f"夏普比率过低: {sharpe:.2f}",
                    {"sharpe_ratio": sharpe}
                )
            
            max_dd = abs(metrics.get("max_drawdown", {}).get("value", 0))
            if max_dd > 0.20:
                issues.append(f"最大回撤过大: {max_dd:.2%}")
                self.add_alert(
                    AlertLevel.WARNING,
                    "backtest",
                    f"最大回撤过大: {max_dd:.2%}",
                    {"max_drawdown": max_dd}
                )
            
            annual_return = metrics.get("annual_return", {}).get("value", 0)
            if annual_return < 0.10:
                issues.append(f"年化收益过低: {annual_return:.2%}")
                self.add_alert(
                    AlertLevel.WARNING,
                    "backtest",
                    f"年化收益过低: {annual_return:.2%}",
                    {"annual_return": annual_return}
                )
            
            return {
                "status": "ok" if not issues else "warning",
                "issues": issues,
                "metrics": metrics
            }
            
        except Exception as e:
            self.add_alert(
                AlertLevel.ERROR,
                "backtest",
                f"读取回测指标失败: {str(e)}",
                {"error": str(e)}
            )
            return {"status": "error", "message": str(e)}
    
    def run_full_check(self) -> Dict[str, Any]:
        """运行完整检查"""
        logger.info("=" * 60)
        logger.info("开始自动监控检查")
        logger.info("=" * 60)
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        # 检查管线数据
        results["checks"]["pipeline"] = self.check_pipeline_data()
        
        # 检查质量门控
        results["checks"]["quality_gates"] = self.check_quality_gates()
        
        # 检查回测质量
        results["checks"]["backtest"] = self.check_backtest_quality()
        
        # 统计告警
        active_alerts = self.get_active_alerts()
        results["active_alerts"] = len(active_alerts)
        results["alert_summary"] = {
            "critical": len([a for a in active_alerts if a.level == AlertLevel.CRITICAL]),
            "error": len([a for a in active_alerts if a.level == AlertLevel.ERROR]),
            "warning": len([a for a in active_alerts if a.level == AlertLevel.WARNING]),
            "info": len([a for a in active_alerts if a.level == AlertLevel.INFO])
        }
        
        logger.info("=" * 60)
        logger.info(f"监控检查完成，活跃告警: {results['active_alerts']}")
        logger.info("=" * 60)
        
        return results


def main():
    """主函数"""
    monitor = AutoMonitor()
    results = monitor.run_full_check()
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
