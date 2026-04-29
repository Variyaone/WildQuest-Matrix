"""
自动修复系统
自动执行修复操作，解决已诊断的问题
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import sys

from ..infrastructure.logging import get_logger
from ..infrastructure.exceptions import AppException

logger = get_logger("automation.auto_fix")


class FixStatus(Enum):
    """修复状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class FixAction:
    """修复动作"""
    name: str
    description: str
    status: FixStatus = FixStatus.PENDING
    result: str = ""
    error: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }


class AutoFix:
    """自动修复器"""
    
    def __init__(self, workspace_path: str = None):
        self.workspace_path = workspace_path or Path.cwd()
        self.fixes: List[FixAction] = []
        self.fixes_file = self.workspace_path / "data" / "monitor" / "fixes.json"
        self.fixes_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载历史修复
        self._load_fixes()
    
    def _load_fixes(self):
        """加载历史修复"""
        if self.fixes_file.exists():
            try:
                with open(self.fixes_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for fix_data in data:
                        fix = FixAction(
                            name=fix_data["name"],
                            description=fix_data["description"],
                            status=FixStatus(fix_data["status"]),
                            result=fix_data.get("result", ""),
                            error=fix_data.get("error", ""),
                            timestamp=datetime.fromisoformat(fix_data["timestamp"])
                        )
                        self.fixes.append(fix)
                logger.info(f"加载了 {len(self.fixes)} 条历史修复记录")
            except Exception as e:
                logger.warning(f"加载历史修复记录失败: {e}")
    
    def _save_fixes(self):
        """保存修复记录"""
        try:
            with open(self.fixes_file, 'w', encoding='utf-8') as f:
                json.dump([fix.to_dict() for fix in self.fixes], f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存修复记录失败: {e}")
    
    def add_fix(self, name: str, description: str, status: FixStatus = FixStatus.PENDING,
                result: str = "", error: str = ""):
        """添加修复记录"""
        fix = FixAction(
            name=name,
            description=description,
            status=status,
            result=result,
            error=error
        )
        self.fixes.append(fix)
        self._save_fixes()
        
        log_func = {
            FixStatus.SUCCESS: logger.info,
            FixStatus.FAILED: logger.error,
            FixStatus.SKIPPED: logger.warning,
            FixStatus.RUNNING: logger.info,
            FixStatus.PENDING: logger.info
        }[status]
        
        log_func(f"修复: {name} - {description}")
        if result:
            log_func(f"结果: {result}")
        if error:
            log_func(f"错误: {error}")
    
    def fix_config_file(self, config_path: str, updates: Dict[str, Any]) -> bool:
        """修复配置文件"""
        try:
            config_file = self.workspace_path / config_path
            
            if not config_file.exists():
                self.add_fix(
                    f"修复配置文件: {config_path}",
                    f"配置文件不存在",
                    FixStatus.FAILED,
                    error=f"文件不存在: {config_file}"
                )
                return False
            
            # 读取配置
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.suffix == '.json':
                    config = json.load(f)
                elif config_file.suffix in ['.yaml', '.yml']:
                    import yaml
                    config = yaml.safe_load(f)
                else:
                    self.add_fix(
                        f"修复配置文件: {config_path}",
                        f"不支持的配置文件格式",
                        FixStatus.FAILED,
                        error=f"不支持的格式: {config_file.suffix}"
                    )
                    return False
            
            # 更新配置
            def update_dict(target, updates):
                for key, value in updates.items():
                    if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                        update_dict(target[key], value)
                    else:
                        target[key] = value
            
            update_dict(config, updates)
            
            # 写回配置
            with open(config_file, 'w', encoding='utf-8') as f:
                if config_file.suffix == '.json':
                    json.dump(config, f, indent=2, ensure_ascii=False)
                elif config_file.suffix in ['.yaml', '.yml']:
                    import yaml
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            self.add_fix(
                f"修复配置文件: {config_path}",
                f"成功更新配置",
                FixStatus.SUCCESS,
                result=f"更新项: {list(updates.keys())}"
            )
            return True
            
        except Exception as e:
            self.add_fix(
                f"修复配置文件: {config_path}",
                f"修复失败",
                FixStatus.FAILED,
                error=str(e)
            )
            return False
    
    def fix_risk_constraints(self) -> bool:
        """修复风险约束"""
        try:
            # 更新配置文件中的风险参数
            updates = {
                "risk": {
                    "max_drawdown": 0.15,
                    "stop_loss": 0.08,
                    "position_limit": 0.90,
                    "industry_concentration": 0.30
                },
                "trading": {
                    "max_position_per_stock": 0.15,
                    "max_positions": 20
                }
            }
            
            success = self.fix_config_file("config.yaml", updates)
            
            if success:
                self.add_fix(
                    "修复风险约束",
                    "成功更新风险参数",
                    FixStatus.SUCCESS,
                    result="最大回撤: 15%, 止损: 8%, 仓位限制: 90%, 行业集中度: 30%"
                )
            
            return success
            
        except Exception as e:
            self.add_fix(
                "修复风险约束",
                "修复失败",
                FixStatus.FAILED,
                error=str(e)
            )
            return False
    
    def fix_factor_selection(self, min_ic: float = 0.02) -> bool:
        """修复因子选择"""
        try:
            pipeline_file = self.workspace_path / "data" / "pipeline_data.json"
            
            if not pipeline_file.exists():
                self.add_fix(
                    "修复因子选择",
                    "管线数据文件不存在",
                    FixStatus.FAILED,
                    error="管线数据文件不存在"
                )
                return False
            
            with open(pipeline_file, 'r', encoding='utf-8') as f:
                pipeline_data = json.load(f)
            
            factor_ic_values = pipeline_data.get("factor_ic_values", {})
            
            # 筛选高IC因子
            high_ic_factors = {
                factor_id: ic for factor_id, ic in factor_ic_values.items()
                if abs(ic) >= min_ic
            }
            
            if len(high_ic_factors) < 10:
                self.add_fix(
                    "修复因子选择",
                    f"高IC因子数量不足: {len(high_ic_factors)}",
                    FixStatus.FAILED,
                    error=f"需要至少10个高IC因子，当前只有{len(high_ic_factors)}个"
                )
                return False
            
            # 更新活跃因子列表
            pipeline_data["active_factor_ids"] = list(high_ic_factors.keys())
            pipeline_data["factor_ic_values"] = high_ic_factors
            
            # 写回文件
            with open(pipeline_file, 'w', encoding='utf-8') as f:
                json.dump(pipeline_data, f, indent=2, ensure_ascii=False)
            
            self.add_fix(
                "修复因子选择",
                f"成功筛选高IC因子",
                FixStatus.SUCCESS,
                result=f"保留 {len(high_ic_factors)} 个高IC因子 (IC >= {min_ic})"
            )
            
            return True
            
        except Exception as e:
            self.add_fix(
                "修复因子选择",
                "修复失败",
                FixStatus.FAILED,
                error=str(e)
            )
            return False
    
    def fix_backtest_parameters(self) -> bool:
        """修复回测参数"""
        try:
            # 更新回测参数
            updates = {
                "strategy": {
                    "rebalance_frequency": "weekly",  # 改为周调仓
                    "min_stocks": 10,
                    "max_stocks": 20
                }
            }
            
            success = self.fix_config_file("config.yaml", updates)
            
            if success:
                self.add_fix(
                    "修复回测参数",
                    "成功更新回测参数",
                    FixStatus.SUCCESS,
                    result="调仓频率: 周调仓, 最小股票数: 10, 最大股票数: 20"
                )
            
            return success
            
        except Exception as e:
            self.add_fix(
                "修复回测参数",
                "修复失败",
                FixStatus.FAILED,
                error=str(e)
            )
            return False
    
    def run_pipeline_command(self, command: str) -> bool:
        """运行管线命令"""
        try:
            self.add_fix(
                f"运行管线命令: {command}",
                "开始执行",
                FixStatus.RUNNING
            )
            
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                self.add_fix(
                    f"运行管线命令: {command}",
                    "执行成功",
                    FixStatus.SUCCESS,
                    result=result.stdout[:500] if result.stdout else "无输出"
                )
                return True
            else:
                self.add_fix(
                    f"运行管线命令: {command}",
                    "执行失败",
                    FixStatus.FAILED,
                    error=result.stderr[:500] if result.stderr else "未知错误"
                )
                return False
                
        except subprocess.TimeoutExpired:
            self.add_fix(
                f"运行管线命令: {command}",
                "执行超时",
                FixStatus.FAILED,
                error="命令执行超时（300秒）"
            )
            return False
        except Exception as e:
            self.add_fix(
                f"运行管线命令: {command}",
                "执行失败",
                FixStatus.FAILED,
                error=str(e)
            )
            return False
    
    def run_auto_fixes(self, diagnoses: List = None) -> Dict[str, Any]:
        """运行自动修复"""
        logger.info("=" * 60)
        logger.info("开始自动修复")
        logger.info("=" * 60)
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "fixes": [],
            "summary": {
                "total": 0,
                "success": 0,
                "failed": 0,
                "skipped": 0
            }
        }
        
        # 如果没有提供诊断，从文件加载
        if diagnoses is None:
            diagnoses_file = self.workspace_path / "data" / "monitor" / "diagnoses.json"
            if diagnoses_file.exists():
                with open(diagnoses_file, 'r', encoding='utf-8') as f:
                    diagnoses = json.load(f)
        
        # 根据诊断执行修复
        if diagnoses:
            for diagnosis in diagnoses:
                issue = diagnosis.get("issue", "")
                severity = diagnosis.get("severity", "")
                
                # 只修复高优先级问题
                if severity in ["high", "critical"]:
                    if "行业集中度" in issue or "风险" in issue:
                        success = self.fix_risk_constraints()
                        results["fixes"].append({"issue": issue, "fix": "risk_constraints", "success": success})
                    
                    elif "因子" in issue or "IC" in issue:
                        success = self.fix_factor_selection()
                        results["fixes"].append({"issue": issue, "fix": "factor_selection", "success": success})
                    
                    elif "回测" in issue or "参数" in issue:
                        success = self.fix_backtest_parameters()
                        results["fixes"].append({"issue": issue, "fix": "backtest_parameters", "success": success})
        
        # 统计结果
        results["summary"]["total"] = len(results["fixes"])
        results["summary"]["success"] = sum(1 for f in results["fixes"] if f["success"])
        results["summary"]["failed"] = sum(1 for f in results["fixes"] if not f["success"])
        
        logger.info("=" * 60)
        logger.info(f"自动修复完成: 成功 {results['summary']['success']}/{results['summary']['total']}")
        logger.info("=" * 60)
        
        return results
    
    def get_fix_history(self, limit: int = 10) -> List[FixAction]:
        """获取修复历史"""
        return self.fixes[-limit:]


def main():
    """主函数"""
    fix = AutoFix()
    results = fix.run_auto_fixes()
    
    print(f"自动修复结果:")
    print(f"  总计: {results['summary']['total']}")
    print(f"  成功: {results['summary']['success']}")
    print(f"  失败: {results['summary']['failed']}")
    
    for fix_result in results["fixes"]:
        status = "✓" if fix_result["success"] else "✗"
        print(f"  {status} {fix_result['issue']}: {fix_result['fix']}")


if __name__ == "__main__":
    main()
