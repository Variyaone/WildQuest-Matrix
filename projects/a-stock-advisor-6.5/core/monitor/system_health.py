"""
系统健康监控模块

监控系统运行状态，包括数据健康、任务健康、资源健康等。
"""

import json
import os
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import pandas as pd
import numpy as np

from core.infrastructure.logging import get_logger


class SystemStatus(Enum):
    """系统状态"""
    HEALTHY = "healthy"         # 健康
    WARNING = "warning"         # 警告
    CRITICAL = "critical"       # 严重
    UNKNOWN = "unknown"         # 未知


@dataclass
class DataHealth:
    """数据健康指标"""
    update_status: str = "normal"
    quality_score: float = 100.0
    delay_hours: float = 0.0
    completeness: float = 100.0
    last_update: str = ""
    score: float = 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskHealth:
    """任务健康指标"""
    success_rate: float = 100.0
    avg_duration: float = 0.0
    failed_count: int = 0
    queue_size: int = 0
    score: float = 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResourceHealth:
    """资源健康指标"""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    network_latency: float = 0.0
    score: float = 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ServiceHealth:
    """服务健康指标"""
    availability: float = 100.0
    response_time: float = 0.0
    error_rate: float = 0.0
    restart_count: int = 0
    score: float = 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SystemHealthReport:
    """系统健康报告"""
    system_status: SystemStatus
    overall_score: float
    
    data_health: DataHealth = field(default_factory=DataHealth)
    task_health: TaskHealth = field(default_factory=TaskHealth)
    resource_health: ResourceHealth = field(default_factory=ResourceHealth)
    service_health: ServiceHealth = field(default_factory=ServiceHealth)
    
    check_items: List[Dict[str, Any]] = field(default_factory=list)
    warning_messages: List[str] = field(default_factory=list)
    last_check: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_status": self.system_status.value,
            "overall_score": self.overall_score,
            "data_health": self.data_health.to_dict(),
            "task_health": self.task_health.to_dict(),
            "resource_health": self.resource_health.to_dict(),
            "service_health": self.service_health.to_dict(),
            "check_items": self.check_items,
            "warning_messages": self.warning_messages,
            "last_check": self.last_check
        }


