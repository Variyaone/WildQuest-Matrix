"""
自动诊断系统
分析问题的根本原因，提供解决方案
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..infrastructure.logging import get_logger
from ..infrastructure.exceptions import AppException

logger = get_logger("automation.auto_diagnose")


class DiagnosisSeverity(Enum):
    """诊断严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Diagnosis:
    """诊断结果"""
    issue: str
    severity: DiagnosisSeverity
    root_cause: str
    solution: str
    priority: int = 0
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue": self.issue,
            "severity": self.severity.value,
            "root_cause": self.root_cause,
            "solution": self.solution,
            "priority": self.priority,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class AutoDiagnose:
    """自动诊断器"""
    
    def __init__(self, workspace_path: str = None):
        self.workspace_path = workspace_path or Path.cwd()
        self.diagnoses: List[Diagnosis] = []
        self.diagnoses_file = self.workspace_path / "data" / "monitor" / "diagnoses.json"
        self.diagnoses_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载历史诊断
        self._load_diagnoses()
    
    def _load_diagnoses(self):
        """加载历史诊断"""
        if self.diagnoses_file.exists():
            try:
                with open(self.diagnoses_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for diag_data in data:
                        diagnosis = Diagnosis(
                            issue=diag_data["issue"],
                            severity=DiagnosisSeverity(diag_data["severity"]),
                            root_cause=diag_data["root_cause"],
                            solution=diag_data["solution"],
                            priority=diag_data.get("priority", 0),
                            details=diag_data.get("details", {}),
                            timestamp=datetime.fromisoformat(diag_data["timestamp"])
                        )
                        self.diagnoses.append(diagnosis)
                logger.info(f"加载了 {len(self.diagnoses)} 条历史诊断")
            except Exception as e:
                logger.warning(f"加载历史诊断失败: {e}")
    
    def _save_diagnoses(self):
        """保存诊断"""
        try:
            with open(self.diagnoses_file, 'w', encoding='utf-8') as f:
                json.dump([d.to_dict() for d in self.diagnoses], f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存诊断失败: {e}")
    
    def add_diagnosis(self, issue: str, severity: DiagnosisSeverity, root_cause: str, 
                     solution: str, priority: int = 0, details: Dict[str, Any] = None):
        """添加诊断"""
        diagnosis = Diagnosis(
            issue=issue,
            severity=severity,
            root_cause=root_cause,
            solution=solution,
            priority=priority,
            details=details or {}
        )
        self.diagnoses.append(diagnosis)
        self._save_diagnoses()
        
        logger.info(f"诊断: {issue}")
        logger.info(f"  根本原因: {root_cause}")
        logger.info(f"  解决方案: {solution}")
    
    def diagnose_risk_violations(self, pipeline_data: Dict[str, Any]) -> List[Diagnosis]:
        """诊断风险违规"""
        diagnoses = []

        risk_check_result = pipeline_data.get("risk_check_result", {})
        if not risk_check_result.get("passed"):
            violations_data = risk_check_result.get("violations", [])

            try:
                # 尝试解析JSON字符串
                violations = []
                if isinstance(violations_data, str):
                    try:
                        violations = json.loads(violations_data)
                    except json.JSONDecodeError:
                        # 如果JSON解析失败，尝试使用eval（不安全，但作为后备方案）
                        try:
                            violations = eval(violations_data)
                        except:
                            logger.error(f"无法解析violations: {violations_data}")
                            violations = []
                elif isinstance(violations_data, list):
                    violations = violations_data
                else:
                    logger.warning(f"violations类型不正确: {type(violations_data)}")
                    violations = []

                # 确保是列表
                if not isinstance(violations, list):
                    violations = [violations]

                for violation in violations:
                    if not isinstance(violation, dict):
                        continue

                    rule_id = violation.get("rule_id")
                    rule_name = violation.get("rule_name")
                    message = violation.get("message")

                    if rule_id == "H2":  # 行业集中度
                        diagnoses.append(Diagnosis(
                            issue=f"行业集中度违规: {message}",
                            severity=DiagnosisSeverity.HIGH,
                            root_cause="组合优化未考虑行业分散，所有股票集中在同一行业",
                            solution="1. 在组合优化中添加行业约束\n2. 使用行业中性化因子\n3. 限制单一行业最大权重",
                            priority=1,
                            details=violation
                        ))

                    elif rule_id == "H3":  # 总仓位
                        diagnoses.append(Diagnosis(
                            issue=f"总仓位违规: {message}",
                            severity=DiagnosisSeverity.MEDIUM,
                            root_cause="组合优化未设置仓位上限约束",
                            solution="1. 在组合优化中添加总仓位约束\n2. 设置最大仓位为90%\n3. 保留10%现金缓冲",
                            priority=2,
                            details=violation
                        ))

                    elif rule_id == "E2":  # 换手率
                        diagnoses.append(Diagnosis(
                            issue=f"换手率过高: {message}",
                            severity=DiagnosisSeverity.MEDIUM,
                            root_cause="调仓频率过高，未考虑交易成本",
                            solution="1. 增加调仓周期（如从5天改为10天）\n2. 添加换手率约束\n3. 使用交易成本优化",
                            priority=3,
                            details=violation
                        ))

            except Exception as e:
                logger.error(f"解析风险违规失败: {e}")
                # 即使解析失败，也创建一个诊断
                diagnoses.append(Diagnosis(
                    issue="风险检查未通过",
                    severity=DiagnosisSeverity.HIGH,
                    root_cause=f"风险违规数据解析失败: {str(e)}",
                    solution="1. 检查风险违规数据格式\n2. 手动审查风险配置\n3. 重新运行风险检查",
                    priority=1,
                    details={"error": str(e), "violations_data": violations_data}
                ))

        return diagnoses
    
    def diagnose_factor_quality(self, pipeline_data: Dict[str, Any]) -> List[Diagnosis]:
        """诊断因子质量"""
        diagnoses = []
        
        factor_ic_values = pipeline_data.get("factor_ic_values", {})
        active_factor_ids = pipeline_data.get("active_factor_ids", [])
        
        # 检查因子IC
        low_ic_factors = []
        for factor_id, ic in factor_ic_values.items():
            if abs(ic) < 0.02:  # IC绝对值小于0.02
                low_ic_factors.append((factor_id, ic))
        
        if low_ic_factors:
            diagnoses.append(Diagnosis(
                issue=f"发现 {len(low_ic_factors)} 个低IC因子",
                severity=DiagnosisSeverity.MEDIUM,
                root_cause="因子预测能力不足，可能需要重新计算或替换",
                solution=f"1. 移除低IC因子: {[f[0] for f in low_ic_factors]}\n2. 重新计算因子\n3. 寻找替代因子",
                priority=4,
                details={"low_ic_factors": low_ic_factors}
            ))
        
        # 检查因子数量
        if len(active_factor_ids) < 10:
            diagnoses.append(Diagnosis(
                issue=f"活跃因子数量过少: {len(active_factor_ids)}",
                severity=DiagnosisSeverity.MEDIUM,
                root_cause="因子筛选过于严格，或因子计算失败",
                solution="1. 放宽因子筛选标准\n2. 检查因子计算失败原因\n3. 添加更多因子",
                priority=5,
                details={"factor_count": len(active_factor_ids)}
            ))
        
        return diagnoses
    
    def diagnose_backtest_quality(self, metrics: Dict[str, Any]) -> List[Diagnosis]:
        """诊断回测质量"""
        diagnoses = []
        
        sharpe = metrics.get("sharpe_ratio", {}).get("value", 0)
        max_dd = abs(metrics.get("max_drawdown", {}).get("value", 0))
        annual_return = metrics.get("annual_return", {}).get("value", 0)
        
        # 夏普比率过低
        if sharpe < 1.0:
            diagnoses.append(Diagnosis(
                issue=f"夏普比率过低: {sharpe:.2f}",
                severity=DiagnosisSeverity.HIGH,
                root_cause="策略风险调整后收益不足，可能原因：\n1. 因子预测能力弱\n2. 组合优化不合理\n3. 交易成本过高",
                solution="1. 提升因子质量（IC > 0.03）\n2. 优化组合权重分配\n3. 降低换手率减少交易成本\n4. 添加风险模型",
                priority=1,
                details={"sharpe_ratio": sharpe}
            ))
        
        # 最大回撤过大
        if max_dd > 0.20:
            diagnoses.append(Diagnosis(
                issue=f"最大回撤过大: {max_dd:.2%}",
                severity=DiagnosisSeverity.HIGH,
                root_cause="风险控制不足，可能原因：\n1. 未设置止损\n2. 仓位过于集中\n3. 市场极端行情",
                solution="1. 添加止损机制（单股-8%）\n2. 分散持仓（单股<15%）\n3. 添加市场择时\n4. 降低整体仓位",
                priority=2,
                details={"max_drawdown": max_dd}
            ))
        
        # 年化收益过低
        if annual_return < 0.10:
            diagnoses.append(Diagnosis(
                issue=f"年化收益过低: {annual_return:.2%}",
                severity=DiagnosisSeverity.MEDIUM,
                root_cause="策略盈利能力不足，可能原因：\n1. 因子选股能力弱\n2. 持仓周期不合理\n3. 交易成本侵蚀收益",
                solution="1. 提升因子IC值\n2. 优化持仓周期\n3. 降低交易频率\n4. 提高仓位利用率",
                priority=3,
                details={"annual_return": annual_return}
            ))
        
        return diagnoses
    
    def diagnose_data_quality(self, pipeline_data: Dict[str, Any]) -> List[Diagnosis]:
        """诊断数据质量"""
        diagnoses = []
        
        data_quality = pipeline_data.get("data_quality", {})
        
        # 检查数据完整性
        for check_name, check_result in data_quality.items():
            if isinstance(check_result, str):
                try:
                    result_dict = eval(check_result)
                    if result_dict.get("status") != "pass":
                        diagnoses.append(Diagnosis(
                            issue=f"数据质量检查失败: {check_name}",
                            severity=DiagnosisSeverity.HIGH,
                            root_cause="数据更新不完整或数据源异常",
                            solution="1. 检查数据源连接\n2. 重新运行数据更新\n3. 验证数据完整性",
                            priority=1,
                            details={"check": check_name, "result": result_dict}
                        ))
                except Exception as e:
                    logger.warning(f"解析数据质量检查失败: {e}")
        
        return diagnoses
    
    def run_full_diagnosis(self, pipeline_data: Dict[str, Any] = None, 
                          backtest_metrics: Dict[str, Any] = None) -> List[Diagnosis]:
        """运行完整诊断"""
        logger.info("=" * 60)
        logger.info("开始自动诊断")
        logger.info("=" * 60)
        
        all_diagnoses = []
        
        # 加载管线数据
        if pipeline_data is None:
            pipeline_file = self.workspace_path / "data" / "pipeline_data.json"
            if pipeline_file.exists():
                with open(pipeline_file, 'r', encoding='utf-8') as f:
                    pipeline_data = json.load(f)
        
        # 诊断风险违规
        if pipeline_data:
            all_diagnoses.extend(self.diagnose_risk_violations(pipeline_data))
            all_diagnoses.extend(self.diagnose_factor_quality(pipeline_data))
            all_diagnoses.extend(self.diagnose_data_quality(pipeline_data))
        
        # 诊断回测质量
        if backtest_metrics is None:
            reports_dir = self.workspace_path / "data" / "reports"
            metric_files = sorted(reports_dir.glob("performance_metrics_*.json"), reverse=True)
            if metric_files:
                with open(metric_files[0], 'r', encoding='utf-8') as f:
                    backtest_metrics = json.load(f)
        
        if backtest_metrics:
            all_diagnoses.extend(self.diagnose_backtest_quality(backtest_metrics))
        
        # 按优先级排序
        all_diagnoses.sort(key=lambda x: x.priority)
        
        # 保存诊断
        for diagnosis in all_diagnoses:
            self.add_diagnosis(
                diagnosis.issue,
                diagnosis.severity,
                diagnosis.root_cause,
                diagnosis.solution,
                diagnosis.priority,
                diagnosis.details
            )
        
        logger.info("=" * 60)
        logger.info(f"诊断完成，发现 {len(all_diagnoses)} 个问题")
        logger.info("=" * 60)
        
        return all_diagnoses
    
    def get_top_diagnoses(self, limit: int = 5) -> List[Diagnosis]:
        """获取优先级最高的诊断"""
        sorted_diagnoses = sorted(self.diagnoses, key=lambda x: x.priority)
        return sorted_diagnoses[:limit]


def main():
    """主函数"""
    diagnose = AutoDiagnose()
    diagnoses = diagnose.run_full_diagnosis()
    
    print(f"发现 {len(diagnoses)} 个问题:")
    for i, diag in enumerate(diagnoses, 1):
        print(f"\n{i}. {diag.issue} (优先级: {diag.priority})")
        print(f"   严重程度: {diag.severity.value}")
        print(f"   根本原因: {diag.root_cause}")
        print(f"   解决方案: {diag.solution}")


if __name__ == "__main__":
    main()