class SystemHealthMonitor:
    """系统健康监控器"""
    
    RESOURCE_THRESHOLDS = {
        "cpu_warning": 70.0,
        "cpu_critical": 90.0,
        "memory_warning": 70.0,
        "memory_critical": 90.0,
        "disk_warning": 80.0,
        "disk_critical": 95.0,
        "disk_space_min_gb": 10.0
    }
    
    DATA_THRESHOLDS = {
        "quality_warning": 80.0,
        "quality_critical": 60.0,
        "delay_warning_hours": 24.0,
        "delay_critical_hours": 48.0,
        "completeness_warning": 95.0,
        "completeness_critical": 90.0
    }
    
    def __init__(
        self,
        monitor_id: str = "main",
        storage_path: str = "./data/system_health"
    ):
        self.monitor_id = monitor_id
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger("monitor.system_health")
        
        self.current_report: Optional[SystemHealthReport] = None
        self.health_history: List[SystemHealthReport] = []
        self._check_counter = 0
    
    def check_system_health(
        self,
        data_info: Optional[Dict[str, Any]] = None,
        task_info: Optional[Dict[str, Any]] = None,
        service_info: Optional[Dict[str, Any]] = None
    ) -> SystemHealthReport:
        """检查系统健康"""
        self._check_counter += 1
        
        data_health = self._check_data_health(data_info)
        task_health = self._check_task_health(task_info)
        resource_health = self._check_resource_health()
        service_health = self._check_service_health(service_info)
        
        overall_score = (
            data_health.score * 0.30 +
            task_health.score * 0.20 +
            resource_health.score * 0.30 +
            service_health.score * 0.20
        )
        
        if overall_score >= 80:
            system_status = SystemStatus.HEALTHY
        elif overall_score >= 60:
            system_status = SystemStatus.WARNING
        else:
            system_status = SystemStatus.CRITICAL
        
        check_items = self._generate_check_items(
            data_health, task_health, resource_health, service_health
        )
        warnings = self._generate_warnings(
            data_health, task_health, resource_health, service_health
        )
        
        report = SystemHealthReport(
            system_status=system_status,
            overall_score=overall_score,
            data_health=data_health,
            task_health=task_health,
            resource_health=resource_health,
            service_health=service_health,
            check_items=check_items,
            warning_messages=warnings,
            last_check=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        self.current_report = report
        self.health_history.append(report)
        
        if len(self.health_history) > 1000:
            self.health_history = self.health_history[-1000:]
        
        self.logger.info(f"系统健康检查完成: 状态={system_status.value}, 得分={overall_score:.1f}")
        return report
    
    def _check_data_health(self, data_info: Optional[Dict[str, Any]]) -> DataHealth:
        """检查数据健康"""
        if not data_info:
            return DataHealth(score=100.0)
        
        update_status = data_info.get("update_status", "normal")
        quality_score = data_info.get("quality_score", 100.0)
        delay_hours = data_info.get("delay_hours", 0.0)
        completeness = data_info.get("completeness", 100.0)
        last_update = data_info.get("last_update", "")
        
        score = 100.0
        
        if update_status != "normal":
            score -= 20
        
        if quality_score < self.DATA_THRESHOLDS["quality_critical"]:
            score -= 30
        elif quality_score < self.DATA_THRESHOLDS["quality_warning"]:
            score -= 15
        
        if delay_hours > self.DATA_THRESHOLDS["delay_critical_hours"]:
            score -= 25
        elif delay_hours > self.DATA_THRESHOLDS["delay_warning_hours"]:
            score -= 10
        
        if completeness < self.DATA_THRESHOLDS["completeness_critical"]:
            score -= 25
        elif completeness < self.DATA_THRESHOLDS["completeness_warning"]:
            score -= 10
        
        return DataHealth(
            update_status=update_status,
            quality_score=quality_score,
            delay_hours=delay_hours,
            completeness=completeness,
            last_update=last_update,
            score=max(0, min(100, score))
        )
    
    def _check_task_health(self, task_info: Optional[Dict[str, Any]]) -> TaskHealth:
        """检查任务健康"""
        if not task_info:
            return TaskHealth(score=100.0)
        
        success_rate = task_info.get("success_rate", 100.0)
        avg_duration = task_info.get("avg_duration", 0.0)
        failed_count = task_info.get("failed_count", 0)
        queue_size = task_info.get("queue_size", 0)
        
        score = 100.0
        
        if success_rate < 90:
            score -= (100 - success_rate) * 0.5
        
        if failed_count > 5:
            score -= 20
        elif failed_count > 0:
            score -= 5
        
        if queue_size > 100:
            score -= 15
        elif queue_size > 50:
            score -= 5
        
        return TaskHealth(
            success_rate=success_rate,
            avg_duration=avg_duration,
            failed_count=failed_count,
            queue_size=queue_size,
            score=max(0, min(100, score))
        )
    
    def _check_resource_health(self) -> ResourceHealth:
        """检查资源健康"""
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            
            score = 100.0
            
            if cpu_usage > self.RESOURCE_THRESHOLDS["cpu_critical"]:
                score -= 30
            elif cpu_usage > self.RESOURCE_THRESHOLDS["cpu_warning"]:
                score -= 15
            
            if memory_usage > self.RESOURCE_THRESHOLDS["memory_critical"]:
                score -= 30
            elif memory_usage > self.RESOURCE_THRESHOLDS["memory_warning"]:
                score -= 15
            
            if disk_usage > self.RESOURCE_THRESHOLDS["disk_critical"]:
                score -= 40
            elif disk_usage > self.RESOURCE_THRESHOLDS["disk_warning"]:
                score -= 20
            
            disk_free_gb = disk.free / (1024 ** 3)
            if disk_free_gb < self.RESOURCE_THRESHOLDS["disk_space_min_gb"]:
                score -= 30
            
            return ResourceHealth(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                network_latency=0.0,
                score=max(0, min(100, score))
            )
        
        except Exception as e:
            self.logger.error(f"获取资源信息失败: {e}")
            return ResourceHealth(score=0.0)
    
    def _check_service_health(self, service_info: Optional[Dict[str, Any]]) -> ServiceHealth:
        """检查服务健康"""
        if not service_info:
            return ServiceHealth(score=100.0)
        
        availability = service_info.get("availability", 100.0)
        response_time = service_info.get("response_time", 0.0)
        error_rate = service_info.get("error_rate", 0.0)
        restart_count = service_info.get("restart_count", 0)
        
        score = 100.0
        
        if availability < 99:
            score -= (100 - availability) * 2
        
        if error_rate > 0.05:
            score -= 30
        elif error_rate > 0.01:
            score -= 15
        
        if restart_count > 5:
            score -= 20
        elif restart_count > 0:
            score -= 5
        
        return ServiceHealth(
            availability=availability,
            response_time=response_time,
            error_rate=error_rate,
            restart_count=restart_count,
            score=max(0, min(100, score))
        )
    
    def _generate_check_items(
        self,
        data: DataHealth,
        task: TaskHealth,
        resource: ResourceHealth,
        service: ServiceHealth
    ) -> List[Dict[str, Any]]:
        """生成检查项"""
        items = [
            {
                "name": "数据更新",
                "status": "pass" if data.update_status == "normal" else "fail",
                "message": f"更新状态: {data.update_status}"
            },
            {
                "name": "数据质量",
                "status": "pass" if data.quality_score >= 80 else "warning" if data.quality_score >= 60 else "fail",
                "message": f"质量分数: {data.quality_score:.1f}"
            },
            {
                "name": "任务执行",
                "status": "pass" if task.success_rate >= 95 else "warning" if task.success_rate >= 90 else "fail",
                "message": f"成功率: {task.success_rate:.1f}%"
            },
            {
                "name": "CPU使用率",
                "status": "pass" if resource.cpu_usage < 70 else "warning" if resource.cpu_usage < 90 else "fail",
                "message": f"使用率: {resource.cpu_usage:.1f}%"
            },
            {
                "name": "内存使用率",
                "status": "pass" if resource.memory_usage < 70 else "warning" if resource.memory_usage < 90 else "fail",
                "message": f"使用率: {resource.memory_usage:.1f}%"
            },
            {
                "name": "磁盘使用率",
                "status": "pass" if resource.disk_usage < 80 else "warning" if resource.disk_usage < 95 else "fail",
                "message": f"使用率: {resource.disk_usage:.1f}%"
            },
            {
                "name": "服务可用性",
                "status": "pass" if service.availability >= 99 else "warning" if service.availability >= 95 else "fail",
                "message": f"可用性: {service.availability:.1f}%"
            }
        ]
        
        return items
    
    def _generate_warnings(
        self,
        data: DataHealth,
        task: TaskHealth,
        resource: ResourceHealth,
        service: ServiceHealth
    ) -> List[str]:
        """生成警告信息"""
        warnings = []
        
        if data.update_status != "normal":
            warnings.append(f"数据更新异常: {data.update_status}")
        
        if data.quality_score < 80:
            warnings.append(f"数据质量分数低: {data.quality_score:.1f}")
        
        if data.delay_hours > 24:
            warnings.append(f"数据延迟: {data.delay_hours:.1f}小时")
        
        if task.success_rate < 95:
            warnings.append(f"任务成功率低: {task.success_rate:.1f}%")
        
        if task.failed_count > 0:
            warnings.append(f"任务失败数: {task.failed_count}")
        
        if resource.cpu_usage > self.RESOURCE_THRESHOLDS["cpu_warning"]:
            warnings.append(f"CPU使用率高: {resource.cpu_usage:.1f}%")
        
        if resource.memory_usage > self.RESOURCE_THRESHOLDS["memory_warning"]:
            warnings.append(f"内存使用率高: {resource.memory_usage:.1f}%")
        
        if resource.disk_usage > self.RESOURCE_THRESHOLDS["disk_warning"]:
            warnings.append(f"磁盘使用率高: {resource.disk_usage:.1f}%")
        
        if service.availability < 99:
            warnings.append(f"服务可用性低: {service.availability:.1f}%")
        
        if service.error_rate > 0.01:
            warnings.append(f"服务错误率高: {service.error_rate:.2%}")
        
        return warnings
    
    def get_current_status(self) -> Optional[SystemHealthReport]:
        """获取当前状态"""
        return self.current_report
    
    def get_health_history(self, count: int = 100) -> List[SystemHealthReport]:
        """获取健康历史"""
        return self.health_history[-count:]
    
    def get_status_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        if not self.current_report:
            return {"status": "unknown", "message": "尚未进行健康检查"}
        
        return {
            "status": self.current_report.system_status.value,
            "overall_score": self.current_report.overall_score,
            "data_score": self.current_report.data_health.score,
            "task_score": self.current_report.task_health.score,
            "resource_score": self.current_report.resource_health.score,
            "service_score": self.current_report.service_health.score,
            "warning_count": len(self.current_report.warning_messages),
            "last_check": self.current_report.last_check
        }
    
    def generate_health_report(self) -> str:
        """生成健康报告"""
        if not self.current_report:
            return "# 系统健康报告\n\n尚未进行健康检查"
        
        report = self.current_report
        
        lines = [
            "# 系统健康报告",
            "",
            f"**检查时间**: {report.last_check}",
            f"**系统状态**: {report.system_status.value}",
            f"**总体得分**: {report.overall_score:.1f}",
            "",
            "## 检查项状态",
            ""
        ]
        
        for item in report.check_items:
            status_icon = "✅" if item["status"] == "pass" else "⚠️" if item["status"] == "warning" else "❌"
            lines.append(f"- {status_icon} **{item['name']}**: {item['message']}")
        
        lines.extend([
            "",
            "## 详细指标",
            "",
            "### 数据健康",
            f"- 更新状态: {report.data_health.update_status}",
            f"- 质量分数: {report.data_health.quality_score:.1f}",
            f"- 数据延迟: {report.data_health.delay_hours:.1f}小时",
            f"- 完整性: {report.data_health.completeness:.1f}%",
            f"- 得分: {report.data_health.score:.1f}",
            "",
            "### 任务健康",
            f"- 成功率: {report.task_health.success_rate:.1f}%",
            f"- 失败数: {report.task_health.failed_count}",
            f"- 队列大小: {report.task_health.queue_size}",
            f"- 得分: {report.task_health.score:.1f}",
            "",
            "### 资源健康",
            f"- CPU使用率: {report.resource_health.cpu_usage:.1f}%",
            f"- 内存使用率: {report.resource_health.memory_usage:.1f}%",
            f"- 磁盘使用率: {report.resource_health.disk_usage:.1f}%",
            f"- 得分: {report.resource_health.score:.1f}",
            "",
            "### 服务健康",
            f"- 可用性: {report.service_health.availability:.1f}%",
            f"- 响应时间: {report.service_health.response_time:.1f}ms",
            f"- 错误率: {report.service_health.error_rate:.2%}",
            f"- 得分: {report.service_health.score:.1f}"
        ])
        
        if report.warning_messages:
            lines.extend([
                "",
                "## 警告信息",
                ""
            ])
            for msg in report.warning_messages:
                lines.append(f"- ⚠️ {msg}")
        
        return "\n".join(lines)
    
    def save(self) -> bool:
        """保存监控数据"""
        if not self.current_report:
            return False
        
        report_file = self.storage_path / "current_report.json"
        history_file = self.storage_path / "health_history.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.current_report.to_dict(), f, ensure_ascii=False, indent=2)
        
        history_data = [r.to_dict() for r in self.health_history[-100:]]
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info("保存系统健康监控数据")
        return True
    
    def load(self) -> bool:
        """加载监控数据"""
        report_file = self.storage_path / "current_report.json"
        history_file = self.storage_path / "health_history.json"
        
        if report_file.exists():
            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.current_report = SystemHealthReport(
                    system_status=SystemStatus(data["system_status"]),
                    overall_score=data["overall_score"],
                    data_health=DataHealth(**data["data_health"]),
                    task_health=TaskHealth(**data["task_health"]),
                    resource_health=ResourceHealth(**data["resource_health"]),
                    service_health=ServiceHealth(**data["service_health"]),
                    check_items=data["check_items"],
                    warning_messages=data["warning_messages"],
                    last_check=data["last_check"]
                )
            except Exception as e:
                self.logger.error(f"加载当前报告失败: {e}")
        
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                
                for data in history_data:
                    report = SystemHealthReport(
                        system_status=SystemStatus(data["system_status"]),
                        overall_score=data["overall_score"],
                        data_health=DataHealth(**data["data_health"]),
                        task_health=TaskHealth(**data["task_health"]),
                        resource_health=ResourceHealth(**data["resource_health"]),
                        service_health=ServiceHealth(**data["service_health"]),
                        check_items=data["check_items"],
                        warning_messages=data["warning_messages"],
                        last_check=data["last_check"]
                    )
                    self.health_history.append(report)
            except Exception as e:
                self.logger.error(f"加载历史记录失败: {e}")
        
        self.logger.info("加载系统健康监控数据")
        return True
